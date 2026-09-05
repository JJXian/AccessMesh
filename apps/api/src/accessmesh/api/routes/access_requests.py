"""权限申请的创建、列表与详情接口。"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.agents.identity_context import SubjectNotFoundError
from accessmesh.agents.request_parser import LlmRequestParser
from accessmesh.api.dependencies import (
    get_current_demo_user,
    require_roles,
)
from accessmesh.config import get_settings
from accessmesh.context.resource_context import ResourceContextLoader
from accessmesh.db.models import (
    AccessRequest,
    Approval,
    AuditEvent,
    DemoUser,
    ExecutionTask,
    PermissionInstance,
    PolicyDecisionRecord,
    ProposedGrant,
    Resource,
)
from accessmesh.db.session import get_db
from accessmesh.domain.schemas import (
    AccessRequestCreate,
    AccessRequestDetailRead,
    AccessRequestPageRead,
    AccessRequestRead,
    ApprovalRead,
    AuditEventRead,
    CandidateGrant,
    ExecutionTaskRead,
    PermissionLifecycleRead,
    PolicyDecisionDetailRead,
    ProposedGrantDetailRead,
)
from accessmesh.execution.service import (
    ExecutionConflictError,
    ExecutionNotFoundError,
    execute_approved_request,
)
from accessmesh.graph.workflow import build_access_request_graph
from accessmesh.llm.provider import (
    LlmConfigurationError,
    LlmProviderError,
    OpenAICompatibleProvider,
)
from accessmesh.planning.persistence import persist_proposed_grants
from accessmesh.policy.client import OpaPolicyClient, PolicyUnavailableError
from accessmesh.policy.evaluator import OpaPolicyEvaluator
from accessmesh.policy.persistence import (
    persist_policy_decisions,
    resolve_request_status,
)

router = APIRouter()


@router.post("", response_model=AccessRequestRead, status_code=status.HTTP_201_CREATED)
async def create_access_request(
    payload: AccessRequestCreate,
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AccessRequestRead:
    """创建申请，完成规划、OPA 策略判断与审计记录。"""

    # “申请人 + 客户端请求号”构成幂等边界，前端重试不会创建重复申请。
    existing = await session.scalar(
        select(AccessRequest).where(
            AccessRequest.requester_external_id == current_user.external_id,
            AccessRequest.client_request_id == payload.client_request_id,
        )
    )
    if existing is not None:
        return AccessRequestRead.model_validate(existing)

    trace_id = uuid4().hex
    request = AccessRequest(
        requester_external_id=current_user.external_id,
        subject_external_id=payload.subject_external_id,
        raw_request=payload.request_text,
        client_request_id=payload.client_request_id,
        trace_id=trace_id,
    )
    session.add(request)

    # 此时写入申请单但还不提交，用于取得 request.id。
    await session.flush()

    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=trace_id,
            event_type="ACCESS_REQUEST_CREATED",
            actor_external_id=current_user.external_id,
            payload={"client_request_id": payload.client_request_id},
        )
    )

    settings = get_settings()
    context_loader = ResourceContextLoader(session)
    policy_client = OpaPolicyClient(settings)
    policy_evaluator = OpaPolicyEvaluator(policy_client)
    request_parser = None
    if settings.llm_enabled:
        # LLM 只负责解析用户意图；它不会获得审批或授权工具。
        request_parser = LlmRequestParser(OpenAICompatibleProvider(settings)).parse
    graph = build_access_request_graph(
        context_loader=context_loader.load,
        policy_evaluator=policy_evaluator.evaluate,
        request_parser=request_parser,
    )

    try:
        workflow_result = await graph.ainvoke(
            {
                "request_id": str(request.id),
                "trace_id": trace_id,
                "raw_request": payload.request_text,
                "subject_external_id": payload.subject_external_id,
            }
        )
    except SubjectNotFoundError as exc:
        # 未提交事务前主动回滚，避免留下没有主体的半成品申请。
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except PolicyUnavailableError as exc:
        # OPA 不可用时默认不放行，也不进入审批。
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="策略服务暂不可用，请稍后重试。",
        ) from exc
    except (LlmConfigurationError, LlmProviderError) as exc:
        # 启用 LLM 后不静默切回规则解析，避免使用者误以为请求经过了模型。
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="请求解析模型暂不可用，请检查模型配置或稍后重试。",
        ) from exc

    candidate_grants = [
        CandidateGrant.model_validate(grant) for grant in workflow_result["proposed_grants"]
    ]
    persisted_grants = await persist_proposed_grants(
        session=session,
        request_id=request.id,
        grants=candidate_grants,
    )
    persisted_decisions = await persist_policy_decisions(
        session=session,
        request_id=request.id,
        raw_decisions=workflow_result["policy_decisions"],
    )

    # 根据候选方案和 OPA 决策，决定申请应进入哪个下一状态。
    request.status = resolve_request_status(
        grant_count=len(persisted_grants),
        policy_decisions=persisted_decisions,
    )

    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=trace_id,
            event_type="ACCESS_REQUEST_PARSED",
            actor_external_id=(
                "accessmesh-request-parser-agent"
                if workflow_result["parser_metadata"]["mode"] == "llm"
                else "accessmesh-rule-parser"
            ),
            payload={
                "parsed_intent": workflow_result["parsed_intent"],
                "parser_metadata": workflow_result["parser_metadata"],
            },
        )
    )
    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=trace_id,
            event_type="ACCESS_PLAN_CREATED",
            actor_external_id="accessmesh-planner",
            payload={
                "grant_count": len(persisted_grants),
                "plan_version": 1,
                "assumptions": workflow_result["plan_assumptions"],
            },
        )
    )
    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=trace_id,
            event_type="ACCESS_POLICY_EVALUATED",
            actor_external_id="opa",
            payload={
                "decision_count": len(persisted_decisions),
                "allowed_count": sum(decision.allow for decision in persisted_decisions),
                "denied_count": sum(not decision.allow for decision in persisted_decisions),
                "request_status": request.status,
            },
        )
    )

    # 申请、候选方案、策略决策、审计事件在同一事务中一次性提交。
    await session.commit()
    await session.refresh(request)

    return AccessRequestRead.model_validate(request)


@router.post(
    "/{request_id}/execute",
    response_model=AccessRequestRead,
)
async def execute_access_request(
    request_id: UUID,
    current_approver: Annotated[
        DemoUser,
        Depends(require_roles("approver")),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AccessRequestRead:
    """执行已审批通过的权限申请。"""

    try:
        request = await execute_approved_request(
            session=session,
            request_id=request_id,
            actor_external_id=current_approver.external_id,
        )
        await session.commit()
    except ExecutionNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ExecutionConflictError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    await session.refresh(request)
    return AccessRequestRead.model_validate(request)


@router.get("", response_model=AccessRequestPageRead)
async def list_access_requests(
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> AccessRequestPageRead:
    """按页查询申请；普通申请人只能查看自己发起的记录。"""

    # 先构建基础查询，再同时用于“总数统计”和“当前页数据查询”。
    base_query = select(AccessRequest)

    if current_user.role == "requester":
        base_query = base_query.where(
            AccessRequest.requester_external_id == current_user.external_id
        )

    # 总数必须在 limit/offset 之前统计，否则无法得到正确页数。
    total = await session.scalar(select(func.count()).select_from(base_query.subquery()))

    # 第 1 页偏移 0 条；第 2 页偏移 page_size 条，以此类推。
    offset = (page - 1) * page_size
    query = base_query.order_by(AccessRequest.created_at.desc()).offset(offset).limit(page_size)
    requests = await session.scalars(query)

    return AccessRequestPageRead(
        items=[AccessRequestRead.model_validate(request) for request in requests.all()],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{request_id}", response_model=AccessRequestRead)
async def get_access_request(
    request_id: UUID,
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AccessRequestRead:
    """查询申请详情，并阻止申请人读取他人的申请。"""

    request = await session.get(AccessRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request not found")
    requester_cannot_view = (
        current_user.role == "requester"
        and request.requester_external_id != current_user.external_id
    )
    if requester_cannot_view:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="request not visible")
    return AccessRequestRead.model_validate(request)


@router.get("/{request_id}/detail", response_model=AccessRequestDetailRead)
async def get_access_request_detail(
    request_id: UUID,
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AccessRequestDetailRead:
    """聚合查询申请从权限规划到回收的完整处理链路。"""

    request = await session.get(AccessRequest, request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="request not found",
        )

    requester_cannot_view = (
        current_user.role == "requester"
        and request.requester_external_id != current_user.external_id
    )
    if requester_cannot_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="request not visible",
        )

    # 候选方案需要同时读取资源目录，前端才能显示中文资源名称和环境。
    grant_result = await session.execute(
        select(ProposedGrant, Resource)
        .join(Resource, Resource.id == ProposedGrant.resource_id)
        .where(ProposedGrant.request_id == request.id)
        .order_by(ProposedGrant.plan_version, ProposedGrant.created_at)
    )
    grants = [
        ProposedGrantDetailRead(
            id=grant.id,
            resource_external_id=resource.external_id,
            resource_name=resource.name,
            resource_type=resource.resource_type,
            environment=resource.environment,
            sensitivity=resource.sensitivity,
            permission=grant.permission,
            duration_days=grant.duration_days,
            reason=grant.reason,
            evidence_refs=grant.evidence_refs,
            plan_version=grant.plan_version,
            created_at=grant.created_at,
        )
        for grant, resource in grant_result.all()
    ]

    decision_result = await session.scalars(
        select(PolicyDecisionRecord)
        .where(PolicyDecisionRecord.request_id == request.id)
        .order_by(PolicyDecisionRecord.created_at)
    )
    approval = await session.scalar(select(Approval).where(Approval.request_id == request.id))
    task_result = await session.scalars(
        select(ExecutionTask)
        .where(ExecutionTask.request_id == request.id)
        .order_by(ExecutionTask.created_at)
    )

    permission_result = await session.execute(
        select(PermissionInstance, Resource)
        .join(Resource, Resource.id == PermissionInstance.resource_id)
        .where(PermissionInstance.request_id == request.id)
        .order_by(PermissionInstance.granted_at)
    )
    permissions = [
        PermissionLifecycleRead(
            id=permission.id,
            execution_task_id=permission.execution_task_id,
            resource_external_id=resource.external_id,
            resource_name=resource.name,
            permission=permission.permission,
            status=permission.status,
            external_grant_id=permission.external_grant_id,
            granted_at=permission.granted_at,
            expires_at=permission.expires_at,
            revoked_at=permission.revoked_at,
            revocation_reason=permission.revocation_reason,
        )
        for permission, resource in permission_result.all()
    ]

    audit_result = await session.scalars(
        select(AuditEvent)
        .where(AuditEvent.request_id == request.id)
        .order_by(AuditEvent.created_at)
    )

    return AccessRequestDetailRead(
        request=AccessRequestRead.model_validate(request),
        proposed_grants=grants,
        policy_decisions=[
            PolicyDecisionDetailRead.model_validate(decision) for decision in decision_result.all()
        ],
        approval=ApprovalRead.model_validate(approval) if approval else None,
        execution_tasks=[ExecutionTaskRead.model_validate(task) for task in task_result.all()],
        permissions=permissions,
        audit_events=[AuditEventRead.model_validate(event) for event in audit_result.all()],
    )

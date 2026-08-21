"""权限申请的创建、列表与详情接口。"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.api.dependencies import get_current_demo_user
from accessmesh.context.resource_context import ResourceContextLoader
from accessmesh.db.models import AccessRequest, AuditEvent, DemoUser
from accessmesh.db.session import get_db
from accessmesh.domain.enums import RequestStatus
from accessmesh.domain.schemas import (
    AccessRequestCreate,
    AccessRequestRead,
    CandidateGrant,
)
from accessmesh.graph.workflow import build_access_request_graph
from accessmesh.planning.persistence import persist_proposed_grants

router = APIRouter()


@router.post("", response_model=AccessRequestRead, status_code=status.HTTP_201_CREATED)
async def create_access_request(
    payload: AccessRequestCreate,
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AccessRequestRead:
    """创建申请、生成候选方案，并在同一事务中记录审计事件。"""

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

    # flush 会发送 INSERT，但不会提交事务。
    # 它的目的只是获取 request.id，供审计事件和候选方案关联。
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

    # 将当前请求使用的数据库会话注入工作流。
    # 工作流因此能查询真实 resources 表，但不会自行创建新事务。
    context_loader = ResourceContextLoader(session)
    graph = build_access_request_graph(context_loader=context_loader.load)
    workflow_result = await graph.ainvoke(
        {
            "request_id": str(request.id),
            "trace_id": trace_id,
            "raw_request": payload.request_text,
        }
    )

    # LangGraph 状态中的候选方案是普通字典；
    # 保存前重新校验为 CandidateGrant，确保数据满足领域约束。
    candidate_grants = [
        CandidateGrant.model_validate(grant) for grant in workflow_result["proposed_grants"]
    ]
    persisted_grants = await persist_proposed_grants(
        session=session,
        request_id=request.id,
        grants=candidate_grants,
    )

    # 当前工作流在“规划完成”后停止，下一阶段才进入 OPA 策略判断。
    request.status = RequestStatus.PLANNING

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

    # 到这里才一次性提交：申请单、候选方案和两条审计事件要么全部成功，要么全部失败。
    await session.commit()
    await session.refresh(request)

    return AccessRequestRead.model_validate(request)


@router.get("", response_model=list[AccessRequestRead])
async def list_access_requests(
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AccessRequestRead]:
    """按时间倒序查询申请；普通申请人只能看到自己发起的记录。"""

    query = select(AccessRequest).order_by(AccessRequest.created_at.desc())
    if current_user.role == "requester":
        query = query.where(AccessRequest.requester_external_id == current_user.external_id)
    requests = await session.scalars(query)
    return [AccessRequestRead.model_validate(item) for item in requests.all()]


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

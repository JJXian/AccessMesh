"""审批通过后执行授权、验证权限并在失败时补偿。"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.adapters.base import GrantCommand, OperationResult, ResourceAdapter
from accessmesh.adapters.registry import AdapterRegistry, adapter_registry
from accessmesh.db.models import (
    AccessRequest,
    AuditEvent,
    ExecutionTask,
    PermissionInstance,
    ProposedGrant,
    Resource,
    utc_now,
)
from accessmesh.domain.enums import (
    ExecutionTaskStatus,
    PermissionStatus,
    RequestStatus,
)


class ExecutionNotFoundError(LookupError):
    """尝试执行不存在申请时抛出的异常。"""


class ExecutionConflictError(ValueError):
    """申请当前状态不允许执行时抛出的异常。"""


class ExecutionOperationError(RuntimeError):
    """外部资源适配器授予或验证权限失败时抛出的异常。"""


@dataclass(slots=True)
class ExecutedGrant:
    """已成功调用 grant、等待统一验证的执行上下文。"""

    task: ExecutionTask
    grant: ProposedGrant
    resource: Resource
    adapter: ResourceAdapter
    command: GrantCommand
    result: OperationResult


async def execute_approved_request(
    session: AsyncSession,
    request_id: UUID,
    actor_external_id: str,
    registry: AdapterRegistry = adapter_registry,
) -> AccessRequest:
    """执行已审批申请，并在失败时撤销本次已成功授予的权限。

    当前项目使用内存适配器模拟 GitLab、数据库和云资源。
    真实环境中可将 AdapterRegistry 中的实现替换为对应系统 API 适配器。
    """

    request = await session.get(AccessRequest, request_id)
    if request is None:
        raise ExecutionNotFoundError("待执行申请不存在。")

    # 只有人工审批通过后的申请才允许执行。
    if request.status != RequestStatus.APPROVED:
        raise ExecutionConflictError(f"当前申请状态为 {request.status}，不能执行授权。")

    result = await session.execute(
        select(ProposedGrant, Resource)
        .join(Resource, Resource.id == ProposedGrant.resource_id)
        .where(ProposedGrant.request_id == request.id)
        .order_by(ProposedGrant.created_at)
    )
    grant_rows = result.all()

    if not grant_rows:
        raise ExecutionConflictError("申请没有可执行的候选授权方案。")

    request.status = RequestStatus.EXECUTING
    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=request.trace_id,
            event_type="ACCESS_EXECUTION_STARTED",
            actor_external_id=actor_external_id,
            payload={"grant_count": len(grant_rows)},
        )
    )

    executed_grants: list[ExecutedGrant] = []

    try:
        for grant, resource in grant_rows:
            # 这把键同时写入数据库和传给适配器，重试时可避免重复授予。
            idempotency_key = f"grant:{request.id}:{grant.id}"

            # 显式生成任务主键，是因为后续 PermissionInstance 需要关联 task.id。
            task = ExecutionTask(
                id=uuid4(),
                request_id=request.id,
                proposed_grant_id=grant.id,
                status=ExecutionTaskStatus.RUNNING,
                idempotency_key=idempotency_key,
                attempt_count=1,
            )
            session.add(task)

            command = GrantCommand(
                subject_external_id=request.subject_external_id,
                resource_external_id=resource.external_id,
                permission=grant.permission,
                idempotency_key=idempotency_key,
            )
            adapter = registry.get(resource.resource_type)

            # 适配器只负责与目标系统交互；状态流转和审计仍由执行服务统一管理。
            operation_result = await adapter.grant(command)
            task.result = {
                "grant_operation_id": operation_result.operation_id,
                "grant_message": operation_result.message,
                "grant_success": operation_result.success,
            }

            if not operation_result.success:
                task.status = ExecutionTaskStatus.FAILED
                task.error_message = operation_result.message
                raise ExecutionOperationError(
                    f"授权失败：{resource.external_id} / {grant.permission}"
                )

            executed_grants.append(
                ExecutedGrant(
                    task=task,
                    grant=grant,
                    resource=resource,
                    adapter=adapter,
                    command=command,
                    result=operation_result,
                )
            )

        # 所有 grant 调用返回成功后，仍需二次验证目标系统状态。
        request.status = RequestStatus.VERIFYING

        for executed in executed_grants:
            verified = await executed.adapter.check(executed.command)
            executed.task.result["verified"] = verified

            if not verified:
                executed.task.status = ExecutionTaskStatus.FAILED
                executed.task.error_message = "授权后验证失败。"
                raise ExecutionOperationError(
                    f"授权后验证失败：{executed.resource.external_id} / {executed.grant.permission}"
                )

        # 只有全部 grant 均验证成功，才创建“真实有效权限”台账。
        granted_at = utc_now()

        for executed in executed_grants:
            executed.task.status = ExecutionTaskStatus.SUCCEEDED

            session.add(
                PermissionInstance(
                    request_id=request.id,
                    execution_task_id=executed.task.id,
                    subject_external_id=request.subject_external_id,
                    resource_id=executed.resource.id,
                    permission=executed.grant.permission,
                    status=PermissionStatus.ACTIVE,
                    external_grant_id=executed.result.operation_id,
                    granted_at=granted_at,
                    expires_at=granted_at + timedelta(days=executed.grant.duration_days),
                )
            )

        request.status = RequestStatus.ACTIVE
        session.add(
            AuditEvent(
                request_id=request.id,
                trace_id=request.trace_id,
                event_type="ACCESS_EXECUTION_COMPLETED",
                actor_external_id=actor_external_id,
                payload={
                    "task_count": len(executed_grants),
                    "permission_status": PermissionStatus.ACTIVE,
                },
            )
        )

    except ExecutionOperationError as exc:
        await _compensate(
            session=session,
            request=request,
            actor_external_id=actor_external_id,
            executed_grants=executed_grants,
            reason=str(exc),
        )

    # 这里不 commit，保证 API 路由可以统一管理事务。
    await session.flush()
    return request


async def _compensate(
    session: AsyncSession,
    request: AccessRequest,
    actor_external_id: str,
    executed_grants: list[ExecutedGrant],
    reason: str,
) -> None:
    """撤销本次执行中已成功授权的资源，避免保留半授权状态。"""

    request.status = RequestStatus.COMPENSATING

    # 倒序补偿：通常按与执行相反的顺序撤销更容易理解和排障。
    for executed in reversed(executed_grants):
        revoke_command = GrantCommand(
            subject_external_id=executed.command.subject_external_id,
            resource_external_id=executed.command.resource_external_id,
            permission=executed.command.permission,
            idempotency_key=f"revoke:{executed.task.id}",
        )

        try:
            revoke_result = await executed.adapter.revoke(revoke_command)
            executed.task.result["compensation_operation_id"] = revoke_result.operation_id
            executed.task.result["compensation_success"] = revoke_result.success
            executed.task.status = (
                ExecutionTaskStatus.COMPENSATED
                if revoke_result.success
                else ExecutionTaskStatus.FAILED
            )
        except Exception as exc:  # noqa: BLE001
            # 补偿失败也必须记录；申请整体仍标记失败，后续可由人工处理。
            executed.task.status = ExecutionTaskStatus.FAILED
            executed.task.result["compensation_success"] = False
            executed.task.result["compensation_error"] = str(exc)

        executed.task.error_message = reason

    request.status = RequestStatus.FAILED
    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=request.trace_id,
            event_type="ACCESS_EXECUTION_FAILED",
            actor_external_id=actor_external_id,
            payload={
                "reason": reason,
                "compensated_task_count": len(executed_grants),
            },
        )
    )

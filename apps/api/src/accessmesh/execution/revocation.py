"""扫描并回收已经到期的权限实例。"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.adapters.base import GrantCommand
from accessmesh.adapters.registry import AdapterRegistry, adapter_registry
from accessmesh.db.models import (
    AccessRequest,
    AuditEvent,
    PermissionInstance,
    Resource,
    utc_now,
)
from accessmesh.domain.enums import PermissionStatus, RequestStatus


@dataclass(frozen=True, slots=True)
class ExpiryScanResult:
    """一次到期扫描的统计结果。"""

    scanned_count: int
    revoked_count: int
    failed_count: int


class RevocationNotFoundError(LookupError):
    """尝试回收不存在的权限实例时抛出的异常。"""


class RevocationConflictError(ValueError):
    """权限实例当前状态不允许再次回收时抛出的异常。"""


class RevocationOperationError(RuntimeError):
    """目标资源撤权失败或撤权后验证失败时抛出的异常。"""


@dataclass(frozen=True, slots=True)
class ManualRevocationResult:
    """手工回收完成后返回给 API 层的权限和资源信息。"""

    permission: PermissionInstance
    resource: Resource


async def revoke_permission_manually(
    session: AsyncSession,
    *,
    permission_id: UUID,
    actor_external_id: str,
    reason: str,
    registry: AdapterRegistry = adapter_registry,
) -> ManualRevocationResult:
    """手工提前回收单条有效权限，并验证外部权限已经不存在。"""

    result = await session.execute(
        select(PermissionInstance, Resource, AccessRequest)
        .join(Resource, Resource.id == PermissionInstance.resource_id)
        .join(AccessRequest, AccessRequest.id == PermissionInstance.request_id)
        .where(PermissionInstance.id == permission_id)
        # 锁住权限实例，避免手工操作与到期扫描同时执行撤权。
        .with_for_update(of=PermissionInstance)
    )
    row = result.one_or_none()
    if row is None:
        raise RevocationNotFoundError("待回收的权限实例不存在。")

    permission, resource, request = row
    if permission.status != PermissionStatus.ACTIVE:
        raise RevocationConflictError("该权限已经回收，不能重复操作。")

    command = GrantCommand(
        subject_external_id=permission.subject_external_id,
        resource_external_id=resource.external_id,
        permission=permission.permission,
        idempotency_key=f"manual-revoke:{permission.id}",
    )
    try:
        adapter = registry.get(resource.resource_type)
        operation_result = await adapter.revoke(command)
        still_granted = await adapter.check(command)
    except Exception as exc:  # noqa: BLE001
        message = f"调用目标资源撤权接口失败：{exc}"
        _add_manual_revocation_failure_event(
            session=session,
            request=request,
            permission=permission,
            resource=resource,
            actor_external_id=actor_external_id,
            reason=message,
        )
        raise RevocationOperationError(message) from exc

    if not operation_result.success:
        message = operation_result.message or "目标资源撤权失败。"
        _add_manual_revocation_failure_event(
            session=session,
            request=request,
            permission=permission,
            resource=resource,
            actor_external_id=actor_external_id,
            reason=message,
        )
        raise RevocationOperationError(message)
    if still_granted:
        message = "撤权后验证失败，目标资源中仍然存在该权限。"
        _add_manual_revocation_failure_event(
            session=session,
            request=request,
            permission=permission,
            resource=resource,
            actor_external_id=actor_external_id,
            reason=message,
        )
        raise RevocationOperationError(message)

    revoked_at = utc_now()
    permission.status = PermissionStatus.REVOKED
    permission.revoked_at = revoked_at
    permission.revocation_reason = reason
    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=request.trace_id,
            event_type="ACCESS_PERMISSION_REVOKED",
            actor_external_id=actor_external_id,
            payload={
                "permission_instance_id": str(permission.id),
                "resource_external_id": resource.external_id,
                "permission": permission.permission,
                "operation_id": operation_result.operation_id,
                "reason": reason,
                "revocation_type": "MANUAL",
            },
        )
    )

    # 同一申请可能生成多条权限；只有最后一条也被回收后，申请才进入 REVOKED。
    await session.flush()
    active_count = await session.scalar(
        select(func.count(PermissionInstance.id)).where(
            PermissionInstance.request_id == request.id,
            PermissionInstance.status == PermissionStatus.ACTIVE,
        )
    )
    if not active_count:
        request.status = RequestStatus.REVOKED
        session.add(
            AuditEvent(
                request_id=request.id,
                trace_id=request.trace_id,
                event_type="ACCESS_REQUEST_REVOKED",
                actor_external_id=actor_external_id,
                payload={"reason": "申请关联的权限均已手工回收"},
            )
        )

    return ManualRevocationResult(permission=permission, resource=resource)


def _add_manual_revocation_failure_event(
    *,
    session: AsyncSession,
    request: AccessRequest,
    permission: PermissionInstance,
    resource: Resource,
    actor_external_id: str,
    reason: str,
) -> None:
    """记录手工回收失败，确保外部操作失败也能被审计。"""

    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=request.trace_id,
            event_type="ACCESS_REVOCATION_FAILED",
            actor_external_id=actor_external_id,
            payload={
                "permission_instance_id": str(permission.id),
                "resource_external_id": resource.external_id,
                "permission": permission.permission,
                "reason": reason,
                "revocation_type": "MANUAL",
            },
        )
    )


async def revoke_expired_permissions(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    batch_size: int = 100,
    registry: AdapterRegistry = adapter_registry,
) -> ExpiryScanResult:
    """回收一批过期权限，并同步申请状态与审计事件。"""

    scan_time = now or utc_now()
    query = (
        select(PermissionInstance, Resource, AccessRequest)
        .join(Resource, Resource.id == PermissionInstance.resource_id)
        .join(AccessRequest, AccessRequest.id == PermissionInstance.request_id)
        .where(
            PermissionInstance.status == PermissionStatus.ACTIVE,
            PermissionInstance.expires_at <= scan_time,
        )
        .order_by(PermissionInstance.expires_at.asc())
        # 跳过其他扫描进程已经锁定的记录，避免同一权限被并发回收。
        .with_for_update(of=PermissionInstance, skip_locked=True)
        .limit(batch_size)
    )
    result = await session.execute(query)
    rows = result.all()

    revoked_count = 0
    failed_count = 0
    affected_requests: dict[UUID, AccessRequest] = {}

    for permission, resource, request in rows:
        affected_requests[request.id] = request
        command = GrantCommand(
            subject_external_id=permission.subject_external_id,
            resource_external_id=resource.external_id,
            permission=permission.permission,
            idempotency_key=f"expiry-revoke:{permission.id}",
        )

        try:
            adapter = registry.get(resource.resource_type)
            operation_result = await adapter.revoke(command)
            still_granted = await adapter.check(command)

            if not operation_result.success or still_granted:
                message = operation_result.message or "撤权后验证仍然存在权限。"
                raise RuntimeError(message)

            permission.status = PermissionStatus.REVOKED
            permission.revoked_at = scan_time
            permission.revocation_reason = "权限到期自动回收"
            revoked_count += 1

            session.add(
                AuditEvent(
                    request_id=request.id,
                    trace_id=request.trace_id,
                    event_type="ACCESS_PERMISSION_REVOKED",
                    actor_external_id="accessmesh-expiry-scanner",
                    payload={
                        "permission_instance_id": str(permission.id),
                        "resource_external_id": resource.external_id,
                        "permission": permission.permission,
                        "operation_id": operation_result.operation_id,
                        "reason": permission.revocation_reason,
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            # 回收失败时保留 ACTIVE，下一轮扫描会继续重试。
            failed_count += 1
            session.add(
                AuditEvent(
                    request_id=request.id,
                    trace_id=request.trace_id,
                    event_type="ACCESS_REVOCATION_FAILED",
                    actor_external_id="accessmesh-expiry-scanner",
                    payload={
                        "permission_instance_id": str(permission.id),
                        "resource_external_id": resource.external_id,
                        "permission": permission.permission,
                        "reason": str(exc),
                    },
                )
            )

    # 先把权限实例状态写入当前事务，再判断每个申请是否已全部回收。
    await session.flush()
    for request in affected_requests.values():
        active_count = await session.scalar(
            select(func.count(PermissionInstance.id)).where(
                PermissionInstance.request_id == request.id,
                PermissionInstance.status == PermissionStatus.ACTIVE,
            )
        )
        if not active_count and request.status != RequestStatus.REVOKED:
            request.status = RequestStatus.REVOKED
            session.add(
                AuditEvent(
                    request_id=request.id,
                    trace_id=request.trace_id,
                    event_type="ACCESS_REQUEST_REVOKED",
                    actor_external_id="accessmesh-expiry-scanner",
                    payload={"reason": "申请关联的权限均已到期回收"},
                )
            )

    return ExpiryScanResult(
        scanned_count=len(rows),
        revoked_count=revoked_count,
        failed_count=failed_count,
    )

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

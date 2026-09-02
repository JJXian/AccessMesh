"""过期权限自动回收服务测试。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from accessmesh.adapters.base import GrantCommand, OperationResult
from accessmesh.adapters.memory import InMemoryResourceAdapter
from accessmesh.db.models import AccessRequest, PermissionInstance, Resource
from accessmesh.domain.enums import (
    Environment,
    PermissionStatus,
    RequestStatus,
    ResourceType,
)
from accessmesh.execution.revocation import revoke_expired_permissions


class FakeRegistry:
    """测试用适配器注册中心。"""

    def __init__(self, adapter: InMemoryResourceAdapter) -> None:
        self._adapter = adapter

    def get(self, _: str) -> InMemoryResourceAdapter:
        """固定返回测试注入的适配器。"""

        return self._adapter


class FailedRevokeAdapter(InMemoryResourceAdapter):
    """模拟外部系统撤权失败的适配器。"""

    async def revoke(self, command: GrantCommand) -> OperationResult:
        """返回失败结果，验证权限实例会留待下一轮重试。"""

        return OperationResult(
            success=False,
            operation_id=command.idempotency_key,
            message="模拟撤权失败",
        )


def build_expired_permission() -> tuple[
    PermissionInstance,
    Resource,
    AccessRequest,
    datetime,
]:
    """构造一组已经到期的权限、资源和申请测试数据。"""

    scan_time = datetime(2026, 9, 2, 12, tzinfo=UTC)
    request = AccessRequest(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        requester_external_id="user-requester",
        subject_external_id="user-requester",
        raw_request="申请支付测试数据库查询权限，有效期 3 天。",
        client_request_id="test-revocation-001",
        status=RequestStatus.ACTIVE,
        trace_id="trace-revocation-001",
    )
    resource = Resource(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        external_id="database:payment-test",
        name="支付测试数据库",
        resource_type=ResourceType.DATABASE,
        environment=Environment.TEST,
        sensitivity="L2",
        owner_external_id="user-approver",
        allowed_permissions=["read_only"],
        enabled=True,
    )
    permission = PermissionInstance(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        request_id=request.id,
        execution_task_id=UUID("44444444-4444-4444-4444-444444444444"),
        subject_external_id="user-requester",
        resource_id=resource.id,
        permission="read_only",
        status=PermissionStatus.ACTIVE,
        external_grant_id="grant-operation-001",
        granted_at=scan_time - timedelta(days=4),
        expires_at=scan_time - timedelta(days=1),
    )
    return permission, resource, request, scan_time


@pytest.mark.asyncio
async def test_expired_permission_is_revoked_and_request_is_closed() -> None:
    """撤权成功后应回收权限，并在没有有效权限时关闭申请。"""

    permission, resource, request, scan_time = build_expired_permission()
    query_result = MagicMock()
    query_result.all.return_value = [(permission, resource, request)]

    session = MagicMock()
    session.execute = AsyncMock(return_value=query_result)
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=0)

    result = await revoke_expired_permissions(
        session,
        now=scan_time,
        registry=FakeRegistry(InMemoryResourceAdapter("database")),
    )

    audit_events = [call.args[0] for call in session.add.call_args_list]

    assert result.scanned_count == 1
    assert result.revoked_count == 1
    assert result.failed_count == 0
    assert permission.status == PermissionStatus.REVOKED
    assert permission.revoked_at == scan_time
    assert permission.revocation_reason == "权限到期自动回收"
    assert request.status == RequestStatus.REVOKED
    assert {event.event_type for event in audit_events} == {
        "ACCESS_PERMISSION_REVOKED",
        "ACCESS_REQUEST_REVOKED",
    }


@pytest.mark.asyncio
async def test_failed_revocation_remains_active_for_retry() -> None:
    """撤权失败时应保留有效状态，并记录失败事件供排查和重试。"""

    permission, resource, request, scan_time = build_expired_permission()
    query_result = MagicMock()
    query_result.all.return_value = [(permission, resource, request)]

    session = MagicMock()
    session.execute = AsyncMock(return_value=query_result)
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=1)

    result = await revoke_expired_permissions(
        session,
        now=scan_time,
        registry=FakeRegistry(FailedRevokeAdapter("database")),
    )

    audit_events = [call.args[0] for call in session.add.call_args_list]

    assert result.scanned_count == 1
    assert result.revoked_count == 0
    assert result.failed_count == 1
    assert permission.status == PermissionStatus.ACTIVE
    assert permission.revoked_at is None
    assert request.status == RequestStatus.ACTIVE
    assert [event.event_type for event in audit_events] == ["ACCESS_REVOCATION_FAILED"]

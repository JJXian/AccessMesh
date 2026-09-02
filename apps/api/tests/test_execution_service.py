"""授权执行服务测试。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from accessmesh.adapters.memory import InMemoryResourceAdapter
from accessmesh.db.models import AccessRequest, ProposedGrant, Resource
from accessmesh.domain.enums import (
    Environment,
    RequestStatus,
    ResourceType,
)
from accessmesh.execution.service import execute_approved_request


class FakeRegistry:
    """测试用适配器注册中心。"""

    def __init__(self, adapter: InMemoryResourceAdapter) -> None:
        self._adapter = adapter

    def get(self, _: str) -> InMemoryResourceAdapter:
        """无论资源类型为何，均返回注入的内存适配器。"""

        return self._adapter


@pytest.mark.asyncio
async def test_execute_approved_request_creates_active_permission() -> None:
    """审批通过的申请执行并验证成功后，应生成有效权限实例。"""

    request = AccessRequest(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        requester_external_id="user-requester",
        subject_external_id="user-requester",
        raw_request="申请支付测试数据库查询权限，有效期 3 天。",
        client_request_id="test-execution-001",
        status=RequestStatus.APPROVED,
        trace_id="trace-execution-001",
    )
    resource = Resource(
        id=UUID("ba17d493-bef0-42bd-a21f-23eb98a7c82e"),
        external_id="database:payment-test",
        name="支付测试数据库",
        resource_type=ResourceType.DATABASE,
        environment=Environment.TEST,
        sensitivity="L2",
        owner_external_id="user-approver",
        allowed_permissions=["connect", "read_only", "read_write"],
        enabled=True,
    )
    grant = ProposedGrant(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        request_id=request.id,
        resource_id=resource.id,
        permission="read_only",
        duration_days=3,
        reason="用于排查支付接口异常。",
        evidence_refs=["planner:basic-rule-v1"],
        plan_version=1,
    )

    execute_result = MagicMock()
    execute_result.all.return_value = [(grant, resource)]

    session = MagicMock()
    session.get = AsyncMock(return_value=request)
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()

    result = await execute_approved_request(
        session=session,
        request_id=request.id,
        actor_external_id="user-approver",
        registry=FakeRegistry(InMemoryResourceAdapter("database")),
    )

    added_objects = [call.args[0] for call in session.add.call_args_list]

    assert result.status == RequestStatus.ACTIVE
    assert any(object_.__class__.__name__ == "ExecutionTask" for object_ in added_objects)
    assert any(object_.__class__.__name__ == "PermissionInstance" for object_ in added_objects)
    assert any(
        object_.__class__.__name__ == "AuditEvent"
        and object_.event_type == "ACCESS_EXECUTION_COMPLETED"
        for object_ in added_objects
    )
    session.flush.assert_awaited_once()

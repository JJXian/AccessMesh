"""身份与资源上下文加载器测试。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from accessmesh.context.resource_context import ResourceContextLoader
from accessmesh.db.models import DemoUser, Resource
from accessmesh.domain.enums import Environment, ResourceType, SubjectType


@pytest.mark.asyncio
async def test_loader_returns_subject_and_enabled_resources() -> None:
    """加载器应返回权限主体和已启用资源的工作流上下文。"""

    subject = DemoUser(
        # 测试不写真实数据库，因此手动模拟已存在记录的主键。
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        external_id="user-requester",
        username="requester",
        display_name="演示申请人",
        role="requester",
        subject_type=SubjectType.EMPLOYEE,
        department="支付研发部",
        employment_status="active",
    )
    enabled_resource = Resource(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        external_id="database:payment-test",
        name="支付测试数据库",
        resource_type=ResourceType.DATABASE,
        environment=Environment.TEST,
        sensitivity="L2",
        owner_external_id="user-approver",
        allowed_permissions=["connect", "read_only", "read_write"],
        enabled=True,
    )

    scalar_result = MagicMock()
    scalar_result.all.return_value = [enabled_resource]

    session = MagicMock()
    # scalar 用于查询单个权限主体。
    session.scalar = AsyncMock(return_value=subject)
    # scalars 用于查询多个资源。
    session.scalars = AsyncMock(return_value=scalar_result)

    result = await ResourceContextLoader(session).load(
        {
            "subject_external_id": "user-requester",
        }
    )

    assert result["status"] == "PLANNING"
    assert result["identity_context"] == {
        "subject": {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "external_id": "user-requester",
            "username": "requester",
            "display_name": "演示申请人",
            "role": "requester",
            "subject_type": "employee",
            "department": "支付研发部",
            "employment_status": "active",
        }
    }
    assert result["resource_context"]["resources"] == [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "external_id": "database:payment-test",
            "name": "支付测试数据库",
            "resource_type": "database",
            "environment": "test",
            "sensitivity": "L2",
            "owner_external_id": "user-approver",
            "allowed_permissions": [
                "connect",
                "read_only",
                "read_write",
            ],
            "enabled": True,
        }
    ]
    session.scalar.assert_awaited_once()
    session.scalars.assert_awaited_once()

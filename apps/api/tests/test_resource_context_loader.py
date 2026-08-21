"""资源上下文加载器测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from accessmesh.context.resource_context import ResourceContextLoader
from accessmesh.db.models import Resource
from accessmesh.domain.enums import Environment, ResourceType
from uuid import UUID

@pytest.mark.asyncio
async def test_loader_returns_only_enabled_resources() -> None:
    """加载器应把查询到的启用资源转换为工作流上下文。"""

    enabled_resource = Resource(
        # 当前是模拟数据库记录，必须手动补齐数据库通常会生成的主键。
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

    # MagicMock 模拟 SQLAlchemy 查询结果。
    scalar_result = MagicMock()
    scalar_result.all.return_value = [enabled_resource]

    # AsyncMock 模拟 await session.scalars(...) 这个异步数据库调用。
    session = MagicMock()
    session.scalars = AsyncMock(return_value=scalar_result)

    result = await ResourceContextLoader(session).load({})

    assert result["status"] == "PLANNING"
    assert result["identity_context"] == {}
    assert result["resource_context"]["resources"] == [
        {
            "id": str(enabled_resource.id),
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
    session.scalars.assert_awaited_once()
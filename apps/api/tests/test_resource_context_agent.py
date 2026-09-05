"""资源上下文 Agent 测试。"""

from uuid import UUID

import pytest

from accessmesh.agents.resource_context import ResourceContextAgent
from accessmesh.db.models import Resource
from accessmesh.domain.enums import Environment, ResourceType


class FakeResourceLookup:
    """仅提供已启用资源读取能力的测试工具。"""

    def __init__(self, resources: list[Resource]) -> None:
        self.resources = resources
        self.call_count = 0

    async def list_enabled_resources(self) -> list[Resource]:
        """记录调用次数并返回预设资源。"""

        self.call_count += 1
        return self.resources


def build_resource() -> Resource:
    """创建不依赖真实数据库的演示资源。"""

    return Resource(
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


@pytest.mark.asyncio
async def test_resource_agent_collects_normalized_resource_context() -> None:
    """Agent 应通过只读工具加载资源，并转换成标准 JSON 数据。"""

    lookup = FakeResourceLookup([build_resource()])

    result = await ResourceContextAgent(lookup).collect({})

    assert lookup.call_count == 1
    assert result == {
        "resource_context": {
            "resources": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "external_id": "database:payment-test",
                    "name": "支付测试数据库",
                    "resource_type": "database",
                    "environment": "test",
                    "sensitivity": "L2",
                    "owner_external_id": "user-approver",
                    "allowed_permissions": ["connect", "read_only", "read_write"],
                    "enabled": True,
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_resource_agent_keeps_empty_catalog_as_empty_context() -> None:
    """资源目录为空时应返回空集合，不能凭空生成候选资源。"""

    lookup = FakeResourceLookup([])

    result = await ResourceContextAgent(lookup).collect({})

    assert lookup.call_count == 1
    assert result == {"resource_context": {"resources": []}}

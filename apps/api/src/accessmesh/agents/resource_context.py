"""收集可申请资源上下文的只读 Agent。"""

from typing import Any, Protocol

from accessmesh.db.models import Resource
from accessmesh.domain.schemas import ResourceRead
from accessmesh.graph.state import AccessRequestState


class ResourceLookupTool(Protocol):
    """资源 Agent 唯一允许使用的只读工具契约。"""

    async def list_enabled_resources(self) -> list[Resource]:
        """读取所有已启用资源，不允许创建、修改或授权资源。"""


class ResourceContextAgent:
    """查询并规范化资源目录，不参与权限授予或回收。"""

    def __init__(self, resource_lookup: ResourceLookupTool) -> None:
        """只注入资源查询工具，限制 Agent 可以使用的能力。"""

        self._resource_lookup = resource_lookup

    async def collect(self, _: AccessRequestState) -> dict[str, Any]:
        """读取已启用资源，并返回可安全写入 LangGraph 的 JSON 数据。"""

        resources = await self._resource_lookup.list_enabled_resources()
        resource_payloads = [
            ResourceRead.model_validate(resource).model_dump(mode="json") for resource in resources
        ]
        return {
            "resource_context": {
                "resources": resource_payloads,
            }
        }

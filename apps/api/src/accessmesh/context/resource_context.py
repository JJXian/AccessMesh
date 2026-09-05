"""权限申请工作流需要的资源上下文加载器。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.agents.identity_context import IdentityContextAgent
from accessmesh.db.models import Resource
from accessmesh.domain.schemas import ResourceRead
from accessmesh.graph.state import AccessRequestState
from accessmesh.identity.provider import DemoIdentityProvider


class ResourceContextLoader:
    """组合身份 Agent 与资源查询，提供兼容现有工作流的上下文入口。"""

    def __init__(self, session: AsyncSession) -> None:
        """保存当前 API 请求的数据库会话。"""

        self._session = session
        self._identity_agent = IdentityContextAgent(DemoIdentityProvider(session))

    async def load(self, state: AccessRequestState) -> dict[str, Any]:
        """分别加载身份和资源，并转换为工作流可传递的 JSON 数据。"""

        identity_result = await self._identity_agent.collect(state)

        query = select(Resource).where(Resource.enabled.is_(True)).order_by(Resource.name)
        result = await self._session.scalars(query)
        resources = result.all()

        # ORM 模型不能直接安全地放进工作流状态。
        # 先转为 Pydantic 模型，再转成标准 JSON 字典。
        resource_payloads = [
            ResourceRead.model_validate(resource).model_dump(mode="json") for resource in resources
        ]

        return {
            **identity_result,
            "resource_context": {
                "resources": resource_payloads,
            },
            "status": "PLANNING",
        }

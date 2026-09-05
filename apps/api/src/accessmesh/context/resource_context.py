"""权限申请工作流需要的资源上下文加载器。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.agents.identity_context import IdentityContextAgent
from accessmesh.agents.resource_context import ResourceContextAgent
from accessmesh.db.models import Resource
from accessmesh.db.session import AsyncSessionLocal
from accessmesh.graph.state import AccessRequestState
from accessmesh.identity.provider import DemoIdentityProvider


class PostgresResourceLookup:
    """从 PostgreSQL 资源目录执行只读查询。"""

    def __init__(self, session: AsyncSession) -> None:
        """保存当前请求的数据库会话。"""

        self._session = session

    async def list_enabled_resources(self) -> list[Resource]:
        """按名称排序返回所有已启用资源。"""

        query = select(Resource).where(Resource.enabled.is_(True)).order_by(Resource.name)
        result = await self._session.scalars(query)
        return list(result.all())


class ResourceContextLoader:
    """组合身份 Agent 与资源查询，提供兼容现有工作流的上下文入口。"""

    def __init__(self, session: AsyncSession) -> None:
        """保存当前 API 请求的数据库会话。"""

        self._session = session
        self._identity_agent = IdentityContextAgent(DemoIdentityProvider(session))
        self._resource_agent = ResourceContextAgent(PostgresResourceLookup(session))

    async def load(self, state: AccessRequestState) -> dict[str, Any]:
        """分别加载身份和资源，并转换为工作流可传递的 JSON 数据。"""

        identity_result = await self._identity_agent.collect(state)
        resource_result = await self._resource_agent.collect(state)

        return {
            **identity_result,
            **resource_result,
            "status": "PLANNING",
        }


async def load_identity_context(state: AccessRequestState) -> dict[str, Any]:
    """使用独立数据库会话运行身份 Agent，允许与资源查询安全并发。"""

    async with AsyncSessionLocal() as session:
        agent = IdentityContextAgent(DemoIdentityProvider(session))
        return await agent.collect(state)


async def load_resource_context(state: AccessRequestState) -> dict[str, Any]:
    """使用独立数据库会话运行资源 Agent，允许与身份查询安全并发。"""

    async with AsyncSessionLocal() as session:
        agent = ResourceContextAgent(PostgresResourceLookup(session))
        return await agent.collect(state)

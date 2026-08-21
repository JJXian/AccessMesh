"""权限申请工作流需要的资源上下文加载器。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.db.models import Resource
from accessmesh.domain.schemas import ResourceRead
from accessmesh.graph.state import AccessRequestState


class ResourceContextLoader:
    """从 PostgreSQL 资源目录加载规划器需要的资源上下文。"""

    def __init__(self, session: AsyncSession) -> None:
        """保存当前 API 请求的数据库会话。"""

        self._session = session

    async def load(self, state: AccessRequestState) -> dict[str, Any]:
        """查询已启用资源，并转换为工作流可传递的 JSON 数据。"""

        query = (
            select(Resource)
            .where(Resource.enabled.is_(True))
            .order_by(Resource.name)
        )
        result = await self._session.scalars(query)
        resources = result.all()

        # ORM 模型不能直接安全地放进工作流状态。
        # 先转成 Pydantic 模型，再转成标准 JSON 字典。
        resource_payloads = [
            ResourceRead.model_validate(resource).model_dump(mode="json")
            for resource in resources
        ]

        return {
            # 身份上下文暂时沿用已有值；下一阶段会在这里补充用户、部门和角色等信息。
            "identity_context": state.get("identity_context", {}),
            "resource_context": {
                "resources": resource_payloads,
            },
            "status": "PLANNING",
        }
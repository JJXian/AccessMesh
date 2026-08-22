"""权限申请工作流需要的身份与资源上下文加载器。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.db.models import DemoUser, Resource
from accessmesh.domain.schemas import DemoUserRead, ResourceRead
from accessmesh.graph.state import AccessRequestState


class SubjectNotFoundError(ValueError):
    """权限申请指定的主体不存在时抛出的异常。"""


class ResourceContextLoader:
    """从 PostgreSQL 加载 OPA 和规划器需要的身份、资源上下文。"""

    def __init__(self, session: AsyncSession) -> None:
        """保存当前 API 请求的数据库会话。"""

        self._session = session

    async def load(self, state: AccessRequestState) -> dict[str, Any]:
        """查询权限主体与已启用资源，并转换为工作流可传递的 JSON 数据。"""

        subject_external_id = state.get("subject_external_id")
        if not subject_external_id:
            raise SubjectNotFoundError("上下文加载缺少权限主体外部标识。")

        # 权限主体不一定等于申请发起人。
        # 例如主管可为团队成员申请权限，因此必须按 subject_external_id 查询。
        subject = await self._session.scalar(
            select(DemoUser).where(DemoUser.external_id == subject_external_id)
        )
        if subject is None:
            raise SubjectNotFoundError(f"权限主体不存在：{subject_external_id}")

        query = select(Resource).where(Resource.enabled.is_(True)).order_by(Resource.name)
        result = await self._session.scalars(query)
        resources = result.all()

        # ORM 模型不能直接安全地放进工作流状态。
        # 先转为 Pydantic 模型，再转成标准 JSON 字典。
        subject_payload = DemoUserRead.model_validate(subject).model_dump(mode="json")
        resource_payloads = [
            ResourceRead.model_validate(resource).model_dump(mode="json") for resource in resources
        ]

        return {
            "identity_context": {
                "subject": subject_payload,
            },
            "resource_context": {
                "resources": resource_payloads,
            },
            "status": "PLANNING",
        }

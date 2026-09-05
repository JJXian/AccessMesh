"""收集权限主体身份上下文的只读 Agent。"""

from typing import Any, Protocol

from accessmesh.db.models import DemoUser
from accessmesh.domain.schemas import DemoUserRead
from accessmesh.graph.state import AccessRequestState


class IdentityLookupTool(Protocol):
    """身份 Agent 唯一允许使用的只读工具契约。"""

    async def get_user(self, external_id: str) -> DemoUser | None:
        """根据外部身份标识读取用户，不允许修改身份数据。"""


class SubjectNotFoundError(ValueError):
    """权限申请指定的主体不存在时抛出的异常。"""


class IdentityContextAgent:
    """查询并规范化权限主体身份信息，不参与审批或授权。"""

    def __init__(self, identity_lookup: IdentityLookupTool) -> None:
        """只注入身份查询工具，限制 Agent 可以使用的能力。"""

        self._identity_lookup = identity_lookup

    async def collect(self, state: AccessRequestState) -> dict[str, Any]:
        """读取权限主体，并返回可安全写入 LangGraph 的 JSON 数据。"""

        subject_external_id = state.get("subject_external_id")
        if not subject_external_id:
            raise SubjectNotFoundError("身份上下文缺少权限主体外部标识。")

        # 权限主体不一定等于申请发起人，例如主管可以为团队成员申请权限。
        subject = await self._identity_lookup.get_user(subject_external_id)
        if subject is None:
            raise SubjectNotFoundError(f"权限主体不存在：{subject_external_id}")

        # ORM 对象不直接进入工作流，避免数据库会话状态泄漏到 Agent 状态中。
        subject_payload = DemoUserRead.model_validate(subject).model_dump(mode="json")
        return {
            "identity_context": {
                "subject": subject_payload,
            }
        }

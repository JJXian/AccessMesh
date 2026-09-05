"""身份上下文 Agent 测试。"""

from uuid import UUID

import pytest

from accessmesh.agents.identity_context import IdentityContextAgent, SubjectNotFoundError
from accessmesh.db.models import DemoUser
from accessmesh.domain.enums import SubjectType


class FakeIdentityLookup:
    """仅提供身份读取能力的测试工具。"""

    def __init__(self, subject: DemoUser | None) -> None:
        self.subject = subject
        self.requested_external_ids: list[str] = []

    async def get_user(self, external_id: str) -> DemoUser | None:
        """记录查询参数并返回预设身份。"""

        self.requested_external_ids.append(external_id)
        return self.subject


def build_subject() -> DemoUser:
    """创建不依赖真实数据库的演示身份。"""

    return DemoUser(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        external_id="user-requester",
        username="requester",
        display_name="演示申请人",
        role="requester",
        subject_type=SubjectType.EMPLOYEE,
        department="支付研发部",
        employment_status="active",
    )


@pytest.mark.asyncio
async def test_identity_agent_collects_normalized_subject_context() -> None:
    """Agent 应只查询目标主体，并返回可序列化的结构化上下文。"""

    lookup = FakeIdentityLookup(build_subject())

    result = await IdentityContextAgent(lookup).collect({"subject_external_id": "user-requester"})

    assert lookup.requested_external_ids == ["user-requester"]
    assert result == {
        "identity_context": {
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
    }


@pytest.mark.asyncio
async def test_identity_agent_rejects_missing_subject_id_without_querying_tool() -> None:
    """缺少主体标识时应立即失败，不能猜测或扫描用户目录。"""

    lookup = FakeIdentityLookup(build_subject())

    with pytest.raises(SubjectNotFoundError, match="缺少权限主体外部标识"):
        await IdentityContextAgent(lookup).collect({})

    assert lookup.requested_external_ids == []


@pytest.mark.asyncio
async def test_identity_agent_rejects_unknown_subject() -> None:
    """身份工具找不到主体时，Agent 应明确失败而不是虚构身份。"""

    lookup = FakeIdentityLookup(None)

    with pytest.raises(SubjectNotFoundError, match="权限主体不存在：unknown-user"):
        await IdentityContextAgent(lookup).collect({"subject_external_id": "unknown-user"})

    assert lookup.requested_external_ids == ["unknown-user"]

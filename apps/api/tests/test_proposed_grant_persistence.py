"""候选授权方案持久化服务测试。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from accessmesh.db.models import Resource
from accessmesh.domain.enums import Environment, ResourceType
from accessmesh.domain.schemas import CandidateGrant
from accessmesh.planning.persistence import persist_proposed_grants


@pytest.mark.asyncio
async def test_persist_proposed_grants_resolves_resource_id() -> None:
    """应将资源外部标识转换为数据库资源主键后再保存。"""

    resource = Resource(
        # 测试不写真实数据库，因此手动模拟已存在资源的主键。
        id=UUID("ba17d493-bef0-42bd-a21f-23eb98a7c82e"),
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
    scalar_result.all.return_value = [resource]

    session = MagicMock()
    session.scalars = AsyncMock(return_value=scalar_result)
    session.flush = AsyncMock()

    request_id = UUID("11111111-1111-1111-1111-111111111111")
    grants = [
        CandidateGrant(
            resource_external_id="database:payment-test",
            permission="read_only",
            duration_days=3,
            reason="用于排查支付接口异常。",
            evidence_refs=["planner:basic-rule-v1"],
        )
    ]

    result = await persist_proposed_grants(
        session=session,
        request_id=request_id,
        grants=grants,
    )

    assert len(result) == 1
    assert result[0].request_id == request_id
    assert result[0].resource_id == resource.id
    assert result[0].permission == "read_only"
    assert result[0].duration_days == 3
    assert result[0].plan_version == 1
    session.add_all.assert_called_once_with(result)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_proposed_grants_rejects_unknown_resource() -> None:
    """候选方案引用不存在资源时，不能写入数据库。"""

    scalar_result = MagicMock()
    scalar_result.all.return_value = []

    session = MagicMock()
    session.scalars = AsyncMock(return_value=scalar_result)
    session.flush = AsyncMock()

    grants = [
        CandidateGrant(
            resource_external_id="database:not-exists",
            permission="read_only",
            duration_days=1,
            reason="测试不存在资源。",
        )
    ]

    with pytest.raises(
        ValueError,
        match="候选方案引用了不存在的资源：database:not-exists",
    ):
        await persist_proposed_grants(
            session=session,
            request_id=UUID("11111111-1111-1111-1111-111111111111"),
            grants=grants,
        )

    session.add_all.assert_not_called()
    session.flush.assert_not_awaited()

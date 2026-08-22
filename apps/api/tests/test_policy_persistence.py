"""OPA 策略决策持久化服务测试。"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from accessmesh.db.models import ProposedGrant, Resource
from accessmesh.domain.enums import Environment, RequestStatus, ResourceType
from accessmesh.policy.persistence import (
    persist_policy_decisions,
    resolve_request_status,
)


@pytest.mark.asyncio
async def test_persist_policy_decisions_links_to_proposed_grant() -> None:
    """策略决策应关联到对应的候选授权方案。"""

    request_id = UUID("11111111-1111-1111-1111-111111111111")
    resource = Resource(
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
    proposed_grant = ProposedGrant(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        request_id=request_id,
        resource_id=resource.id,
        permission="read_only",
        duration_days=3,
        reason="用于排查支付接口异常。",
        evidence_refs=["planner:basic-rule-v1"],
        plan_version=1,
    )

    execute_result = MagicMock()
    execute_result.all.return_value = [(proposed_grant, resource)]

    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.flush = AsyncMock()

    result = await persist_policy_decisions(
        session=session,
        request_id=request_id,
        raw_decisions=[
            {
                "resource_external_id": "database:payment-test",
                "permission": "read_only",
                "policy_input": {
                    "subject": {
                        "subject_type": "employee",
                        "employment_status": "active",
                    },
                    "resource": {
                        "environment": "test",
                        "enabled": True,
                        "allowed_permissions": ["read_only"],
                    },
                    "grant": {
                        "permission": "read_only",
                        "duration_days": 3,
                    },
                },
                "allow": True,
                "risk_level": "medium",
                "violations": [],
                "required_approvals": ["approver"],
                "max_duration_days": 30,
                "policy_version": "test-v1",
            }
        ],
    )

    assert len(result) == 1
    assert result[0].request_id == request_id
    assert result[0].proposed_grant_id == proposed_grant.id
    assert result[0].allow is True
    assert result[0].required_approvals == ["approver"]
    assert result[0].policy_version == "test-v1"
    session.add_all.assert_called_once_with(result)
    session.flush.assert_awaited_once()


def test_resolve_request_status_requires_approval_when_all_allowed() -> None:
    """所有候选方案通过策略后，应进入待审批状态。"""

    allowed_decision = MagicMock(allow=True)

    result = resolve_request_status(
        grant_count=1,
        policy_decisions=[allowed_decision],
    )

    assert result == RequestStatus.PENDING_APPROVAL


def test_resolve_request_status_denies_when_any_grant_is_denied() -> None:
    """任意候选方案被拒绝时，整单必须进入策略拒绝状态。"""

    allowed_decision = MagicMock(allow=True)
    denied_decision = MagicMock(allow=False)

    result = resolve_request_status(
        grant_count=2,
        policy_decisions=[allowed_decision, denied_decision],
    )

    assert result == RequestStatus.POLICY_DENIED


def test_resolve_request_status_requires_clarification_without_grants() -> None:
    """没有候选方案时，应要求用户补充申请信息。"""

    result = resolve_request_status(
        grant_count=0,
        policy_decisions=[],
    )

    assert result == RequestStatus.NEED_CLARIFICATION

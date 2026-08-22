"""OPA 工作流评估器测试。"""

from typing import Any

import pytest

from accessmesh.domain.schemas import PolicyDecision
from accessmesh.policy.evaluator import OpaPolicyEvaluator


class FakePolicyClient:
    """测试用 OPA 客户端：记录输入，并返回固定允许决策。"""

    def __init__(self) -> None:
        self.inputs: list[dict[str, Any]] = []

    async def evaluate(self, policy_input: dict[str, Any]) -> PolicyDecision:
        """记录收到的策略输入，模拟 OPA 返回结果。"""

        self.inputs.append(policy_input)
        return PolicyDecision(
            allow=True,
            risk_level="medium",
            violations=[],
            required_approvals=["approver"],
            max_duration_days=30,
            policy_version="test-v1",
        )


@pytest.mark.asyncio
async def test_evaluator_builds_opa_input_for_each_grant() -> None:
    """每条候选权限都应独立生成 OPA 输入和策略决策。"""

    policy_client = FakePolicyClient()
    evaluator = OpaPolicyEvaluator(policy_client)

    result = await evaluator.evaluate(
        {
            "identity_context": {
                "subject": {
                    "external_id": "user-requester",
                    "subject_type": "employee",
                    "employment_status": "active",
                    "department": "支付研发部",
                }
            },
            "resource_context": {
                "resources": [
                    {
                        "external_id": "database:payment-test",
                        "name": "支付测试数据库",
                        "environment": "test",
                        "enabled": True,
                        "allowed_permissions": [
                            "connect",
                            "read_only",
                            "read_write",
                        ],
                    }
                ]
            },
            "proposed_grants": [
                {
                    "resource_external_id": "database:payment-test",
                    "permission": "read_only",
                    "duration_days": 30,
                    "reason": "用于排查支付接口异常。",
                    "evidence_refs": ["planner:basic-rule-v1"],
                }
            ],
        }
    )

    assert result["status"] == "POLICY_EVALUATED"
    assert len(result["policy_decisions"]) == 1

    decision = result["policy_decisions"][0]
    assert decision["resource_external_id"] == "database:payment-test"
    assert decision["permission"] == "read_only"
    assert decision["allow"] is True
    assert decision["required_approvals"] == ["approver"]
    assert decision["policy_version"] == "test-v1"

    # 验证真正传给 OPA 的输入结构与 Rego 中的 input 路径一致。
    assert policy_client.inputs == [
        {
            "subject": {
                "external_id": "user-requester",
                "subject_type": "employee",
                "employment_status": "active",
                "department": "支付研发部",
            },
            "resource": {
                "external_id": "database:payment-test",
                "name": "支付测试数据库",
                "environment": "test",
                "enabled": True,
                "allowed_permissions": [
                    "connect",
                    "read_only",
                    "read_write",
                ],
            },
            "grant": {
                "resource_external_id": "database:payment-test",
                "permission": "read_only",
                "duration_days": 30,
                "reason": "用于排查支付接口异常。",
                "evidence_refs": ["planner:basic-rule-v1"],
            },
        }
    ]


@pytest.mark.asyncio
async def test_evaluator_rejects_grant_without_matching_resource() -> None:
    """候选权限找不到对应资源时，不能向 OPA 发送不完整输入。"""

    evaluator = OpaPolicyEvaluator(FakePolicyClient())

    with pytest.raises(
        ValueError,
        match="策略评估找不到候选方案对应的资源：database:not-exists",
    ):
        await evaluator.evaluate(
            {
                "identity_context": {
                    "subject": {
                        "subject_type": "employee",
                        "employment_status": "active",
                    }
                },
                "resource_context": {"resources": []},
                "proposed_grants": [
                    {
                        "resource_external_id": "database:not-exists",
                        "permission": "read_only",
                        "duration_days": 1,
                        "reason": "测试异常路径。",
                    }
                ],
            }
        )

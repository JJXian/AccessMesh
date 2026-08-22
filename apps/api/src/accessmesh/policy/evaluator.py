"""将候选授权方案提交给 OPA 进行策略评估。"""

from typing import Any, Protocol

from accessmesh.domain.schemas import CandidateGrant, PolicyDecision
from accessmesh.graph.state import AccessRequestState


class PolicyClient(Protocol):
    """OPA 客户端需要满足的最小接口。"""

    async def evaluate(self, policy_input: dict[str, Any]) -> PolicyDecision:
        """提交策略输入并返回结构化策略决策。"""


class OpaPolicyEvaluator:
    """逐条评估候选权限，并生成可持久化的策略决策数据。"""

    def __init__(self, policy_client: PolicyClient) -> None:
        """注入 OPA 客户端，便于测试时替换为模拟客户端。"""

        self._policy_client = policy_client

    async def evaluate(self, state: AccessRequestState) -> dict[str, Any]:
        """对当前工作流中的每条候选权限执行 OPA 策略判断。"""

        subject = state.get("identity_context", {}).get("subject")
        if not isinstance(subject, dict):
            raise ValueError("策略评估缺少权限主体上下文。")

        raw_resources = state.get("resource_context", {}).get("resources", [])
        resources_by_external_id = {resource["external_id"]: resource for resource in raw_resources}

        policy_decisions: list[dict[str, Any]] = []

        for raw_grant in state.get("proposed_grants", []):
            # 先转为领域模型，避免未经校验的工作流状态直接进入策略层。
            grant = CandidateGrant.model_validate(raw_grant)
            resource = resources_by_external_id.get(grant.resource_external_id)

            if resource is None:
                raise ValueError(f"策略评估找不到候选方案对应的资源：{grant.resource_external_id}")

            # 这个字典结构必须与 policies/access.rego 中的 input 路径一致。
            policy_input = {
                "subject": subject,
                "resource": resource,
                "grant": grant.model_dump(mode="json"),
            }
            decision = await self._policy_client.evaluate(policy_input)

            # 除 OPA 返回值外，保留资源和权限标识、以及完整输入快照。
            # 下一步写入 policy_decisions 表时会使用这些字段。
            policy_decisions.append(
                {
                    "resource_external_id": grant.resource_external_id,
                    "permission": grant.permission,
                    "policy_input": policy_input,
                    **decision.model_dump(mode="json"),
                }
            )

        return {
            "policy_decisions": policy_decisions,
            "status": "POLICY_EVALUATED",
        }

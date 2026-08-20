"""基于确定性规则生成最小权限候选方案。

第一版不依赖 LLM：它根据意图中的资源提示、动作提示和资源允许权限，
生成可预测、可测试的最小权限方案。
"""

from collections.abc import Sequence

from accessmesh.domain.schemas import CandidateGrant, ParsedIntent, PlanResult, ResourceRead

# 这些关键词表达“用户需要修改资源”，风险通常高于只读。
WRITE_KEYWORDS = ("写", "修改", "更新", "删除", "创建", "提交", "开发")

# 这些关键词表达“用户只需要查看资源”。
READ_KEYWORDS = ("读", "查", "查看", "查询", "读取", "分析", "排查", "只读")


class BasicPlanner:
    """根据结构化意图和资源目录，生成最小权限候选方案。"""

    def create_plan(
        self,
        intent: ParsedIntent,
        resources: Sequence[ResourceRead],
    ) -> PlanResult:
        """为一次申请生成候选权限方案。

        如果资源信息不足或资源不存在，不猜测目标资源，而是返回空方案，
        并在 assumptions 中说明原因。后续工作流会根据这些信息要求用户补充。
        """

        assumptions: list[str] = []

        # 申请文本中没有资源提示时，不能安全地给出授权建议。
        if not intent.resource_hints:
            return PlanResult(
                assumptions=["未识别到目标资源，无法生成候选授权方案。"],
            )

        matched_resources = self._find_matching_resources(intent.resource_hints, resources)
        if not matched_resources:
            return PlanResult(
                assumptions=["资源目录中未找到与申请匹配的目标资源。"],
            )

        # 第一版约定：未明确填写时长时，先建议 7 天。
        # 这不是最终策略；后面 OPA 会进一步限制时长和高风险资源。
        duration_days = intent.duration_days
        if duration_days is None:
            duration_days = 7
            assumptions.append("申请未明确授权时长，暂按 7 天生成候选方案。")

        grants: list[CandidateGrant] = []
        for resource in matched_resources:
            permission = self._choose_least_privilege_permission(
                allowed_permissions=resource.allowed_permissions,
                action_hints=intent.action_hints,
            )

            # 找不到一个能满足需求的允许权限时，宁可不生成方案，也不能猜一个权限。
            if permission is None:
                assumptions.append(
                    f"资源“{resource.name}”没有可匹配的允许权限，未生成授权建议。"
                )
                continue

            grants.append(
                CandidateGrant(
                    resource_external_id=resource.external_id,
                    permission=permission,
                    duration_days=duration_days,
                    reason=self._build_reason(resource.name, permission, intent.task),
                    evidence_refs=[
                        f"resource:{resource.external_id}",
                        "planner:basic-rule-v1",
                    ],
                )
            )

        return PlanResult(grants=grants, assumptions=assumptions)

    def _find_matching_resources(
        self,
        resource_hints: Sequence[str],
        resources: Sequence[ResourceRead],
    ) -> list[ResourceRead]:
        """根据资源提示，在资源外部标识和资源名称中查找匹配项。"""

        matched_resources: list[ResourceRead] = []

        for resource in resources:
            searchable_text = f"{resource.external_id} {resource.name}".lower()

            # 例如“支付测试数据库”可以匹配 name，
            # “database:payment-test”可以匹配 external_id。
            if any(hint.lower() in searchable_text for hint in resource_hints):
                matched_resources.append(resource)

        return matched_resources

    def _choose_least_privilege_permission(
        self,
        allowed_permissions: Sequence[str],
        action_hints: Sequence[str],
    ) -> str | None:
        """从资源允许权限中选择满足动作需求的最低权限。"""

        action_text = " ".join(action_hints)

        # 对“写”类操作，优先选择资源允许的低风险写权限。
        if any(keyword in action_text for keyword in WRITE_KEYWORDS):
            preferred_permissions = (
                "read_write",
                "developer",
                "maintainer",
                "ddl_admin",
            )
        # 未明确动作或明显是“读”类操作时，优先选择只读权限。
        else:
            preferred_permissions = (
                "read_only",
                "reporter",
                "guest",
                "connect",
                "read_write",
                "developer",
                "maintainer",
                "ddl_admin",
            )

        for permission in preferred_permissions:
            if permission in allowed_permissions:
                return permission

        return None

    def _build_reason(
        self,
        resource_name: str,
        permission: str,
        task: str | None,
    ) -> str:
        """构造可进入审批和审计记录的、可读的推荐理由。"""

        task_description = task or "完成当前申请任务"
        return (
            f"为完成“{task_description}”，"
            f"建议在资源“{resource_name}”上授予“{permission}”权限。"
        )
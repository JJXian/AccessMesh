"""OPA 策略决策的持久化和申请状态归并逻辑。"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.db.models import PolicyDecisionRecord, ProposedGrant, Resource
from accessmesh.domain.enums import RequestStatus
from accessmesh.domain.schemas import PolicyDecision


async def persist_policy_decisions(
    session: AsyncSession,
    request_id: UUID,
    raw_decisions: Sequence[dict[str, Any]],
) -> list[PolicyDecisionRecord]:
    """将工作流中的策略决策写入 policy_decisions 表。"""

    if not raw_decisions:
        return []

    # 查询本次申请的候选方案及其关联资源。
    # 这样可以通过“资源外部标识 + 权限”定位到对应 proposed_grant_id。
    query = (
        select(ProposedGrant, Resource)
        .join(Resource, Resource.id == ProposedGrant.resource_id)
        .where(ProposedGrant.request_id == request_id)
    )
    result = await session.execute(query)
    grants_by_key = {
        (resource.external_id, proposed_grant.permission): proposed_grant
        for proposed_grant, resource in result.all()
    }

    records: list[PolicyDecisionRecord] = []

    for raw_decision in raw_decisions:
        resource_external_id = raw_decision["resource_external_id"]
        permission = raw_decision["permission"]
        proposed_grant = grants_by_key.get((resource_external_id, permission))

        if proposed_grant is None:
            raise ValueError(f"策略决策找不到对应候选方案：{resource_external_id} / {permission}")

        # 只校验真正由 OPA 返回的字段。
        # resource_external_id、permission、policy_input 是工作流为关联和审计额外补充的字段。
        decision = PolicyDecision.model_validate(raw_decision)

        records.append(
            PolicyDecisionRecord(
                request_id=request_id,
                proposed_grant_id=proposed_grant.id,
                policy_input=raw_decision["policy_input"],
                allow=decision.allow,
                risk_level=decision.risk_level,
                violations=decision.violations,
                required_approvals=decision.required_approvals,
                max_duration_days=decision.max_duration_days,
                policy_version=decision.policy_version,
            )
        )

    session.add_all(records)

    # 提前执行 INSERT，让唯一约束、外键等问题在本函数中暴露。
    # 不 commit，仍由 API 路由统一提交整个事务。
    await session.flush()

    return records


def resolve_request_status(
    grant_count: int,
    policy_decisions: Sequence[PolicyDecisionRecord],
) -> RequestStatus:
    """根据候选方案与策略决策的整体结果确定申请下一状态。"""

    # 没有方案，通常意味着资源、操作或时长信息不足，需要用户补充。
    if grant_count == 0:
        return RequestStatus.NEED_CLARIFICATION

    # 每条候选方案都必须有一条策略结论。
    # 数量不一致说明工作流或持久化链路出现异常，不能冒险继续。
    if len(policy_decisions) != grant_count:
        raise ValueError("候选方案数量与策略决策数量不一致。")

    # 所有候选权限均被允许后，才可以进入人工审批。
    if all(decision.allow for decision in policy_decisions):
        return RequestStatus.PENDING_APPROVAL

    # 只要有一条被拒绝，整单进入策略拒绝状态。
    return RequestStatus.POLICY_DENIED

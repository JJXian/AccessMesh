"""候选授权方案的数据库持久化逻辑。"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.db.models import ProposedGrant, Resource
from accessmesh.domain.schemas import CandidateGrant


async def persist_proposed_grants(
    session: AsyncSession,
    request_id: UUID,
    grants: Sequence[CandidateGrant],
    plan_version: int = 1,
) -> list[ProposedGrant]:
    """将规划器生成的候选授权方案保存到 proposed_grants 表。

    规划器只使用 resource_external_id，避免它直接依赖数据库主键；
    持久化时再将外部资源标识转换为 resources.id。
    """

    if not grants:
        return []

    resource_external_ids = {grant.resource_external_id for grant in grants}

    query = select(Resource).where(Resource.external_id.in_(resource_external_ids))
    result = await session.scalars(query)
    resources_by_external_id = {resource.external_id: resource for resource in result.all()}

    proposed_grants: list[ProposedGrant] = []

    for grant in grants:
        resource = resources_by_external_id.get(grant.resource_external_id)

        # 正常情况下不会发生：方案里的资源来自刚刚查询到的资源上下文。
        # 但这里仍需防御式校验，避免写入无法关联资源的候选方案。
        if resource is None:
            raise ValueError(f"候选方案引用了不存在的资源：{grant.resource_external_id}")

        proposed_grants.append(
            ProposedGrant(
                request_id=request_id,
                resource_id=resource.id,
                permission=grant.permission,
                duration_days=grant.duration_days,
                reason=grant.reason,
                evidence_refs=grant.evidence_refs,
                plan_version=plan_version,
            )
        )

    session.add_all(proposed_grants)

    # 提前执行 SQL，让外键、唯一约束等数据库错误在当前函数内暴露。
    # 此处不 commit，提交权仍由 API 路由统一控制。
    await session.flush()

    return proposed_grants

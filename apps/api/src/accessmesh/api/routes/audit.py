"""权限治理审计事件查询接口。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.api.dependencies import get_current_demo_user
from accessmesh.db.models import (
    AccessRequest,
    AuditEvent,
    DemoUser,
    ProposedGrant,
    Resource,
)
from accessmesh.db.session import get_db
from accessmesh.domain.schemas import AuditEventPageRead, AuditEventRead

router = APIRouter()


@router.get("", response_model=AuditEventPageRead)
async def list_audit_events(
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request_id: UUID | None = None,
    subject_external_id: str | None = None,
    resource_external_id: str | None = None,
    event_type: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> AuditEventPageRead:
    """分页查询审计事件，并按申请、主体、资源及事件类型筛选。"""

    base_query = select(AuditEvent).outerjoin(
        AccessRequest,
        AccessRequest.id == AuditEvent.request_id,
    )

    # 普通申请人只能看到自己发起申请所产生的审计事件；
    # 审批人和审计员可以查看全部事件。
    if current_user.role == "requester":
        base_query = base_query.where(
            AccessRequest.requester_external_id == current_user.external_id
        )

    if request_id is not None:
        base_query = base_query.where(AuditEvent.request_id == request_id)

    if subject_external_id:
        base_query = base_query.where(AccessRequest.subject_external_id == subject_external_id)

    if resource_external_id:
        # 审计事件通过申请关联候选授权，再定位到申请涉及的资源。
        matching_request_ids = (
            select(ProposedGrant.request_id)
            .join(Resource, Resource.id == ProposedGrant.resource_id)
            .where(Resource.external_id == resource_external_id)
        )
        base_query = base_query.where(AuditEvent.request_id.in_(matching_request_ids))

    if event_type:
        base_query = base_query.where(AuditEvent.event_type == event_type)

    # 先统计筛选后的总数，供前端正确计算总页数。
    total = await session.scalar(select(func.count()).select_from(base_query.subquery()))

    offset = (page - 1) * page_size
    query = base_query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(page_size)

    result = await session.scalars(query)
    return AuditEventPageRead(
        items=[AuditEventRead.model_validate(event) for event in result.all()],
        total=total or 0,
        page=page,
        page_size=page_size,
    )

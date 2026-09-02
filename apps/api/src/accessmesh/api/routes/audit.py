"""权限治理审计事件查询接口。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.api.dependencies import get_current_demo_user
from accessmesh.db.models import AccessRequest, AuditEvent, DemoUser
from accessmesh.db.session import get_db
from accessmesh.domain.schemas import AuditEventRead

router = APIRouter()


@router.get("", response_model=list[AuditEventRead])
async def list_audit_events(
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    request_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AuditEventRead]:
    """按时间倒序查询审计事件，支持按申请编号筛选。"""

    query = (
        select(AuditEvent)
        .outerjoin(AccessRequest, AccessRequest.id == AuditEvent.request_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )

    # 普通申请人只能看到自己发起申请所产生的审计事件；
    # 审批人和审计员可以查看全部事件。
    if current_user.role == "requester":
        query = query.where(AccessRequest.requester_external_id == current_user.external_id)

    if request_id is not None:
        query = query.where(AuditEvent.request_id == request_id)

    result = await session.scalars(query)
    return [AuditEventRead.model_validate(event) for event in result.all()]

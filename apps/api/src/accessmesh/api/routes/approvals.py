"""待审批申请查询与人工审批接口。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.api.dependencies import require_roles
from accessmesh.approval.service import (
    ApprovalConflictError,
    ApprovalNotFoundError,
    ApprovalValidationError,
    decide_approval,
)
from accessmesh.db.models import AccessRequest, DemoUser
from accessmesh.db.session import get_db
from accessmesh.domain.enums import RequestStatus
from accessmesh.domain.schemas import (
    AccessRequestRead,
    ApprovalCreate,
    ApprovalRead,
)

router = APIRouter()


@router.get("/pending", response_model=list[AccessRequestRead])
async def list_pending_approvals(
    _: Annotated[DemoUser, Depends(require_roles("approver"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AccessRequestRead]:
    """仅允许审批人查看当前等待人工审批的申请。"""

    result = await session.scalars(
        select(AccessRequest)
        .where(AccessRequest.status == RequestStatus.PENDING_APPROVAL)
        .order_by(AccessRequest.created_at.asc())
    )
    return [AccessRequestRead.model_validate(request) for request in result.all()]


@router.post("/{request_id}", response_model=ApprovalRead)
async def create_approval(
    request_id: UUID,
    payload: ApprovalCreate,
    current_approver: Annotated[
        DemoUser,
        Depends(require_roles("approver")),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApprovalRead:
    """由审批人通过或拒绝一条待审批申请。"""

    try:
        approval = await decide_approval(
            session=session,
            request_id=request_id,
            approver_external_id=current_approver.external_id,
            payload=payload,
        )
        await session.commit()
    except ApprovalNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ApprovalConflictError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ApprovalValidationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await session.refresh(approval)
    return ApprovalRead.model_validate(approval)

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.api.dependencies import get_current_demo_user
from accessmesh.db.models import AccessRequest, AuditEvent, DemoUser
from accessmesh.db.session import get_db
from accessmesh.domain.schemas import AccessRequestCreate, AccessRequestRead

router = APIRouter()


@router.post("", response_model=AccessRequestRead, status_code=status.HTTP_201_CREATED)
async def create_access_request(
    payload: AccessRequestCreate,
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AccessRequestRead:
    existing = await session.scalar(
        select(AccessRequest).where(
            AccessRequest.requester_external_id == current_user.external_id,
            AccessRequest.client_request_id == payload.client_request_id,
        )
    )
    if existing is not None:
        return AccessRequestRead.model_validate(existing)

    trace_id = uuid4().hex
    request = AccessRequest(
        requester_external_id=current_user.external_id,
        subject_external_id=payload.subject_external_id,
        raw_request=payload.request_text,
        client_request_id=payload.client_request_id,
        trace_id=trace_id,
    )
    session.add(request)
    await session.flush()
    session.add(
        AuditEvent(
            request_id=request.id,
            trace_id=trace_id,
            event_type="ACCESS_REQUEST_CREATED",
            actor_external_id=current_user.external_id,
            payload={"client_request_id": payload.client_request_id},
        )
    )
    await session.commit()
    await session.refresh(request)
    return AccessRequestRead.model_validate(request)


@router.get("", response_model=list[AccessRequestRead])
async def list_access_requests(
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AccessRequestRead]:
    query = select(AccessRequest).order_by(AccessRequest.created_at.desc())
    if current_user.role == "requester":
        query = query.where(AccessRequest.requester_external_id == current_user.external_id)
    requests = await session.scalars(query)
    return [AccessRequestRead.model_validate(item) for item in requests.all()]


@router.get("/{request_id}", response_model=AccessRequestRead)
async def get_access_request(
    request_id: UUID,
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AccessRequestRead:
    request = await session.get(AccessRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request not found")
    requester_cannot_view = (
        current_user.role == "requester"
        and request.requester_external_id != current_user.external_id
    )
    if requester_cannot_view:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="request not visible")
    return AccessRequestRead.model_validate(request)

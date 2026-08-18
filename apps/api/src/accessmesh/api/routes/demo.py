from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.db.session import get_db
from accessmesh.domain.schemas import DemoUserRead
from accessmesh.identity.provider import DemoIdentityProvider

router = APIRouter()


@router.get("/users", response_model=list[DemoUserRead])
async def list_demo_users(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[DemoUserRead]:
    users = await DemoIdentityProvider(session).list_users()
    return [DemoUserRead.model_validate(user) for user in users]

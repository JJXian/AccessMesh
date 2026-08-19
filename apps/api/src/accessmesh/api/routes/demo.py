"""仅供本地演示环境切换身份的接口。"""

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
    """返回可在前端身份切换器中选择的演示用户。"""

    users = await DemoIdentityProvider(session).list_users()
    return [DemoUserRead.model_validate(user) for user in users]

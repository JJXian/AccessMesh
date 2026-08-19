"""权限资源目录查询接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.api.dependencies import get_current_demo_user
from accessmesh.db.models import DemoUser, Resource
from accessmesh.db.session import get_db
from accessmesh.domain.schemas import ResourceRead

router = APIRouter()


@router.get("", response_model=list[ResourceRead])
async def list_resources(
    _: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ResourceRead]:
    """返回当前身份可浏览的全部启用资源。"""

    resources = await session.scalars(select(Resource).where(Resource.enabled.is_(True)))
    return [ResourceRead.model_validate(resource) for resource in resources.all()]

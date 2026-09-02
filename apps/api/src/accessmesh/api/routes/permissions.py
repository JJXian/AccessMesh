"""已生效权限实例查询接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.api.dependencies import get_current_demo_user
from accessmesh.db.models import DemoUser, PermissionInstance, Resource
from accessmesh.db.session import get_db
from accessmesh.domain.enums import PermissionStatus
from accessmesh.domain.schemas import PermissionInstanceRead

router = APIRouter()


@router.get("", response_model=list[PermissionInstanceRead])
async def list_active_permissions(
    current_user: Annotated[DemoUser, Depends(get_current_demo_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PermissionInstanceRead]:
    """查询当前有效权限；普通申请人只能查看自己的权限。"""

    query = (
        select(PermissionInstance, Resource)
        .join(Resource, Resource.id == PermissionInstance.resource_id)
        .where(PermissionInstance.status == PermissionStatus.ACTIVE)
        .order_by(PermissionInstance.expires_at.asc())
    )

    # 申请人只能查看自己真正获得的权限；
    # 审批人和审计员在演示环境中可查看全部有效权限。
    if current_user.role == "requester":
        query = query.where(PermissionInstance.subject_external_id == current_user.external_id)

    result = await session.execute(query)

    return [
        PermissionInstanceRead(
            id=permission.id,
            request_id=permission.request_id,
            subject_external_id=permission.subject_external_id,
            resource_external_id=resource.external_id,
            resource_name=resource.name,
            permission=permission.permission,
            status=permission.status,
            granted_at=permission.granted_at,
            expires_at=permission.expires_at,
            revoked_at=permission.revoked_at,
        )
        for permission, resource in result.all()
    ]

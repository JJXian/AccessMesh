"""已生效权限实例查询接口。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.api.dependencies import get_current_demo_user, require_roles
from accessmesh.db.models import DemoUser, PermissionInstance, Resource
from accessmesh.db.session import get_db
from accessmesh.domain.enums import PermissionStatus
from accessmesh.domain.schemas import PermissionInstanceRead, PermissionRevocationCreate
from accessmesh.execution.revocation import (
    RevocationConflictError,
    RevocationNotFoundError,
    RevocationOperationError,
    revoke_permission_manually,
)

router = APIRouter()


@router.post("/{permission_id}/revoke", response_model=PermissionInstanceRead)
async def revoke_permission(
    permission_id: UUID,
    payload: PermissionRevocationCreate,
    current_approver: Annotated[
        DemoUser,
        Depends(require_roles("approver")),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PermissionInstanceRead:
    """由审批人手工提前回收一条有效权限。"""

    try:
        result = await revoke_permission_manually(
            session,
            permission_id=permission_id,
            actor_external_id=current_approver.external_id,
            reason=payload.reason,
        )
        await session.commit()
    except RevocationNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RevocationConflictError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RevocationOperationError as exc:
        # 权限状态没有改变，但失败事件需要提交，保证外部调用失败也可审计。
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    permission = result.permission
    resource = result.resource
    return PermissionInstanceRead(
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

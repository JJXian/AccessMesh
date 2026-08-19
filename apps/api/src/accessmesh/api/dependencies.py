"""FastAPI 路由共享的身份认证、角色校验和配置依赖。"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.config import Settings, get_settings
from accessmesh.db.models import DemoUser
from accessmesh.db.session import get_db
from accessmesh.identity.provider import DemoIdentityProvider


async def get_current_demo_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: Annotated[str | None, Header(alias="X-Demo-Subject-Id")] = None,
) -> DemoUser:
    """从演示请求头解析当前用户；未提供请求头时使用默认身份。"""

    if not settings.demo_identity_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="demo identity provider is disabled",
        )
    external_id = subject_id or settings.default_demo_subject_id
    user = await DemoIdentityProvider(session).get_user(external_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unknown demo identity",
        )
    return user


def require_roles(*roles: str) -> Callable[..., DemoUser]:
    """生成角色守卫依赖，限制路由只能由指定角色访问。"""

    async def dependency(
        user: Annotated[DemoUser, Depends(get_current_demo_user)],
    ) -> DemoUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return dependency

"""身份信息提供方接口及演示数据库实现。"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.db.models import DemoUser


class IdentityProvider(Protocol):
    """隔离上层业务与具体身份系统的数据来源。"""

    async def get_user(self, external_id: str) -> DemoUser | None: ...

    async def list_users(self) -> list[DemoUser]: ...


class DemoIdentityProvider:
    """从本地演示用户表读取身份信息。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user(self, external_id: str) -> DemoUser | None:
        """根据外部身份标识查询单个用户。"""

        return await self._session.scalar(
            select(DemoUser).where(DemoUser.external_id == external_id)
        )

    async def list_users(self) -> list[DemoUser]:
        """按用户名排序返回全部演示用户。"""

        result = await self._session.scalars(select(DemoUser).order_by(DemoUser.username))
        return list(result.all())

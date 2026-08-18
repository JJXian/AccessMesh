from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accessmesh.db.models import DemoUser


class IdentityProvider(Protocol):
    async def get_user(self, external_id: str) -> DemoUser | None: ...

    async def list_users(self) -> list[DemoUser]: ...


class DemoIdentityProvider:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user(self, external_id: str) -> DemoUser | None:
        return await self._session.scalar(
            select(DemoUser).where(DemoUser.external_id == external_id)
        )

    async def list_users(self) -> list[DemoUser]:
        result = await self._session.scalars(select(DemoUser).order_by(DemoUser.username))
        return list(result.all())

import pytest

from accessmesh.adapters.base import GrantCommand
from accessmesh.adapters.memory import InMemoryResourceAdapter


@pytest.mark.asyncio
async def test_grant_is_idempotent_and_revocable() -> None:
    adapter = InMemoryResourceAdapter("database")
    command = GrantCommand("user-1", "database:test", "read_only", "idem-1")

    first = await adapter.grant(command)
    second = await adapter.grant(command)

    assert first == second
    assert await adapter.check(command) is True

    await adapter.revoke(command)
    assert await adapter.check(command) is False

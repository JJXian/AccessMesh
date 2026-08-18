from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GrantCommand:
    subject_external_id: str
    resource_external_id: str
    permission: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class OperationResult:
    success: bool
    operation_id: str
    message: str = ""


class ResourceAdapter(Protocol):
    async def grant(self, command: GrantCommand) -> OperationResult: ...

    async def revoke(self, command: GrantCommand) -> OperationResult: ...

    async def check(self, command: GrantCommand) -> bool: ...

    async def health(self) -> bool: ...

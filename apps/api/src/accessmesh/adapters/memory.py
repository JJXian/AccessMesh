from accessmesh.adapters.base import GrantCommand, OperationResult


class InMemoryResourceAdapter:
    """Deterministic adapter for local development and fault-injection tests."""

    def __init__(self, adapter_name: str) -> None:
        self.adapter_name = adapter_name
        self._grants: set[tuple[str, str, str]] = set()
        self._results: dict[str, OperationResult] = {}

    async def grant(self, command: GrantCommand) -> OperationResult:
        if command.idempotency_key in self._results:
            return self._results[command.idempotency_key]
        key = (command.subject_external_id, command.resource_external_id, command.permission)
        self._grants.add(key)
        result = OperationResult(True, command.idempotency_key, "grant applied")
        self._results[command.idempotency_key] = result
        return result

    async def revoke(self, command: GrantCommand) -> OperationResult:
        key = (command.subject_external_id, command.resource_external_id, command.permission)
        self._grants.discard(key)
        return OperationResult(True, command.idempotency_key, "grant revoked")

    async def check(self, command: GrantCommand) -> bool:
        key = (command.subject_external_id, command.resource_external_id, command.permission)
        return key in self._grants

    async def health(self) -> bool:
        return True

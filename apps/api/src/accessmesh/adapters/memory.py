"""用于本地开发和测试的内存资源适配器。"""

from accessmesh.adapters.base import GrantCommand, OperationResult


class InMemoryResourceAdapter:
    """结果确定的内存适配器，适用于本地开发和故障注入测试。"""

    def __init__(self, adapter_name: str) -> None:
        self.adapter_name = adapter_name
        self._grants: set[tuple[str, str, str]] = set()
        self._results: dict[str, OperationResult] = {}

    async def grant(self, command: GrantCommand) -> OperationResult:
        """授予权限；相同幂等键重复提交时直接返回首次执行结果。"""

        if command.idempotency_key in self._results:
            return self._results[command.idempotency_key]
        key = (command.subject_external_id, command.resource_external_id, command.permission)
        self._grants.add(key)
        result = OperationResult(True, command.idempotency_key, "grant applied")
        self._results[command.idempotency_key] = result
        return result

    async def revoke(self, command: GrantCommand) -> OperationResult:
        """撤销权限；目标不存在时也视为成功，以保证操作幂等。"""

        key = (command.subject_external_id, command.resource_external_id, command.permission)
        self._grants.discard(key)
        return OperationResult(True, command.idempotency_key, "grant revoked")

    async def check(self, command: GrantCommand) -> bool:
        """检查指定主体当前是否持有目标权限。"""

        key = (command.subject_external_id, command.resource_external_id, command.permission)
        return key in self._grants

    async def health(self) -> bool:
        """内存实现无外部依赖，始终处于健康状态。"""

        return True

"""资源适配器的公共命令、结果模型和接口协议。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GrantCommand:
    """对外部资源执行授权或撤权所需的最小参数。"""

    subject_external_id: str
    resource_external_id: str
    permission: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class OperationResult:
    """资源适配器操作的标准化结果。"""

    success: bool
    operation_id: str
    message: str = ""


class ResourceAdapter(Protocol):
    """GitLab、数据库和云资源适配器必须实现的异步接口。"""

    async def grant(self, command: GrantCommand) -> OperationResult: ...

    async def revoke(self, command: GrantCommand) -> OperationResult: ...

    async def check(self, command: GrantCommand) -> bool: ...

    async def health(self) -> bool: ...

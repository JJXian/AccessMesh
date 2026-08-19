"""按资源类型查找对应适配器的注册中心。"""

from accessmesh.adapters.base import ResourceAdapter
from accessmesh.adapters.memory import InMemoryResourceAdapter


class AdapterRegistry:
    """集中管理资源类型与适配器实例的映射。"""

    def __init__(self) -> None:
        self._adapters: dict[str, ResourceAdapter] = {
            "gitlab": InMemoryResourceAdapter("gitlab"),
            "database": InMemoryResourceAdapter("database"),
            "cloud": InMemoryResourceAdapter("cloud"),
        }

    def get(self, adapter_type: str) -> ResourceAdapter:
        """返回指定类型的适配器，不支持的类型会显式报错。"""

        try:
            return self._adapters[adapter_type]
        except KeyError as exc:
            raise ValueError(f"unsupported adapter: {adapter_type}") from exc


adapter_registry = AdapterRegistry()

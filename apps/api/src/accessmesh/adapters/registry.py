from accessmesh.adapters.base import ResourceAdapter
from accessmesh.adapters.memory import InMemoryResourceAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ResourceAdapter] = {
            "gitlab": InMemoryResourceAdapter("gitlab"),
            "database": InMemoryResourceAdapter("database"),
            "cloud": InMemoryResourceAdapter("cloud"),
        }

    def get(self, adapter_type: str) -> ResourceAdapter:
        try:
            return self._adapters[adapter_type]
        except KeyError as exc:
            raise ValueError(f"unsupported adapter: {adapter_type}") from exc


adapter_registry = AdapterRegistry()

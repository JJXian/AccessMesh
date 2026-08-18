from typing import Any

import httpx

from accessmesh.config import Settings
from accessmesh.domain.schemas import PolicyDecision


class PolicyUnavailableError(RuntimeError):
    pass


class OpaPolicyClient:
    """Fail-closed OPA client. An unavailable policy service never implies allow."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def evaluate(self, policy_input: dict[str, Any]) -> PolicyDecision:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=3.0)
        try:
            response = await client.post(
                f"{self._settings.opa_url}{self._settings.opa_decision_path}",
                json={"input": policy_input},
            )
            response.raise_for_status()
            result = response.json().get("result")
            if not isinstance(result, dict):
                raise PolicyUnavailableError("OPA returned no decision")
            return PolicyDecision.model_validate(result)
        except (httpx.HTTPError, ValueError) as exc:
            raise PolicyUnavailableError("OPA policy evaluation failed") from exc
        finally:
            if owns_client:
                await client.aclose()

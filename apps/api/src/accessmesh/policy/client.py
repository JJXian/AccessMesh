"""OPA 策略服务的异步客户端。"""

from typing import Any

import httpx

from accessmesh.config import Settings
from accessmesh.domain.schemas import PolicyDecision


class PolicyUnavailableError(RuntimeError):
    """策略服务不可用或未返回合法决策。"""


class OpaPolicyClient:
    """默认拒绝的 OPA 客户端；策略服务异常时绝不会隐式放行。"""

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    async def evaluate(self, policy_input: dict[str, Any]) -> PolicyDecision:
        """提交策略输入并将 OPA 返回值校验为统一决策模型。"""

        # 支持注入共享客户端；未注入时由本方法创建并负责关闭临时客户端。
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=3.0)
        try:
            response = await client.post(
                f"{self._settings.opa_url}{self._settings.opa_decision_path}",
                json={"input": policy_input},
            )
            response.raise_for_status()
            result = response.json().get("result")
            # OPA 即使返回 2xx，也可能因策略路径错误而缺少 result，必须按失败处理。
            if not isinstance(result, dict):
                raise PolicyUnavailableError("OPA returned no decision")
            return PolicyDecision.model_validate(result)
        except (httpx.HTTPError, ValueError) as exc:
            raise PolicyUnavailableError("OPA policy evaluation failed") from exc
        finally:
            if owns_client:
                await client.aclose()

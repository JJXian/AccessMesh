"""统一的结构化大语言模型调用入口。"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from accessmesh.config import Settings

ResponseT = TypeVar("ResponseT", bound=BaseModel)
RetrySleeper = Callable[[float], Awaitable[None]]


class LlmConfigurationError(ValueError):
    """模型配置不完整时抛出的异常。"""


class LlmProviderError(RuntimeError):
    """模型服务不可用或返回非法协议数据时抛出的异常。"""


class LlmStructuredOutputError(LlmProviderError):
    """模型输出无法通过目标 Pydantic Schema 校验时抛出的异常。"""


@dataclass(frozen=True, slots=True)
class LlmCallMetadata:
    """一次模型调用的非敏感运行指标。"""

    provider: str
    model: str
    latency_ms: int
    attempt_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class LlmCallResult[ResponseT]:
    """通过 Schema 校验的业务结果及其调用指标。"""

    output: ResponseT
    metadata: LlmCallMetadata


class LlmProvider(Protocol):
    """所有 Agent 依赖的最小模型能力接口。"""

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseT],
    ) -> LlmCallResult[ResponseT]:
        """根据提示词生成并校验结构化输出。"""

        ...


class OpenAICompatibleProvider:
    """通过 OpenAI 兼容 Chat Completions 接口生成结构化输出。"""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        sleeper: RetrySleeper = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._client = client
        self._sleeper = sleeper

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseT],
    ) -> LlmCallResult[ResponseT]:
        """调用模型，并在临时故障或 Schema 错误时执行有限重试。"""

        self._validate_configuration()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=self._settings.llm_timeout_seconds,
            trust_env=self._settings.llm_trust_env,
        )
        started_at = perf_counter()
        max_attempts = self._settings.llm_max_retries + 1
        last_error: Exception | None = None

        try:
            for attempt in range(1, max_attempts + 1):
                try:
                    response = await client.post(
                        f"{self._settings.llm_base_url.rstrip('/')}/chat/completions",
                        headers={
                            "Authorization": (
                                f"Bearer {self._settings.llm_api_key.get_secret_value()}"
                            ),
                            "Content-Type": "application/json",
                        },
                        json=self._build_request_body(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            response_model=response_model,
                        ),
                    )
                    response.raise_for_status()
                    payload = response.json()
                    output = self._parse_output(payload, response_model)
                    usage = payload.get("usage", {})
                    return LlmCallResult(
                        output=output,
                        metadata=LlmCallMetadata(
                            provider=self._settings.llm_provider,
                            model=self._settings.llm_model,
                            latency_ms=round((perf_counter() - started_at) * 1000),
                            attempt_count=attempt,
                            prompt_tokens=self._read_token_count(usage, "prompt_tokens"),
                            completion_tokens=self._read_token_count(
                                usage,
                                "completion_tokens",
                            ),
                            total_tokens=self._read_token_count(usage, "total_tokens"),
                        ),
                    )
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                    last_error = exc
                    if attempt >= max_attempts or not self._is_retryable(exc):
                        break
                    # 退避时间有上限，避免模型异常时长时间占用请求线程。
                    await self._sleeper(min(0.25 * (2 ** (attempt - 1)), 2.0))
        finally:
            if owns_client:
                await client.aclose()

        if isinstance(last_error, ValidationError):
            raise LlmStructuredOutputError("模型输出未通过结构化 Schema 校验。") from last_error
        raise LlmProviderError("模型服务调用失败。") from last_error

    def _validate_configuration(self) -> None:
        """在发出网络请求前检查必要配置。"""

        missing_fields = []
        if not self._settings.llm_base_url.strip():
            missing_fields.append("LLM_BASE_URL")
        if not self._settings.llm_api_key.get_secret_value().strip():
            missing_fields.append("LLM_API_KEY")
        if not self._settings.llm_model.strip():
            missing_fields.append("LLM_MODEL")
        if missing_fields:
            raise LlmConfigurationError(f"缺少模型配置：{', '.join(missing_fields)}")

    def _build_request_body(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ResponseT],
    ) -> dict[str, Any]:
        """构建要求模型严格返回 JSON Schema 的请求体。"""

        return {
            "model": self._settings.llm_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": response_model.model_json_schema(),
                },
            },
        }

    @staticmethod
    def _parse_output(payload: dict[str, Any], response_model: type[ResponseT]) -> ResponseT:
        """提取首个模型响应，并交给 Pydantic 完成业务校验。"""

        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("模型没有返回文本形式的结构化结果。")
        return response_model.model_validate_json(content)

    @staticmethod
    def _read_token_count(usage: Any, field: str) -> int:
        """安全读取 Token 计数，兼容未返回 usage 的模型服务。"""

        if not isinstance(usage, dict):
            return 0
        value = usage.get(field, 0)
        return value if isinstance(value, int) and value >= 0 else 0

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """只重试临时故障和模型格式错误，不重试普通客户端错误。"""

        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code == 429 or exc.response.status_code >= 500
        return isinstance(
            exc,
            (
                httpx.TransportError,
                ValidationError,
                ValueError,
                KeyError,
                TypeError,
            ),
        )

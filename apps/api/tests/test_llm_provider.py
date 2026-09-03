"""统一大语言模型 Provider 测试。"""

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from accessmesh.config import Settings
from accessmesh.domain.schemas import ParsedIntent
from accessmesh.llm.provider import (
    LlmConfigurationError,
    LlmStructuredOutputError,
    OpenAICompatibleProvider,
)


def build_settings(**overrides: object) -> Settings:
    """创建不会访问真实模型服务的测试配置。"""

    return Settings(
        llm_base_url="https://llm.example.test/v1",
        llm_api_key="test-secret",
        llm_model="test-model",
        **overrides,
    )


@pytest.mark.asyncio
async def test_provider_returns_validated_output_and_metadata() -> None:
    """合法模型响应应转换为领域模型，并记录 Token 和尝试次数。"""

    def handler(request: httpx.Request) -> httpx.Response:
        request_body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert request_body["response_format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "task": "排查支付接口异常",
                                    "resource_hints": ["支付测试数据库"],
                                    "action_hints": ["read_only"],
                                    "duration_days": 3,
                                    "missing_fields": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 12,
                    "total_tokens": 32,
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAICompatibleProvider(build_settings(), client).generate_structured(
            system_prompt="你是权限申请解析器。",
            user_prompt="申请支付测试数据库只读权限三天。",
            response_model=ParsedIntent,
        )

    assert result.output.duration_days == 3
    assert result.output.action_hints == ["read_only"]
    assert result.metadata.attempt_count == 1
    assert result.metadata.total_tokens == 32


@pytest.mark.asyncio
async def test_provider_retries_schema_error_then_succeeds() -> None:
    """第一次输出不符合 Schema 时，应在有限次数内要求模型重新生成。"""

    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        duration = 0 if call_count == 1 else 7
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "task": "查询测试数据库",
                                    "resource_hints": ["测试数据库"],
                                    "action_hints": ["read_only"],
                                    "duration_days": duration,
                                    "missing_fields": [],
                                }
                            )
                        }
                    }
                ]
            },
        )

    sleeper = AsyncMock()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAICompatibleProvider(
            build_settings(llm_max_retries=1),
            client,
            sleeper=sleeper,
        ).generate_structured(
            system_prompt="解析申请。",
            user_prompt="查询测试数据库七天。",
            response_model=ParsedIntent,
        )

    assert result.output.duration_days == 7
    assert result.metadata.attempt_count == 2
    sleeper.assert_awaited_once_with(0.25)


@pytest.mark.asyncio
async def test_provider_rejects_invalid_output_after_retry_limit() -> None:
    """持续不合法的模型输出不能进入 Agent 工作流。"""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"duration_days": 0}'}}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LlmStructuredOutputError):
            await OpenAICompatibleProvider(
                build_settings(llm_max_retries=0),
                client,
            ).generate_structured(
                system_prompt="解析申请。",
                user_prompt="测试输入。",
                response_model=ParsedIntent,
            )


@pytest.mark.asyncio
async def test_provider_checks_configuration_before_network_call() -> None:
    """缺少密钥、地址和模型名称时，不应尝试发送网络请求。"""

    client = AsyncMock(spec=httpx.AsyncClient)
    provider = OpenAICompatibleProvider(
        Settings(llm_base_url="", llm_api_key="", llm_model=""),
        client,
    )

    with pytest.raises(LlmConfigurationError, match="LLM_BASE_URL.*LLM_API_KEY.*LLM_MODEL"):
        await provider.generate_structured(
            system_prompt="解析申请。",
            user_prompt="测试输入。",
            response_model=ParsedIntent,
        )

    client.post.assert_not_awaited()

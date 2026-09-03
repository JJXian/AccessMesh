"""使用大语言模型提取权限申请结构化意图。"""

from accessmesh.domain.enums import IntentField
from accessmesh.domain.schemas import ParsedIntent
from accessmesh.llm.provider import LlmCallResult, LlmProvider
from accessmesh.prompts.request_parser import REQUEST_PARSER_SYSTEM_PROMPT


class LlmRequestParser:
    """只负责理解申请文本、无权执行授权操作的解析 Agent。"""

    def __init__(self, provider: LlmProvider) -> None:
        self._provider = provider

    async def parse(self, raw_request: str) -> LlmCallResult[ParsedIntent]:
        """调用模型解析申请，再用确定性逻辑校正缺失字段。"""

        result = await self._provider.generate_structured(
            system_prompt=REQUEST_PARSER_SYSTEM_PROMPT,
            user_prompt=raw_request,
            response_model=ParsedIntent,
        )
        normalized_intent = self._normalize_intent(result.output)
        return LlmCallResult(output=normalized_intent, metadata=result.metadata)

    @staticmethod
    def _normalize_intent(intent: ParsedIntent) -> ParsedIntent:
        """清理重复提示，并重新计算缺失字段，避免信任模型自报结果。"""

        task = intent.task.strip() if intent.task else None
        resource_hints = list(
            dict.fromkeys(hint.strip() for hint in intent.resource_hints if hint.strip())
        )
        action_hints = list(
            dict.fromkeys(hint.strip() for hint in intent.action_hints if hint.strip())
        )

        missing_fields: list[IntentField] = []
        if not task:
            missing_fields.append(IntentField.TASK)
        if not resource_hints:
            missing_fields.append(IntentField.RESOURCE)
        if not action_hints:
            missing_fields.append(IntentField.ACTION)
        if intent.duration_days is None:
            missing_fields.append(IntentField.DURATION)

        return ParsedIntent(
            task=task,
            resource_hints=resource_hints,
            action_hints=action_hints,
            duration_days=intent.duration_days,
            missing_fields=missing_fields,
        )

"""基于规则的自然语言权限申请解析器。

第一版用于演示环境：从申请文本中识别资源类型、操作类型和授权时长。
后续可替换为 LLM 结构化输出，但仍保持 ParsedIntent 作为统一输出格式。
"""

import re

from accessmesh.domain.enums import IntentField
from accessmesh.domain.schemas import ParsedIntent


# 代码仓库资源提示规则。
GITLAB_KEYWORDS = ("gitlab", "代码仓库", "仓库")

# 数据库环境提示规则。必须先识别具体环境，再考虑泛化的“数据库”。
TEST_DATABASE_KEYWORDS = ("测试数据库", "测试库", "test database")
PRODUCTION_DATABASE_KEYWORDS = (
    "生产数据库",
    "生产库",
    "prod database",
    "production database",
)
GENERIC_DATABASE_KEYWORDS = ("数据库", "database", "db")

# 写操作的风险通常更高，因此必须优先判断。
WRITE_KEYWORDS = ("写入", "修改", "更新", "删除", "创建", "提交", "开发")

# 只读操作关键词。
READ_KEYWORDS = ("只读", "查询", "查看", "读取", "分析", "排查")

# 例如识别“30天”“30 天”“有效期 30 天”中的 30。
DURATION_PATTERN = re.compile(r"(?P<days>\d{1,3})\s*天")


class BasicIntentParser:
    """将自然语言权限申请转换为 ParsedIntent。"""

    def parse(self, raw_request: str) -> ParsedIntent:
        """解析一段原始申请文本，并标记尚未识别的信息。"""

        request_text = raw_request.strip()
        resource_hints = self._extract_resource_hints(request_text)
        action_hints = self._extract_action_hints(request_text)
        duration_days = self._extract_duration_days(request_text)
        missing_fields = self._find_missing_fields(
            task=request_text,
            resource_hints=resource_hints,
            action_hints=action_hints,
            duration_days=duration_days,
        )

        return ParsedIntent(
            # 第一版不额外总结任务，直接保留用户的完整原话，确保信息不丢失。
            task=request_text or None,
            resource_hints=resource_hints,
            action_hints=action_hints,
            duration_days=duration_days,
            missing_fields=missing_fields,
        )

    def _extract_resource_hints(self, request_text: str) -> list[str]:
        """从文本中提取资源提示，并优先保留具体环境。"""

        normalized_text = request_text.lower()
        resource_hints: list[str] = []

        # GitLab 与数据库可能同时出现在一次申请中，因此独立判断。
        if any(keyword in normalized_text for keyword in GITLAB_KEYWORDS):
            resource_hints.append("GitLab")

        # 数据库必须优先匹配具体环境。
        # 使用 if / elif，避免“测试数据库”同时又被识别成泛化的“数据库”。
        if any(keyword in normalized_text for keyword in TEST_DATABASE_KEYWORDS):
            resource_hints.append("测试数据库")
        elif any(
                keyword in normalized_text
                for keyword in PRODUCTION_DATABASE_KEYWORDS
        ):
            resource_hints.append("生产数据库")
        elif any(keyword in normalized_text for keyword in GENERIC_DATABASE_KEYWORDS):
            resource_hints.append("数据库")

        return resource_hints

    def _extract_action_hints(self, request_text: str) -> list[str]:
        """从文本中提取操作提示；写操作优先于读操作。"""

        if any(keyword in request_text for keyword in WRITE_KEYWORDS):
            return ["更新"]

        if any(keyword in request_text for keyword in READ_KEYWORDS):
            return ["查询"]

        return []

    def _extract_duration_days(self, request_text: str) -> int | None:
        """从文本中提取以“天”为单位的授权时长。"""

        match = DURATION_PATTERN.search(request_text)
        if match is None:
            return None

        return int(match.group("days"))

    def _find_missing_fields(
        self,
        task: str,
        resource_hints: list[str],
        action_hints: list[str],
        duration_days: int | None,
    ) -> list[IntentField]:
        """找出未识别字段，供后续澄清、策略和审批环节使用。"""

        missing_fields: list[IntentField] = []

        if not task:
            missing_fields.append(IntentField.TASK)
        if not resource_hints:
            missing_fields.append(IntentField.RESOURCE)
        if not action_hints:
            missing_fields.append(IntentField.ACTION)
        if duration_days is None:
            missing_fields.append(IntentField.DURATION)

        return missing_fields
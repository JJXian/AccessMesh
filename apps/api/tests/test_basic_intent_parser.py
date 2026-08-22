"""规则版意图解析器测试。"""

from accessmesh.domain.enums import IntentField
from accessmesh.parsing.basic_intent_parser import BasicIntentParser


def test_parser_extracts_frontend_demo_request() -> None:
    """应正确解析前端默认演示申请中的资源、动作和时长。"""

    result = BasicIntentParser().parse(
        "我需要支付项目GitLab只读权限和测试数据库查询权限，有效期30天，用于排查对账问题。"
    )

    assert result.task == "我需要支付项目GitLab只读权限和测试数据库查询权限，有效期30天，用于排查对账问题。"
    assert result.resource_hints == ["GitLab", "测试数据库"]
    assert result.action_hints == ["查询"]
    assert result.duration_days == 30
    assert result.missing_fields == []


def test_parser_marks_missing_action_and_duration() -> None:
    """未写操作和时长时，应明确标记缺失字段。"""

    result = BasicIntentParser().parse("我需要访问支付测试数据库。")

    assert result.resource_hints == ["测试数据库"]
    assert result.action_hints == []
    assert result.duration_days is None
    assert result.missing_fields == [
        IntentField.ACTION,
        IntentField.DURATION,
    ]


def test_parser_prioritizes_write_action() -> None:
    """同时存在查询和更新描述时，应以风险更高的写操作为准。"""

    result = BasicIntentParser().parse("需要查询并更新测试数据库，有效期2天。")

    assert result.resource_hints == ["测试数据库"]
    assert result.action_hints == ["更新"]
    assert result.duration_days == 2
    assert result.missing_fields == []

def test_parser_distinguishes_production_database() -> None:
    """生产数据库申请不能被错误识别为测试数据库。"""

    result = BasicIntentParser().parse("需要查询支付生产数据库，有效期1天。")

    assert result.resource_hints == ["生产数据库"]
    assert result.action_hints == ["查询"]
    assert result.duration_days == 1
    assert result.missing_fields == []
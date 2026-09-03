import pytest
from pydantic import ValidationError

from accessmesh.domain.enums import IntentField
from accessmesh.domain.schemas import CandidateGrant, ParsedIntent, PlanResult


def test_parsed_intent_accepts_complete_request() -> None:
    intent = ParsedIntent(
        task="排查测试环境的支付对账问题",
        resource_hints=["支付项目代码仓库", "支付测试数据库"],
        action_hints=["只读", "查询"],
        duration_days=30,
    )

    assert intent.task == "排查测试环境的支付对账问题"
    assert intent.duration_days == 30
    assert intent.missing_fields == []


def test_parsed_intent_records_missing_fields() -> None:
    intent = ParsedIntent(
        resource_hints=["支付项目"],
        missing_fields=[
            IntentField.TASK,
            IntentField.ACTION,
            IntentField.DURATION,
        ],
    )

    assert intent.task is None
    assert intent.duration_days is None
    assert intent.missing_fields == [
        IntentField.TASK,
        IntentField.ACTION,
        IntentField.DURATION,
    ]


def test_candidate_grant_rejects_invalid_duration() -> None:
    with pytest.raises(ValidationError):
        CandidateGrant(
            resource_external_id="database:payment-test",
            permission="read_only",
            duration_days=0,
            reason="用于排查测试环境对账问题",
        )


def test_plan_result_accepts_valid_candidate_grants() -> None:
    grant = CandidateGrant(
        resource_external_id="database:payment-test",
        permission="read_only",
        duration_days=30,
        reason="用于排查测试环境对账问题",
        evidence_refs=["resource:database:payment-test", "request:task"],
    )

    result = PlanResult(
        grants=[grant],
        assumptions=["申请人当前在支付研发部任职"],
    )

    assert len(result.grants) == 1
    assert result.grants[0].permission == "read_only"
    assert result.assumptions == ["申请人当前在支付研发部任职"]

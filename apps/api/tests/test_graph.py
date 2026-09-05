"""LangGraph 权限申请工作流测试。"""

import asyncio

import pytest

from accessmesh.domain.schemas import ParsedIntent
from accessmesh.graph.workflow import build_access_request_graph
from accessmesh.llm.provider import LlmCallMetadata, LlmCallResult


@pytest.mark.asyncio
async def test_graph_creates_least_privilege_plan() -> None:
    """工作流应将意图和资源上下文交给规划器，并得到只读候选方案。"""

    graph = build_access_request_graph()

    result = await graph.ainvoke(
        {
            "raw_request": "申请支付测试数据库权限",
            "parsed_intent": {
                "task": "排查支付接口异常",
                "resource_hints": ["支付测试数据库"],
                "action_hints": ["查询"],
                "duration_days": 3,
                "missing_fields": [],
            },
            "resource_context": {
                "resources": [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "external_id": "database:payment-test",
                        "name": "支付测试数据库",
                        "resource_type": "database",
                        "environment": "test",
                        "sensitivity": "L2",
                        "owner_external_id": "user-approver",
                        "allowed_permissions": [
                            "connect",
                            "read_only",
                            "read_write",
                        ],
                        "enabled": True,
                    }
                ]
            },
        }
    )

    assert result["status"] == "PLAN_READY"
    assert result["plan_assumptions"] == []
    assert result["proposed_grants"] == [
        {
            "resource_external_id": "database:payment-test",
            "permission": "read_only",
            "duration_days": 3,
            "reason": "为完成“排查支付接口异常”，建议在资源“支付测试数据库”上授予“read_only”权限。",
            "evidence_refs": [
                "resource:database:payment-test",
                "planner:basic-rule-v1",
            ],
        }
    ]


@pytest.mark.asyncio
async def test_graph_returns_empty_plan_when_context_has_no_resource() -> None:
    """未找到资源时，工作流应保留说明，但不能生成猜测性的权限。"""

    graph = build_access_request_graph()

    result = await graph.ainvoke(
        {
            "raw_request": "申请未知数据库权限",
            "parsed_intent": {
                "task": "排查问题",
                "resource_hints": ["未知数据库"],
                "action_hints": ["查询"],
                "duration_days": 1,
                "missing_fields": [],
            },
            "resource_context": {"resources": []},
        }
    )

    assert result["status"] == "PLAN_READY"
    assert result["proposed_grants"] == []
    assert result["plan_assumptions"] == ["资源目录中未找到与申请匹配的目标资源。"]


@pytest.mark.asyncio
async def test_graph_runs_configured_policy_evaluator() -> None:
    """配置策略评估器后，工作流应在规划完成后继续执行策略节点。"""

    evaluated_states: list[dict] = []

    async def fake_policy_evaluator(state: dict) -> dict:
        """模拟策略评估器，记录它接收到的规划结果。"""

        evaluated_states.append(state)
        return {
            "policy_decisions": [
                {
                    "resource_external_id": "database:payment-test",
                    "permission": "read_only",
                    "allow": True,
                }
            ],
            "status": "POLICY_EVALUATED",
        }

    graph = build_access_request_graph(
        policy_evaluator=fake_policy_evaluator,
    )
    result = await graph.ainvoke(
        {
            "raw_request": "申请支付测试数据库查询权限，有效期3天。",
            "identity_context": {
                "subject": {
                    "subject_type": "employee",
                    "employment_status": "active",
                }
            },
            "resource_context": {
                "resources": [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "external_id": "database:payment-test",
                        "name": "支付测试数据库",
                        "resource_type": "database",
                        "environment": "test",
                        "sensitivity": "L2",
                        "owner_external_id": "user-approver",
                        "allowed_permissions": [
                            "connect",
                            "read_only",
                            "read_write",
                        ],
                        "enabled": True,
                    }
                ]
            },
        }
    )

    assert result["status"] == "POLICY_EVALUATED"
    assert result["policy_decisions"][0]["allow"] is True
    assert len(evaluated_states) == 1
    assert evaluated_states[0]["proposed_grants"][0]["permission"] == "read_only"


@pytest.mark.asyncio
async def test_graph_uses_configured_llm_request_parser() -> None:
    """启用 LLM 解析器后，工作流应使用其结果并保留非敏感调用指标。"""

    async def fake_request_parser(_: str) -> LlmCallResult[ParsedIntent]:
        return LlmCallResult(
            output=ParsedIntent(
                task="排查支付接口异常",
                resource_hints=["支付测试数据库"],
                action_hints=["查询"],
                duration_days=3,
            ),
            metadata=LlmCallMetadata(
                provider="deepseek",
                model="deepseek-v4-flash",
                latency_ms=120,
                attempt_count=1,
                prompt_tokens=30,
                completion_tokens=20,
                total_tokens=50,
            ),
        )

    graph = build_access_request_graph(request_parser=fake_request_parser)
    result = await graph.ainvoke(
        {
            "raw_request": "申请支付测试数据库查询权限三天。",
            "resource_context": {"resources": []},
        }
    )

    assert result["parsed_intent"]["duration_days"] == 3
    assert result["parser_metadata"]["mode"] == "llm"
    assert result["parser_metadata"]["model"] == "deepseek-v4-flash"
    assert result["parser_metadata"]["total_tokens"] == 50


@pytest.mark.asyncio
async def test_graph_collects_identity_and_resource_context_in_parallel() -> None:
    """身份和资源 Agent 应并行启动，并在规划前汇合各自结果。"""

    identity_started = asyncio.Event()
    resource_started = asyncio.Event()

    async def load_identity(_: dict) -> dict:
        """等待资源分支启动，若工作流串行执行则测试会超时失败。"""

        identity_started.set()
        await asyncio.wait_for(resource_started.wait(), timeout=0.2)
        return {
            "identity_context": {
                "subject": {
                    "subject_type": "employee",
                    "employment_status": "active",
                }
            }
        }

    async def load_resources(_: dict) -> dict:
        """等待身份分支启动，验证两个分支确实发生重叠。"""

        resource_started.set()
        await asyncio.wait_for(identity_started.wait(), timeout=0.2)
        return {
            "resource_context": {
                "resources": [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "external_id": "database:payment-test",
                        "name": "支付测试数据库",
                        "resource_type": "database",
                        "environment": "test",
                        "sensitivity": "L2",
                        "owner_external_id": "user-approver",
                        "allowed_permissions": ["connect", "read_only", "read_write"],
                        "enabled": True,
                    }
                ]
            }
        }

    graph = build_access_request_graph(
        identity_context_loader=load_identity,
        resource_context_loader=load_resources,
    )
    result = await graph.ainvoke(
        {
            "raw_request": "申请支付测试数据库查询权限三天。",
            "parsed_intent": {
                "task": "排查支付异常",
                "resource_hints": ["支付测试数据库"],
                "action_hints": ["查询"],
                "duration_days": 3,
                "missing_fields": [],
            },
            "subject_external_id": "user-requester",
        }
    )

    assert identity_started.is_set()
    assert resource_started.is_set()
    assert result["identity_context"]["subject"]["subject_type"] == "employee"
    assert result["resource_context"]["resources"][0]["name"] == "支付测试数据库"
    assert result["proposed_grants"][0]["permission"] == "read_only"


def test_graph_requires_both_parallel_context_loaders() -> None:
    """只配置一个并行分支时应拒绝构图，避免规划使用不完整上下文。"""

    async def load_identity(_: dict) -> dict:
        return {"identity_context": {}}

    with pytest.raises(ValueError, match="必须同时配置"):
        build_access_request_graph(identity_context_loader=load_identity)

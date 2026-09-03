"""权限申请的 LangGraph 工作流。"""

from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any

from langgraph.graph import END, START, StateGraph

from accessmesh.domain.schemas import ParsedIntent, ResourceRead
from accessmesh.graph.state import AccessRequestState
from accessmesh.llm.provider import LlmCallResult
from accessmesh.parsing.basic_intent_parser import BasicIntentParser
from accessmesh.planning.basic_planner import BasicPlanner
from accessmesh.prompts.request_parser import REQUEST_PARSER_PROMPT_VERSION

# 上下文加载器和策略评估器都接收工作流状态，并异步返回要写回状态的内容。
ContextLoader = Callable[
    [AccessRequestState],
    Awaitable[dict[str, Any]],
]
PolicyEvaluator = Callable[
    [AccessRequestState],
    Awaitable[dict[str, Any]],
]
RequestParserAgent = Callable[[str], Awaitable[LlmCallResult[ParsedIntent]]]


async def parse_request(
    state: AccessRequestState,
    request_parser: RequestParserAgent | None = None,
) -> dict[str, Any]:
    """使用已配置的 LLM Agent 或规则解析器提取申请意图。"""

    existing_intent = state.get("parsed_intent")
    if existing_intent is not None:
        return {
            "parsed_intent": existing_intent,
            "parser_metadata": {"mode": "provided"},
            "status": "COLLECTING_CONTEXT",
        }

    if request_parser is not None:
        result = await request_parser(state["raw_request"])
        intent = result.output
        parser_metadata = {
            "mode": "llm",
            "prompt_version": REQUEST_PARSER_PROMPT_VERSION,
            **asdict(result.metadata),
        }
    else:
        # 未启用 LLM 时保留规则模式，让本地开发不依赖外部模型服务。
        intent = BasicIntentParser().parse(state["raw_request"])
        parser_metadata = {
            "mode": "rule",
            "parser_version": "basic-rule-v1",
        }

    return {
        "parsed_intent": intent.model_dump(mode="json"),
        "parser_metadata": parser_metadata,
        "status": "COLLECTING_CONTEXT",
    }


async def collect_context(state: AccessRequestState) -> dict[str, Any]:
    """默认上下文收集逻辑，主要供不连接数据库的单元测试使用。"""

    return {
        "identity_context": state.get("identity_context", {}),
        "resource_context": state.get("resource_context", {}),
        "status": "PLANNING",
    }


def create_plan(state: AccessRequestState) -> dict[str, Any]:
    """调用规划器，根据意图和资源上下文生成候选授权方案。"""

    intent = ParsedIntent.model_validate(state["parsed_intent"])

    raw_resources = state.get("resource_context", {}).get("resources", [])
    resources = [ResourceRead.model_validate(resource) for resource in raw_resources]

    result = BasicPlanner().create_plan(
        intent=intent,
        resources=resources,
    )

    return {
        "proposed_grants": [grant.model_dump(mode="json") for grant in result.grants],
        "plan_assumptions": result.assumptions,
        "status": "PLAN_READY",
    }


def build_access_request_graph(
    context_loader: ContextLoader | None = None,
    policy_evaluator: PolicyEvaluator | None = None,
    request_parser: RequestParserAgent | None = None,
) -> Any:
    """构建解析、上下文、规划和可选策略评估组成的工作流。"""

    async def collect_context_node(
        state: AccessRequestState,
    ) -> dict[str, Any]:
        """优先使用调用方提供的真实上下文加载器。"""

        if context_loader is not None:
            return await context_loader(state)

        return await collect_context(state)

    async def evaluate_policy_node(
        state: AccessRequestState,
    ) -> dict[str, Any]:
        """调用方配置策略评估器后，执行 OPA 决策。"""

        # 这个节点只会在 policy_evaluator 存在时加入工作流。
        assert policy_evaluator is not None
        return await policy_evaluator(state)

    async def parse_request_node(state: AccessRequestState) -> dict[str, Any]:
        """把图构建时选择的解析器绑定到当前工作流节点。"""

        return await parse_request(state, request_parser)

    builder = StateGraph(AccessRequestState)
    builder.add_node("parse_request", parse_request_node)
    builder.add_node("collect_context", collect_context_node)
    builder.add_node("create_plan", create_plan)

    builder.add_edge(START, "parse_request")
    builder.add_edge("parse_request", "collect_context")
    builder.add_edge("collect_context", "create_plan")

    # 保留“无策略评估器”的模式，让之前纯规划测试继续成立。
    if policy_evaluator is None:
        builder.add_edge("create_plan", END)
    else:
        builder.add_node("evaluate_policy", evaluate_policy_node)
        builder.add_edge("create_plan", "evaluate_policy")
        builder.add_edge("evaluate_policy", END)

    return builder.compile()

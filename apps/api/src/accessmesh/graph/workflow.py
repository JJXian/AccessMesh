"""权限申请的 LangGraph 工作流骨架。"""

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from accessmesh.domain.schemas import ParsedIntent, ResourceRead
from accessmesh.graph.state import AccessRequestState
from accessmesh.planning.basic_planner import BasicPlanner
from accessmesh.parsing.basic_intent_parser import BasicIntentParser

# 上下文加载器接收当前工作流状态，并异步返回要写回状态的内容。
ContextLoader = Callable[
    [AccessRequestState],
    Awaitable[dict[str, Any]],
]

def parse_request(state: AccessRequestState) -> dict[str, Any]:
    """将原始申请转换为初步意图。

    当前阶段还没有接入 LLM，因此默认将原始文本作为任务描述。
    如果调用方已经提供了结构化意图，则保留它，便于测试和后续接入解析器。
    """

    existing_intent = state.get("parsed_intent")
    if existing_intent is not None:
        return {
            "parsed_intent": existing_intent,
            "status": "COLLECTING_CONTEXT",
        }

    # 当前使用规则解析器；后续可在此替换为 LLM 结构化解析器。
    intent = BasicIntentParser().parse(state["raw_request"])
    return {
        # mode="json" 会把模型转换为可以放进状态、日志和 JSON 响应的普通字典。
        "parsed_intent": intent.model_dump(mode="json"),
        "status": "COLLECTING_CONTEXT",
    }

async def collect_context(state: AccessRequestState) -> dict[str, Any]:
    """默认上下文收集逻辑。

    单元测试或调用方未提供数据库加载器时，保留已注入的上下文。
    """

    return {
        "identity_context": state.get("identity_context", {}),
        "resource_context": state.get("resource_context", {}),
        "status": "PLANNING",
    }

def create_plan(state: AccessRequestState) -> dict[str, Any]:
    """调用规划器，根据意图和资源上下文生成候选授权方案。"""

    # model_validate 的作用是：即使 state 内是普通字典，
    # 也先转换并校验为领域模型，避免后续逻辑依赖未经校验的数据。
    intent = ParsedIntent.model_validate(state["parsed_intent"])

    # 资源上下文约定使用 resources 键保存资源列表。
    # 默认空列表表示当前还没有查询到可用资源。
    raw_resources = state.get("resource_context", {}).get("resources", [])
    resources = [ResourceRead.model_validate(item) for item in raw_resources]

    result = BasicPlanner().create_plan(intent=intent, resources=resources)

    return {
        # CandidateGrant 转成普通字典后才能安全放入 LangGraph 状态。
        "proposed_grants": [
            grant.model_dump(mode="json")
            for grant in result.grants
        ],
        "plan_assumptions": result.assumptions,
        "status": "PLAN_READY",
    }

def build_access_request_graph(
            context_loader: ContextLoader | None = None,
    ) -> Any:
    """按“解析申请→收集上下文→生成方案”的顺序构建可执行图。"""
    async def collect_context_node(state: AccessRequestState) -> dict[str, Any]:
        """优先使用调用方提供的上下文加载器。"""

        if context_loader is not None:
            return await context_loader(state)

        return await collect_context(state)
    builder = StateGraph(AccessRequestState)
    builder.add_node("parse_request", parse_request)
    builder.add_node("collect_context", collect_context_node)
    builder.add_node("create_plan", create_plan)
    builder.add_edge(START, "parse_request")
    builder.add_edge("parse_request", "collect_context")
    builder.add_edge("collect_context", "create_plan")
    builder.add_edge("create_plan", END)
    return builder.compile()
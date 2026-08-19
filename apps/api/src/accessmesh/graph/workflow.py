"""权限申请的 LangGraph 工作流骨架。"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from accessmesh.graph.state import AccessRequestState


def parse_request(state: AccessRequestState) -> dict[str, Any]:
    """将原始申请转换为初步意图；结构化 LLM 解析将在第三阶段接入。"""
    return {
        "parsed_intent": {"task": state["raw_request"], "requires_llm_planning": True},
        "status": "COLLECTING_CONTEXT",
    }


def collect_context(_: AccessRequestState) -> dict[str, Any]:
    """预留身份与资源上下文收集节点。"""

    return {"identity_context": {}, "resource_context": {}, "status": "PLANNING"}


def create_plan(_: AccessRequestState) -> dict[str, Any]:
    """预留最小权限方案生成节点。"""

    return {"proposed_grants": [], "status": "SCAFFOLD_READY"}


def build_access_request_graph() -> Any:
    """按“解析申请→收集上下文→生成方案”的顺序构建可执行图。"""

    builder = StateGraph(AccessRequestState)
    builder.add_node("parse_request", parse_request)
    builder.add_node("collect_context", collect_context)
    builder.add_node("create_plan", create_plan)
    builder.add_edge(START, "parse_request")
    builder.add_edge("parse_request", "collect_context")
    builder.add_edge("collect_context", "create_plan")
    builder.add_edge("create_plan", END)
    return builder.compile()

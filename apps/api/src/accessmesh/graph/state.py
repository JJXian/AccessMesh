"""LangGraph 权限申请工作流在节点间共享的状态结构。"""

from typing import Any, TypedDict


class AccessRequestState(TypedDict, total=False):
    """工作流状态；字段为可选，以支持各节点逐步补全处理结果。"""

    request_id: str
    trace_id: str
    raw_request: str
    parsed_intent: dict[str, Any]
    identity_context: dict[str, Any]
    resource_context: dict[str, Any]
    proposed_grants: list[dict[str, Any]]
    # 规划器生成方案时采用的默认值、未确认信息等说明。
    plan_assumptions: list[str]
    policy_decision: dict[str, Any]
    risk_findings: list[dict[str, Any]]
    status: str
    errors: list[dict[str, Any]]
    replan_count: int

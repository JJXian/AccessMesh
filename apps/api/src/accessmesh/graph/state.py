"""LangGraph 权限申请工作流在节点间共享的状态结构。"""

from typing import Any, TypedDict


class AccessRequestState(TypedDict, total=False):
    """工作流状态；字段为可选，以支持各节点逐步补全处理结果。"""

    request_id: str
    trace_id: str
    # 最终被授予权限的主体外部标识。
    subject_external_id: str
    raw_request: str
    parsed_intent: dict[str, Any]
    # 请求解析方式、Prompt版本、耗时和Token等非敏感指标。
    parser_metadata: dict[str, Any]
    identity_context: dict[str, Any]
    resource_context: dict[str, Any]
    proposed_grants: list[dict[str, Any]]
    # 每条候选授权方案对应的一条 OPA 决策结果。
    policy_decisions: list[dict[str, Any]]
    # 规划器生成方案时采用的默认值、未确认信息等说明。
    plan_assumptions: list[str]
    risk_findings: list[dict[str, Any]]
    status: str
    errors: list[dict[str, Any]]
    replan_count: int

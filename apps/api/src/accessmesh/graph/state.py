from typing import Any, TypedDict


class AccessRequestState(TypedDict, total=False):
    request_id: str
    trace_id: str
    raw_request: str
    parsed_intent: dict[str, Any]
    identity_context: dict[str, Any]
    resource_context: dict[str, Any]
    proposed_grants: list[dict[str, Any]]
    policy_decision: dict[str, Any]
    risk_findings: list[dict[str, Any]]
    status: str
    errors: list[dict[str, Any]]
    replan_count: int

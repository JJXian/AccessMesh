"""API 输入输出及策略决策的数据校验模型。"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from accessmesh.domain.enums import (
    Environment,
    IntentField,
    RequestStatus,
    ResourceType,
    SubjectType,
)

class HealthRead(BaseModel):
    """健康检查响应。"""

    status: str
    service: str
    version: str


class DemoUserRead(BaseModel):
    """对外展示的演示用户信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    username: str
    display_name: str
    role: str
    subject_type: SubjectType
    department: str
    employment_status: str


class ResourceRead(BaseModel):
    """对外展示的可申请资源信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    name: str
    resource_type: ResourceType
    environment: Environment
    sensitivity: str
    owner_external_id: str
    allowed_permissions: list[str]
    enabled: bool


class AccessRequestCreate(BaseModel):
    """创建权限申请时由客户端提交的字段。"""

    subject_external_id: str
    request_text: str = Field(min_length=5, max_length=4000)
    client_request_id: str = Field(min_length=3, max_length=128)


class AccessRequestRead(BaseModel):
    """权限申请的完整读取模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_external_id: str
    subject_external_id: str
    raw_request: str
    client_request_id: str
    status: RequestStatus
    trace_id: str
    created_at: datetime
    updated_at: datetime

class ParsedIntent(BaseModel):
    """将自然语言申请解析为后续规划可消费的结构化意图。"""

    task: str | None = Field(default=None, min_length=1, max_length=2000)
    resource_hints: list[str] = Field(default_factory=list)
    action_hints: list[str] = Field(default_factory=list)
    duration_days: int | None = Field(default=None, ge=1, le=365)
    missing_fields: list[IntentField] = Field(default_factory=list)


class CandidateGrant(BaseModel):
    """规划器提出的候选权限；尚未经过策略、审批或执行。"""

    resource_external_id: str = Field(min_length=3, max_length=160)
    permission: str = Field(min_length=1, max_length=128)
    duration_days: int = Field(ge=1, le=365)
    reason: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list)


class PlanResult(BaseModel):
    """一次最小权限规划的结构化结果。"""

    grants: list[CandidateGrant] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    """OPA 策略输出；默认拒绝并保留违规原因和审批要求。"""

    allow: bool = False
    risk_level: str = "unknown"
    violations: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    max_duration_days: int | None = None
    policy_version: str = "unknown"

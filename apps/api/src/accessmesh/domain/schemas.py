from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from accessmesh.domain.enums import Environment, RequestStatus, ResourceType, SubjectType


class HealthRead(BaseModel):
    status: str
    service: str
    version: str


class DemoUserRead(BaseModel):
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
    subject_external_id: str
    request_text: str = Field(min_length=5, max_length=4000)
    client_request_id: str = Field(min_length=3, max_length=128)


class AccessRequestRead(BaseModel):
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


class PolicyDecision(BaseModel):
    allow: bool = False
    risk_level: str = "unknown"
    violations: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    max_duration_days: int | None = None
    policy_version: str = "unknown"

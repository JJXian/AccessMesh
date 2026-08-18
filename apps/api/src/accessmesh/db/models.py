from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from accessmesh.db.base import Base
from accessmesh.domain.enums import Environment, RequestStatus, ResourceType, SubjectType


def utc_now() -> datetime:
    return datetime.now(UTC)


class DemoUser(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(128), unique=True)
    display_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(64), index=True)
    subject_type: Mapped[SubjectType] = mapped_column(String(32))
    department: Mapped[str] = mapped_column(String(128))
    employment_status: Mapped[str] = mapped_column(String(32), default="active")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    resource_type: Mapped[ResourceType] = mapped_column(String(32), index=True)
    environment: Mapped[Environment] = mapped_column(String(32), index=True)
    sensitivity: Mapped[str] = mapped_column(String(8), default="L1")
    owner_external_id: Mapped[str] = mapped_column(String(128))
    allowed_permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(default=True)


class AccessRequest(Base):
    __tablename__ = "access_requests"
    __table_args__ = (
        UniqueConstraint("requester_external_id", "client_request_id", name="uq_request_client"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    requester_external_id: Mapped[str] = mapped_column(String(128), index=True)
    subject_external_id: Mapped[str] = mapped_column(String(128), index=True)
    raw_request: Mapped[str] = mapped_column(Text)
    client_request_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[RequestStatus] = mapped_column(String(32), default=RequestStatus.SUBMITTED)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    actor_external_id: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

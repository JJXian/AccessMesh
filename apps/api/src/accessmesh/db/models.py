"""权限治理核心数据表的 ORM 映射。"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from accessmesh.db.base import Base
from accessmesh.domain.enums import Environment, RequestStatus, ResourceType, SubjectType


def utc_now() -> datetime:
    """生成带 UTC 时区的时间，供模型默认值和更新时间复用。"""

    return datetime.now(UTC)


class DemoUser(Base):
    """演示身份；生产环境应由真实身份提供方替代。"""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("external_id"),
        UniqueConstraint("username"),
        Index("ix_users_external_id", "external_id"),
        Index("ix_users_role", "role"),
        {"comment": "演示环境用户身份表"},
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="用户主键"
    )
    external_id: Mapped[str] = mapped_column(String(128), comment="外部身份系统中的用户唯一标识")
    username: Mapped[str] = mapped_column(String(128), comment="用户名")
    display_name: Mapped[str] = mapped_column(String(128), comment="用户显示名称")
    role: Mapped[str] = mapped_column(String(64), comment="系统角色")
    subject_type: Mapped[SubjectType] = mapped_column(String(32), comment="权限主体类型")
    department: Mapped[str] = mapped_column(String(128), comment="所属部门")
    employment_status: Mapped[str] = mapped_column(String(32), default="active", comment="任职状态")
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, comment="用户扩展属性（JSON）"
    )


class Resource(Base):
    """可被申请和授权的外部资源目录项。"""

    __tablename__ = "resources"
    __table_args__ = (
        UniqueConstraint("external_id"),
        Index("ix_resources_external_id", "external_id"),
        Index("ix_resources_environment", "environment"),
        Index("ix_resources_resource_type", "resource_type"),
        {"comment": "权限治理资源目录表"},
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="资源主键"
    )
    external_id: Mapped[str] = mapped_column(String(160), comment="外部资源唯一标识")
    name: Mapped[str] = mapped_column(String(160), comment="资源名称")
    resource_type: Mapped[ResourceType] = mapped_column(String(32), comment="资源类型")
    environment: Mapped[Environment] = mapped_column(String(32), comment="资源所属环境")
    sensitivity: Mapped[str] = mapped_column(String(8), default="L1", comment="资源敏感等级")
    owner_external_id: Mapped[str] = mapped_column(String(128), comment="资源负责人外部标识")
    allowed_permissions: Mapped[list[str]] = mapped_column(
        JSON, default=list, comment="资源允许申请的权限集合（JSON）"
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, comment="资源扩展元数据（JSON）"
    )
    enabled: Mapped[bool] = mapped_column(default=True, comment="资源是否启用")


class AccessRequest(Base):
    """记录自然语言权限申请及其工作流状态。"""

    __tablename__ = "access_requests"
    __table_args__ = (
        UniqueConstraint("requester_external_id", "client_request_id", name="uq_request_client"),
        Index("ix_access_requests_requester", "requester_external_id"),
        Index("ix_access_requests_subject", "subject_external_id"),
        Index("ix_access_requests_trace", "trace_id"),
        {"comment": "权限申请单表"},
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="权限申请主键"
    )
    requester_external_id: Mapped[str] = mapped_column(String(128), comment="申请发起人外部标识")
    subject_external_id: Mapped[str] = mapped_column(String(128), comment="权限授予主体外部标识")
    raw_request: Mapped[str] = mapped_column(Text, comment="用户提交的原始权限申请文本")
    client_request_id: Mapped[str] = mapped_column(String(128), comment="客户端请求幂等标识")
    status: Mapped[RequestStatus] = mapped_column(
        String(32), default=RequestStatus.SUBMITTED, comment="权限申请当前状态"
    )
    trace_id: Mapped[str] = mapped_column(String(64), comment="全链路追踪标识")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, comment="最后更新时间"
    )


class ProposedGrant(Base):
    """规划器提出的候选权限，尚未经过策略、审批或执行。"""

    __tablename__ = "proposed_grants"
    __table_args__ = (
        UniqueConstraint(
            "request_id",
            "resource_id",
            "permission",
            "plan_version",
            name="uq_proposed_grant_plan_item",
        ),
        CheckConstraint(
            "duration_days > 0",
            name="ck_proposed_grants_duration_positive",
        ),
        CheckConstraint(
            "plan_version > 0",
            name="ck_proposed_grants_plan_version_positive",
        ),
        Index("ix_proposed_grants_request_plan", "request_id", "plan_version"),
        Index("ix_proposed_grants_resource", "resource_id"),
        {"comment": "权限规划阶段生成的候选授权方案表"},
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="候选授权主键",
    )
    request_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("access_requests.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属权限申请主键",
    )
    resource_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resources.id"),
        nullable=False,
        comment="目标资源主键",
    )
    permission: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="候选权限名称",
    )
    duration_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="建议授权期限（天）",
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="建议该权限的业务理由",
    )
    evidence_refs: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="支撑规划结论的证据引用（JSON）",
    )
    plan_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="权限方案版本号",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        comment="候选方案生成时间",
    )


class AuditEvent(Base):
    """记录权限治理链路中不可变的审计事件。"""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_request", "request_id"),
        Index("ix_audit_events_trace", "trace_id"),
        Index("ix_audit_events_type", "event_type"),
        {"comment": "权限治理审计事件表"},
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="审计事件主键"
    )
    request_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), comment="关联的权限申请主键"
    )
    trace_id: Mapped[str] = mapped_column(String(64), comment="全链路追踪标识")
    event_type: Mapped[str] = mapped_column(String(128), comment="审计事件类型")
    actor_external_id: Mapped[str] = mapped_column(String(128), comment="事件操作者外部标识")
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, comment="事件详情载荷（JSON）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, comment="事件发生时间"
    )

"""创建 AccessMesh 初始数据表。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建用户、资源、权限申请和审计事件表及其索引。"""

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("department", sa.String(128), nullable=False),
        sa.Column("employment_status", sa.String(32), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.UniqueConstraint("external_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_external_id", "users", ["external_id"])
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(160), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("sensitivity", sa.String(8), nullable=False),
        sa.Column("owner_external_id", sa.String(128), nullable=False),
        sa.Column("allowed_permissions", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_resources_external_id", "resources", ["external_id"])
    op.create_index("ix_resources_environment", "resources", ["environment"])
    op.create_index("ix_resources_resource_type", "resources", ["resource_type"])

    op.create_table(
        "access_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requester_external_id", sa.String(128), nullable=False),
        sa.Column("subject_external_id", sa.String(128), nullable=False),
        sa.Column("raw_request", sa.Text(), nullable=False),
        sa.Column("client_request_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("requester_external_id", "client_request_id", name="uq_request_client"),
    )
    op.create_index("ix_access_requests_requester", "access_requests", ["requester_external_id"])
    op.create_index("ix_access_requests_subject", "access_requests", ["subject_external_id"])
    op.create_index("ix_access_requests_trace", "access_requests", ["trace_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("actor_external_id", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_request", "audit_events", ["request_id"])
    op.create_index("ix_audit_events_trace", "audit_events", ["trace_id"])
    op.create_index("ix_audit_events_type", "audit_events", ["event_type"])


def downgrade() -> None:
    """按依赖关系的逆序移除初始数据表。"""

    op.drop_table("audit_events")
    op.drop_table("access_requests")
    op.drop_table("resources")
    op.drop_table("users")

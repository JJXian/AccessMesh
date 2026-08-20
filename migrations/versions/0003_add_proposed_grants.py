"""Add proposed grants table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proposed_grants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="候选授权主键",
        ),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="所属权限申请主键",
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="目标资源主键",
        ),
        sa.Column(
            "permission",
            sa.String(length=128),
            nullable=False,
            comment="候选权限名称",
        ),
        sa.Column(
            "duration_days",
            sa.Integer(),
            nullable=False,
            comment="建议授权期限（天）",
        ),
        sa.Column(
            "reason",
            sa.Text(),
            nullable=False,
            comment="建议该权限的业务理由",
        ),
        sa.Column(
            "evidence_refs",
            sa.JSON(),
            nullable=False,
            comment="支撑规划结论的证据引用（JSON）",
        ),
        sa.Column(
            "plan_version",
            sa.Integer(),
            nullable=False,
            comment="权限方案版本号",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="候选方案生成时间",
        ),
        sa.CheckConstraint(
            "duration_days > 0",
            name="ck_proposed_grants_duration_positive",
        ),
        sa.CheckConstraint(
            "plan_version > 0",
            name="ck_proposed_grants_plan_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["access_requests.id"],
            name="fk_proposed_grants_request",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.id"],
            name="fk_proposed_grants_resource",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "request_id",
            "resource_id",
            "permission",
            "plan_version",
            name="uq_proposed_grant_plan_item",
        ),
        comment="权限规划阶段生成的候选授权方案表",
    )
    op.create_index(
        "ix_proposed_grants_request_plan",
        "proposed_grants",
        ["request_id", "plan_version"],
    )
    op.create_index(
        "ix_proposed_grants_resource",
        "proposed_grants",
        ["resource_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_proposed_grants_resource", table_name="proposed_grants")
    op.drop_index("ix_proposed_grants_request_plan", table_name="proposed_grants")
    op.drop_table("proposed_grants")

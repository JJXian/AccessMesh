"""新增 policy decisions 表."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 OPA 策略决策记录表。"""

    op.create_table(
        "policy_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="策略决策主键",
        ),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="所属权限申请主键",
        ),
        sa.Column(
            "proposed_grant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="关联的候选授权方案主键",
        ),
        sa.Column(
            "policy_input",
            sa.JSON(),
            nullable=False,
            comment="提交给 OPA 的策略输入快照（JSON）",
        ),
        sa.Column(
            "allow",
            sa.Boolean(),
            nullable=False,
            comment="OPA 是否允许该候选授权方案",
        ),
        sa.Column(
            "risk_level",
            sa.String(length=32),
            nullable=False,
            comment="OPA 评估出的风险等级",
        ),
        sa.Column(
            "violations",
            sa.JSON(),
            nullable=False,
            comment="OPA 返回的策略违规原因列表（JSON）",
        ),
        sa.Column(
            "required_approvals",
            sa.JSON(),
            nullable=False,
            comment="OPA 要求的审批角色列表（JSON）",
        ),
        sa.Column(
            "max_duration_days",
            sa.Integer(),
            nullable=True,
            comment="OPA 允许的最长授权时长（天）",
        ),
        sa.Column(
            "policy_version",
            sa.String(length=128),
            nullable=False,
            comment="命中的 OPA 策略版本",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="策略决策创建时间",
        ),
        sa.CheckConstraint(
            "max_duration_days IS NULL OR max_duration_days > 0",
            name="ck_policy_decisions_max_duration_positive",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["access_requests.id"],
            name="fk_policy_decisions_request",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_grant_id"],
            ["proposed_grants.id"],
            name="fk_policy_decisions_proposed_grant",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposed_grant_id",
            name="uq_policy_decisions_proposed_grant",
        ),
        comment="OPA 策略决策记录表",
    )
    op.create_index(
        "ix_policy_decisions_request",
        "policy_decisions",
        ["request_id"],
    )
    op.create_index(
        "ix_policy_decisions_allow",
        "policy_decisions",
        ["allow"],
    )


def downgrade() -> None:
    """删除 OPA 策略决策记录表。"""

    op.drop_index("ix_policy_decisions_allow", table_name="policy_decisions")
    op.drop_index("ix_policy_decisions_request", table_name="policy_decisions")
    op.drop_table("policy_decisions")

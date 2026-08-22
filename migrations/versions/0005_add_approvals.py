"""新增approvals table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建人工审批记录表。"""

    op.create_table(
        "approvals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="审批记录主键",
        ),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="所属权限申请主键",
        ),
        sa.Column(
            "approver_external_id",
            sa.String(length=128),
            nullable=False,
            comment="审批人外部身份标识",
        ),
        sa.Column(
            "decision",
            sa.String(length=32),
            nullable=False,
            comment="审批最终决定",
        ),
        sa.Column(
            "comment",
            sa.Text(),
            nullable=True,
            comment="审批意见",
        ),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="审批决定时间",
        ),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')",
            name="ck_approvals_decision",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["access_requests.id"],
            name="fk_approvals_request",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "request_id",
            name="uq_approvals_request",
        ),
        comment="权限申请人工审批记录表",
    )
    op.create_index(
        "ix_approvals_approver",
        "approvals",
        ["approver_external_id"],
    )
    op.create_index(
        "ix_approvals_decision",
        "approvals",
        ["decision"],
    )


def downgrade() -> None:
    """删除人工审批记录表。"""

    op.drop_index("ix_approvals_decision", table_name="approvals")
    op.drop_index("ix_approvals_approver", table_name="approvals")
    op.drop_table("approvals")

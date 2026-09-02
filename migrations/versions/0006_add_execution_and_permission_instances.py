"""Add execution tasks and permission instances."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建执行任务表和已生效权限实例表。"""

    op.create_table(
        "execution_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="执行任务主键",
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
            "status",
            sa.String(length=32),
            nullable=False,
            comment="执行任务当前状态",
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=160),
            nullable=False,
            comment="调用外部资源适配器的幂等键",
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            comment="已执行尝试次数",
        ),
        sa.Column(
            "result",
            sa.JSON(),
            nullable=False,
            comment="外部资源适配器返回结果（JSON）",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="最近一次执行失败原因",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="执行任务创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="执行任务最后更新时间",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_execution_tasks_attempt_count_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'COMPENSATED')",
            name="ck_execution_tasks_status",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["access_requests.id"],
            name="fk_execution_tasks_request",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_grant_id"],
            ["proposed_grants.id"],
            name="fk_execution_tasks_proposed_grant",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposed_grant_id",
            name="uq_execution_tasks_proposed_grant",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_execution_tasks_idempotency_key",
        ),
        comment="权限授予执行任务表",
    )
    op.create_index(
        "ix_execution_tasks_request_status",
        "execution_tasks",
        ["request_id", "status"],
    )

    op.create_table(
        "permission_instances",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="权限实例主键",
        ),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="来源权限申请主键",
        ),
        sa.Column(
            "execution_task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="来源执行任务主键",
        ),
        sa.Column(
            "subject_external_id",
            sa.String(length=128),
            nullable=False,
            comment="实际获得权限的主体外部标识",
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
            comment="已生效权限名称",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            comment="权限实例当前状态",
        ),
        sa.Column(
            "external_grant_id",
            sa.String(length=160),
            nullable=False,
            comment="外部资源系统返回的授权操作标识",
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="权限实际生效时间",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="权限到期时间",
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="权限撤销时间",
        ),
        sa.Column(
            "revocation_reason",
            sa.Text(),
            nullable=True,
            comment="撤销原因",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED')",
            name="ck_permission_instances_status",
        ),
        sa.CheckConstraint(
            "expires_at > granted_at",
            name="ck_permission_instances_expiry_after_grant",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= granted_at",
            name="ck_permission_instances_revoked_after_grant",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["access_requests.id"],
            name="fk_permission_instances_request",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["execution_task_id"],
            ["execution_tasks.id"],
            name="fk_permission_instances_execution_task",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.id"],
            name="fk_permission_instances_resource",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_task_id",
            name="uq_permission_instances_execution_task",
        ),
        comment="已生效权限实例表",
    )
    op.create_index(
        "ix_permission_instances_subject_status",
        "permission_instances",
        ["subject_external_id", "status"],
    )
    op.create_index(
        "ix_permission_instances_expiry_status",
        "permission_instances",
        ["expires_at", "status"],
    )


def downgrade() -> None:
    """删除执行任务表和已生效权限实例表。"""

    op.drop_index(
        "ix_permission_instances_expiry_status",
        table_name="permission_instances",
    )
    op.drop_index(
        "ix_permission_instances_subject_status",
        table_name="permission_instances",
    )
    op.drop_table("permission_instances")

    op.drop_index(
        "ix_execution_tasks_request_status",
        table_name="execution_tasks",
    )
    op.drop_table("execution_tasks")

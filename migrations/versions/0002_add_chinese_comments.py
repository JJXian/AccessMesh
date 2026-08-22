"""为已有数据表和字段补充中文数据库注释。"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_COMMENTS = {
    "users": "演示环境用户身份表",
    "resources": "权限治理资源目录表",
    "access_requests": "权限申请单表",
    "audit_events": "权限治理审计事件表",
}

COLUMN_COMMENTS = {
    "users": {
        "id": "用户主键",
        "external_id": "外部身份系统中的用户唯一标识",
        "username": "用户名",
        "display_name": "用户显示名称",
        "role": "系统角色",
        "subject_type": "权限主体类型",
        "department": "所属部门",
        "employment_status": "任职状态",
        "attributes": "用户扩展属性（JSON）",
    },
    "resources": {
        "id": "资源主键",
        "external_id": "外部资源唯一标识",
        "name": "资源名称",
        "resource_type": "资源类型",
        "environment": "资源所属环境",
        "sensitivity": "资源敏感等级",
        "owner_external_id": "资源负责人外部标识",
        "allowed_permissions": "资源允许申请的权限集合（JSON）",
        "metadata": "资源扩展元数据（JSON）",
        "enabled": "资源是否启用",
    },
    "access_requests": {
        "id": "权限申请主键",
        "requester_external_id": "申请发起人外部标识",
        "subject_external_id": "权限授予主体外部标识",
        "raw_request": "用户提交的原始权限申请文本",
        "client_request_id": "客户端请求幂等标识",
        "status": "权限申请当前状态",
        "trace_id": "全链路追踪标识",
        "created_at": "创建时间",
        "updated_at": "最后更新时间",
    },
    "audit_events": {
        "id": "审计事件主键",
        "request_id": "关联的权限申请主键",
        "trace_id": "全链路追踪标识",
        "event_type": "审计事件类型",
        "actor_external_id": "事件操作者外部标识",
        "payload": "事件详情载荷（JSON）",
        "created_at": "事件发生时间",
    },
}


def upgrade() -> None:
    """批量写入表注释和字段注释。"""

    for table_name, table_comment in TABLE_COMMENTS.items():
        op.create_table_comment(table_name, table_comment)
    for table_name, columns in COLUMN_COMMENTS.items():
        for column_name, column_comment in columns.items():
            op.alter_column(table_name, column_name, comment=column_comment)


def downgrade() -> None:
    """移除本次迁移添加的全部注释。"""

    for table_name, columns in reversed(COLUMN_COMMENTS.items()):
        for column_name, column_comment in columns.items():
            op.alter_column(
                table_name,
                column_name,
                existing_comment=column_comment,
                comment=None,
            )
    for table_name, table_comment in reversed(TABLE_COMMENTS.items()):
        op.drop_table_comment(table_name, existing_comment=table_comment)

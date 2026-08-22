"""领域对象使用的受限枚举值。"""

from enum import StrEnum


class RequestStatus(StrEnum):
    """权限申请从提交、审批、执行到撤销的完整状态集合。"""

    SUBMITTED = "SUBMITTED"
    PARSING_REQUEST = "PARSING_REQUEST"
    NEED_CLARIFICATION = "NEED_CLARIFICATION"
    COLLECTING_CONTEXT = "COLLECTING_CONTEXT"
    PLANNING = "PLANNING"
    POLICY_DENIED = "POLICY_DENIED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPENSATING = "COMPENSATING"
    VERIFYING = "VERIFYING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    FAILED = "FAILED"


class ApprovalDecision(StrEnum):
    """单次人工审批可以作出的最终决定。"""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SubjectType(StrEnum):
    """可接受权限的主体类型。"""

    EMPLOYEE = "employee"
    CONTRACTOR = "contractor"
    SERVICE_ACCOUNT = "service_account"


class ResourceType(StrEnum):
    """当前已支持接入的资源类型。"""

    GITLAB = "gitlab"
    DATABASE = "database"
    CLOUD = "cloud"


class Environment(StrEnum):
    """资源所在的部署环境；环境等级会影响策略判断。"""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class IntentField(StrEnum):
    """自然语言权限申请中必须补充的字段。"""

    TASK = "task"
    RESOURCE = "resource"
    ACTION = "action"
    DURATION = "duration"

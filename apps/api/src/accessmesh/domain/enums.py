from enum import StrEnum


class RequestStatus(StrEnum):
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


class SubjectType(StrEnum):
    EMPLOYEE = "employee"
    CONTRACTOR = "contractor"
    SERVICE_ACCOUNT = "service_account"


class ResourceType(StrEnum):
    GITLAB = "gitlab"
    DATABASE = "database"
    CLOUD = "cloud"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

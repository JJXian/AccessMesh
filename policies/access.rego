package accessmesh

default allow := false

valid_permission if {
    input.grant.permission in input.resource.allowed_permissions
}

active_subject if {
    input.subject.employment_status == "active"
}

within_duration if {
    input.resource.environment == "production"
    input.grant.duration_days <= 7
}

within_duration if {
    input.resource.environment != "production"
    input.grant.duration_days <= 30
}

contractor_allowed if {
    input.subject.subject_type != "contractor"
}

contractor_allowed if {
    input.subject.subject_type == "contractor"
    input.resource.environment != "production"
}

allow if {
    active_subject
    input.resource.enabled == true
    valid_permission
    within_duration
    contractor_allowed
}

violations contains {"code": "SUBJECT_INACTIVE", "message": "subject is not active"} if {
    not active_subject
}

violations contains {"code": "RESOURCE_DISABLED", "message": "resource is disabled"} if {
    input.resource.enabled != true
}

violations contains {"code": "INVALID_PERMISSION", "message": "permission is not available"} if {
    not valid_permission
}

violations contains {"code": "DURATION_EXCEEDED", "message": "requested duration is too long"} if {
    not within_duration
}

violations contains {"code": "CONTRACTOR_PRODUCTION_DENIED", "message": "contractor production access is denied"} if {
    not contractor_allowed
}

risk_level := "high" if {
    input.resource.environment == "production"
}

default risk_level := "medium"

decision := {
    "allow": allow,
    "risk_level": risk_level,
    "violations": violations,
    "required_approvals": ["approver"],
    "max_duration_days": 7,
    "policy_version": "v0.1.0",
}

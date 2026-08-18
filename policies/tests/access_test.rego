package accessmesh_test

import data.accessmesh

test_employee_test_read_allowed if {
    result := accessmesh.decision with input as {
        "subject": {"subject_type": "employee", "employment_status": "active"},
        "resource": {
            "environment": "test",
            "enabled": true,
            "allowed_permissions": ["read_only"],
        },
        "grant": {"permission": "read_only", "duration_days": 30},
    }
    result.allow
}

test_contractor_production_denied if {
    result := accessmesh.decision with input as {
        "subject": {"subject_type": "contractor", "employment_status": "active"},
        "resource": {
            "environment": "production",
            "enabled": true,
            "allowed_permissions": ["read_only"],
        },
        "grant": {"permission": "read_only", "duration_days": 3},
    }
    not result.allow
}

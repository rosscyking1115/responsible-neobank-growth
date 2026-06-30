"""Lightweight role-based access control over sensitive wellbeing data.

Demonstrates data minimisation: individual-level vulnerability/wellbeing fields are
only visible to roles that need them (e.g. a Consumer Duty reviewer), while analysts
work from aggregate, non-sensitive segments. This is a scoped demonstration of the
governance posture; production would enforce it via IAM / row-level security.
"""

from src.access.rbac import (
    ROLES,
    SENSITIVE_WELLBEING_FIELDS,
    AccessError,
    accessible_segments,
    assert_role,
    can_view_sensitive,
    redact_sensitive,
)

__all__ = [
    "ROLES",
    "SENSITIVE_WELLBEING_FIELDS",
    "AccessError",
    "accessible_segments",
    "assert_role",
    "can_view_sensitive",
    "redact_sensitive",
]

"""Role-based access control for sensitive wellbeing fields.

Pairs with ``src.wellbeing.guardrails`` (which governs permitted *uses*): this module
governs *who can see* individual-level sensitive data. The principle is least
privilege / data minimisation -- only roles whose job requires individual
vulnerability data may see it; others work from aggregates and non-sensitive segments.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd

Role = Literal["analyst", "consumer_duty_reviewer", "operations", "admin"]
ROLES: tuple[Role, ...] = ("analyst", "consumer_duty_reviewer", "operations", "admin")

# Individual-level fields that reveal a customer's vulnerability/wellbeing position.
SENSITIVE_WELLBEING_FIELDS: frozenset[str] = frozenset(
    {
        "vulnerable_customer_proxy",
        "vulnerable_customer_flag",
        "accessibility_need_proxy",
        "new_to_uk_proxy",
        "student_proxy",
        "income_volatility_score",
        "salary_regularity_score",
        "cash_buffer_proxy",
        "bill_pressure_score",
        "overdraft_risk_proxy",
        "missed_payment_proxy",
        "complaint_history_flag",
        "digital_confidence_score",
        "support_contact_frequency",
    }
)

# Roles permitted to view individual-level sensitive wellbeing data.
_SENSITIVE_VIEW_ROLES: frozenset[str] = frozenset({"consumer_duty_reviewer", "admin"})


class AccessError(ValueError):
    """Raised for an unknown role."""


def assert_role(role: str) -> None:
    if role not in ROLES:
        raise AccessError(f"unknown role '{role}'. Known roles: {list(ROLES)}.")


def can_view_sensitive(role: str) -> bool:
    """Whether the role may see individual-level sensitive wellbeing fields."""
    assert_role(role)
    return role in _SENSITIVE_VIEW_ROLES


def redact_sensitive(frame: pd.DataFrame, role: str) -> pd.DataFrame:
    """Drop individual-level sensitive columns the role is not permitted to see.

    A no-op for roles that may view sensitive data; otherwise returns a copy with the
    sensitive columns removed (the rest of the frame stays usable for aggregate work).
    """
    if can_view_sensitive(role):
        return frame
    drop = [column for column in frame.columns if column in SENSITIVE_WELLBEING_FIELDS]
    return frame.drop(columns=drop)


def accessible_segments(role: str, segments: list[str]) -> list[str]:
    """Filter a list of segment dimensions to those the role may slice by."""
    if can_view_sensitive(role):
        return list(segments)
    return [segment for segment in segments if segment not in SENSITIVE_WELLBEING_FIELDS]

from __future__ import annotations

import pandas as pd
import pytest

from src.access import (
    AccessError,
    accessible_segments,
    assert_role,
    can_view_sensitive,
    redact_sensitive,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": ["u1", "u2"],
            "income_band": ["low", "high"],
            "digital_confidence_band": ["low", "high"],
            "activated_d7": [True, False],
            "vulnerable_customer_proxy": [True, False],
            "overdraft_risk_proxy": [0.8, 0.2],
        }
    )


def test_assert_role_rejects_unknown() -> None:
    with pytest.raises(AccessError):
        assert_role("ceo")
    assert_role("analyst")  # known role does not raise


@pytest.mark.parametrize(
    "role,expected",
    [
        ("consumer_duty_reviewer", True),
        ("admin", True),
        ("analyst", False),
        ("operations", False),
    ],
)
def test_can_view_sensitive(role: str, expected: bool) -> None:
    assert can_view_sensitive(role) is expected


def test_redact_sensitive_drops_fields_for_analyst() -> None:
    redacted = redact_sensitive(_frame(), "analyst")
    assert "vulnerable_customer_proxy" not in redacted.columns
    assert "overdraft_risk_proxy" not in redacted.columns
    # Non-sensitive columns survive.
    assert {"user_id", "income_band", "activated_d7"} <= set(redacted.columns)


def test_redact_sensitive_is_noop_for_reviewer() -> None:
    frame = _frame()
    redacted = redact_sensitive(frame, "consumer_duty_reviewer")
    assert list(redacted.columns) == list(frame.columns)


def test_accessible_segments_filters_for_analyst() -> None:
    segments = ["income_band", "digital_confidence_band", "vulnerable_customer_proxy"]
    assert accessible_segments("analyst", segments) == [
        "income_band",
        "digital_confidence_band",
    ]
    assert accessible_segments("consumer_duty_reviewer", segments) == segments


def test_redact_sensitive_rejects_unknown_role() -> None:
    with pytest.raises(AccessError):
        redact_sensitive(_frame(), "intern")

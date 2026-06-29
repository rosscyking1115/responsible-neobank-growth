"""Map transfer risk signals to a supportive scam-intervention decision.

Escalating, supportive responses only -- no action, education, soft friction,
cooling-off, or a human-review recommendation. The simulation never blocks a payment
or makes a punitive decision; it models risk-triggered support and education.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from src.protection.friction_rules import (
    DEFAULT_PROTECTION_THRESHOLDS,
    RISK_WEIGHTS,
    ProtectionThresholds,
)

ProtectionAction = Literal[
    "no_action",
    "education_prompt",
    "soft_friction",
    "cooling_off_period",
    "human_review_recommendation",
]

# Every possible action is supportive; the simulation cannot block or deny.
SUPPORTIVE_ACTIONS: frozenset[ProtectionAction] = frozenset(
    {
        "no_action",
        "education_prompt",
        "soft_friction",
        "cooling_off_period",
        "human_review_recommendation",
    }
)


@dataclass(frozen=True)
class ProtectionEvent:
    event_id: str
    user_id: str = ""
    amount_gbp: float = 0.0
    new_payee: bool = False
    first_large_transfer: bool = False
    unusual_time: bool = False
    recent_device_change: bool = False
    viewed_scam_warning: bool = False
    ignored_warning: bool = False
    confirmed_transfer: bool = False
    support_contact_about_scam: bool = False
    investment_context: bool = False
    vulnerable_customer: bool = False


@dataclass(frozen=True)
class InterventionDecision:
    event_id: str
    action: ProtectionAction
    risk_score: float
    reasons: list[str] = field(default_factory=list)


def risk_score(
    event: ProtectionEvent,
    thresholds: ProtectionThresholds = DEFAULT_PROTECTION_THRESHOLDS,
) -> float:
    """Sum weighted risk signals into a 0..1 score."""
    large_amount = event.amount_gbp >= thresholds.large_amount_gbp
    warning_heeded = event.viewed_scam_warning and not event.ignored_warning
    contributions = {
        "new_payee": event.new_payee,
        "first_large_transfer": event.first_large_transfer,
        "large_amount": large_amount,
        "unusual_time": event.unusual_time,
        "recent_device_change": event.recent_device_change,
        "ignored_warning": event.ignored_warning,
        "support_contact_about_scam": event.support_contact_about_scam,
        "investment_context": event.investment_context,
        "vulnerable_customer": event.vulnerable_customer,
        "confirmed_transfer": event.confirmed_transfer,
        "viewed_warning_heeded": warning_heeded,
    }
    score = sum(RISK_WEIGHTS[name] for name, active in contributions.items() if active)
    return round(max(0.0, min(1.0, score)), 4)


def _active_reasons(event: ProtectionEvent) -> list[str]:
    labels = {
        "new_payee": "new payee",
        "first_large_transfer": "first large transfer",
        "unusual_time": "unusual time",
        "recent_device_change": "recent device change",
        "ignored_warning": "ignored scam warning",
        "support_contact_about_scam": "contacted support about a scam",
        "investment_context": "investment context",
        "vulnerable_customer": "vulnerable customer",
    }
    return [label for attr, label in labels.items() if getattr(event, attr)]


def decide_intervention(
    event: ProtectionEvent,
    thresholds: ProtectionThresholds = DEFAULT_PROTECTION_THRESHOLDS,
) -> InterventionDecision:
    """Choose the supportive intervention for a transfer event."""
    score = risk_score(event, thresholds)
    reasons = _active_reasons(event)

    if event.support_contact_about_scam or (
        score >= thresholds.high_risk and event.vulnerable_customer
    ):
        action: ProtectionAction = "human_review_recommendation"
    elif score >= thresholds.high_risk:
        action = "cooling_off_period"
    elif score >= thresholds.medium_risk:
        action = "soft_friction"
    elif score >= thresholds.low_risk or event.investment_context:
        action = "education_prompt"
    else:
        action = "no_action"

    if not reasons:
        reasons = ["no elevated risk signals"]
    return InterventionDecision(
        event_id=event.event_id,
        action=action,
        risk_score=score,
        reasons=reasons,
    )


_EVENT_FIELDS = ProtectionEvent.__dataclass_fields__.keys()


def assess_events(
    events: pd.DataFrame,
    thresholds: ProtectionThresholds = DEFAULT_PROTECTION_THRESHOLDS,
) -> pd.DataFrame:
    """Apply the intervention rules to a frame of protection events.

    Returns one row per event with ``risk_score``, ``action``, and ``reasons``.
    """
    columns = ["event_id", "user_id", "risk_score", "action", "reasons"]
    if events.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for record in events.to_dict(orient="records"):
        kwargs = {key: record[key] for key in _EVENT_FIELDS if key in record}
        # The persisted table names the id "protection_event_id".
        if "event_id" not in kwargs and "protection_event_id" in record:
            kwargs["event_id"] = record["protection_event_id"]
        event = ProtectionEvent(**kwargs)
        decision = decide_intervention(event, thresholds)
        rows.append(
            {
                "event_id": decision.event_id,
                "user_id": event.user_id,
                "risk_score": decision.risk_score,
                "action": decision.action,
                "reasons": ", ".join(decision.reasons),
            }
        )
    return pd.DataFrame(rows, columns=columns)

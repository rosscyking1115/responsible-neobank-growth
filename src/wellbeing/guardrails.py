"""Use-boundary guardrails for synthetic wellbeing proxies.

Wellbeing proxies exist to support *supportive* product decisions and outcome
monitoring. They must never drive punitive, credit, pricing-penalty, or
service-denial decisions. These guardrails make the boundary executable so it can
be asserted in tests and at call sites rather than living only in documentation.
"""

from __future__ import annotations

PERMITTED_USES = frozenset(
    {
        "supportive_onboarding",
        "experiment_monitoring",
        "customer_outcome_analysis",
        "pricing_scenario_governance",
        "fairness_gap_detection",
        "support_burden_monitoring",
        "responsible_release_planning",
    }
)

PROHIBITED_USES = frozenset(
    {
        "credit_eligibility",
        "account_closure",
        "punitive_treatment",
        "unfair_pricing",
        "real_vulnerability_labelling",
        "financial_advice",
        "automated_fraud_blocking",
        "denial_of_services",
    }
)

# Interventions that are allowed to be triggered off the back of wellbeing signals.
# Anything outside this set is treated as potentially punitive and rejected.
SUPPORTIVE_DECISIONS = frozenset(
    {
        "assisted_onboarding",
        "clearer_communication",
        "education_prompt",
        "soft_friction",
        "cooling_off_period",
        "prioritise_support",
        "human_review",
        "monitor",
        "no_action",
    }
)


class ProhibitedUseError(ValueError):
    """Raised when wellbeing proxies are requested for a non-permitted use."""


def assert_permitted_use(use: str) -> None:
    """Allow only explicitly permitted uses; reject prohibited and unknown ones."""

    if use in PROHIBITED_USES:
        raise ProhibitedUseError(
            f"'{use}' is a prohibited use of wellbeing proxies. "
            "These fields are synthetic and must not be used for punitive, credit, "
            "pricing-penalty, fraud-blocking, or service-denial decisions."
        )
    if use not in PERMITTED_USES:
        raise ProhibitedUseError(
            f"'{use}' is not an explicitly permitted use. "
            f"Permitted uses: {sorted(PERMITTED_USES)}."
        )


def assert_supportive_decision(decision: str) -> None:
    """Reject any decision that is not in the supportive intervention set."""

    if decision not in SUPPORTIVE_DECISIONS:
        raise ProhibitedUseError(
            f"'{decision}' is not a supportive decision. Wellbeing proxies may only "
            f"trigger supportive interventions: {sorted(SUPPORTIVE_DECISIONS)}."
        )


def is_permitted_use(use: str) -> bool:
    """Non-raising variant of :func:`assert_permitted_use`."""

    try:
        assert_permitted_use(use)
    except ProhibitedUseError:
        return False
    return True

from __future__ import annotations

from datetime import date

import pandas as pd

from data_generator.config import GeneratorConfig
from data_generator.protection import generate_protection_events
from data_generator.users import generate_users
from src.protection import (
    SUPPORTIVE_ACTIONS,
    ProtectionEvent,
    decide_intervention,
    risk_score,
)


def _event(**overrides) -> ProtectionEvent:
    base = {"event_id": "prot_1"}
    base.update(overrides)
    return ProtectionEvent(**base)


# --- rules engine -----------------------------------------------------------


def test_clean_event_takes_no_action() -> None:
    decision = decide_intervention(_event(confirmed_transfer=True))
    assert decision.action == "no_action"
    assert decision.risk_score == 0.0


def test_investment_context_always_educates() -> None:
    assert decide_intervention(_event(investment_context=True)).action == "education_prompt"


def test_moderate_risk_applies_soft_friction() -> None:
    decision = decide_intervention(
        _event(new_payee=True, first_large_transfer=True, amount_gbp=5000.0)
    )
    # 0.20 + 0.25 + 0.20 = 0.65 -> medium band
    assert decision.action == "soft_friction"


def test_high_risk_triggers_cooling_off() -> None:
    decision = decide_intervention(
        _event(
            new_payee=True,
            first_large_transfer=True,
            amount_gbp=5000.0,
            recent_device_change=True,
            ignored_warning=True,
            viewed_scam_warning=True,
        )
    )
    assert decision.risk_score >= 0.70
    assert decision.action == "cooling_off_period"


def test_support_contact_routes_to_human_review() -> None:
    decision = decide_intervention(_event(support_contact_about_scam=True))
    assert decision.action == "human_review_recommendation"


def test_vulnerable_high_risk_routes_to_human_review() -> None:
    decision = decide_intervention(
        _event(
            vulnerable_customer=True,
            new_payee=True,
            first_large_transfer=True,
            amount_gbp=5000.0,
            recent_device_change=True,
        )
    )
    assert decision.action == "human_review_recommendation"


def test_confirmation_lowers_risk_below_an_unconfirmed_event() -> None:
    signals = {"new_payee": True, "first_large_transfer": True, "amount_gbp": 5000.0}
    confirmed = risk_score(_event(confirmed_transfer=True, **signals))
    unconfirmed = risk_score(_event(**signals))
    assert confirmed < unconfirmed


def test_all_actions_are_supportive() -> None:
    # No combination of signals can produce a blocking/punitive action.
    events = [
        _event(),
        _event(investment_context=True),
        _event(new_payee=True, first_large_transfer=True, amount_gbp=9000.0),
        _event(support_contact_about_scam=True, vulnerable_customer=True),
    ]
    for event in events:
        assert decide_intervention(event).action in SUPPORTIVE_ACTIONS


# --- generator --------------------------------------------------------------


def test_generator_is_deterministic_and_well_formed() -> None:
    config = GeneratorConfig(users=800, months=3, start_date=date(2025, 1, 1), seed=5)
    users = generate_users(config)
    first = generate_protection_events(users, config)
    second = generate_protection_events(users, config)

    assert first.equals(second)
    assert first.height > 0
    assert first.get_column("protection_event_id").n_unique() == first.height
    assert first.get_column("amount_gbp").min() > 0
    # ignored_warning implies the warning was viewed.
    frame = first.to_pandas()
    assert (~frame["ignored_warning"] | frame["viewed_scam_warning"]).all()


# --- dashboard helper -------------------------------------------------------


def test_protection_intervention_summary_counts_actions() -> None:
    from app.dashboard_data import protection_intervention_summary

    events = pd.DataFrame(
        {
            "protection_event_id": ["e1", "e2", "e3"],
            "user_id": ["u1", "u2", "u3"],
            "support_contact_about_scam": [True, False, False],
            "investment_context": [False, True, False],
            "confirmed_transfer": [False, False, True],
        }
    )
    summary = protection_intervention_summary(events).set_index("action")
    assert summary.loc["human_review_recommendation", "events"] == 1
    assert summary.loc["education_prompt", "events"] == 1
    assert summary.loc["no_action", "events"] == 1
    assert abs(summary["share"].sum() - 1.0) < 1e-9


def test_protection_intervention_summary_empty() -> None:
    from app.dashboard_data import protection_intervention_summary

    assert protection_intervention_summary(pd.DataFrame()).empty

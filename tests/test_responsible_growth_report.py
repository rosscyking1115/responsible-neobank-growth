from __future__ import annotations

import pandas as pd
import pytest

from src.release_decisions import ReleaseSignals, decide
from src.reports import (
    build_report,
    render_html,
    render_markdown,
    report_excel_bytes,
    write_excel,
)


def _customer_outcomes(n: int = 40) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "digital_confidence_band": ["low"] * n + ["high"] * n,
            "income_band": ["low"] * n + ["high"] * n,
            "vulnerable_customer_proxy": [True] * n + [False] * n,
            "activated_d7": [False] * n + [True] * n,
            "has_support_contact": [True] * n + [False] * n,
            "has_complaint": [False] * (2 * n),
        }
    )


def _onboarding_funnel(n: int = 40) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "digital_confidence_band": ["low"] * n + ["high"] * n,
            "identity_check_started": [True] * (2 * n),
            "identity_check_passed": [False] * n + [True] * n,
            "card_activated": [False] * n + [True] * n,
            "completed_onboarding": [False] * n + [True] * n,
            "needs_assisted_onboarding": [True] * n + [False] * n,
        }
    )


def _fair_value() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "offer_id": ["clean", "unfair"],
            "fair_value_score": [0.9, 0.2],
            "recommended_action": ["scale", "scale"],
            "governance_action": ["scale", "hold_fair_value"],
            "downgraded": [False, True],
            "reason": ["ok", "fairness"],
        }
    )


def _protection_events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "protection_event_id": ["e1", "e2", "e3"],
            "support_contact_about_scam": [True, False, False],
            "investment_context": [False, True, False],
            "confirmed_transfer": [False, False, True],
        }
    )


def _release_decision():
    return decide(
        ReleaseSignals(
            feature_name="personalised_onboarding",
            business_uplift=0.031,
            evidence_strength=0.9,
        )
    )


def _report():
    return build_report(
        feature_name="personalised_onboarding",
        release_decision=_release_decision(),
        customer_outcomes=_customer_outcomes(),
        onboarding_funnel=_onboarding_funnel(),
        fair_value=_fair_value(),
        protection_events=_protection_events(),
    )


def test_build_report_summarises_all_engines() -> None:
    report = _report()
    s = report.summary
    assert s.release_recommendation == "ship"
    assert s.worst_fairness_gap_pp == pytest.approx(100.0)  # low 0%, high 100% activation
    assert s.assisted_onboarding_customers == 40
    assert s.fair_value_downgrades == 1
    assert s.protection_human_review == 1
    assert 0.0 < s.protection_intervention_rate <= 1.0
    assert s.impact_statements


def test_render_markdown_contains_verdict_and_sections() -> None:
    md = render_markdown(_report())
    assert "Responsible Growth Decision Pack" in md
    assert "SHIP" in md
    assert "Business impact summary" in md
    assert "Customer-protection interventions" in md


def test_render_html_is_self_contained() -> None:
    html = render_html(_report())
    assert html.startswith("<!doctype html>")
    assert "SHIP" in html
    assert "pack-table" in html


def test_excel_export_has_expected_sheets(tmp_path) -> None:
    path = write_excel(_report(), tmp_path / "pack.xlsx")
    assert path.exists()
    sheets = pd.ExcelFile(path).sheet_names
    assert {"Summary", "Fairness gaps", "Fair-value pricing", "Protection"} <= set(sheets)

    blob = report_excel_bytes(_report())
    assert blob[:2] == b"PK"  # xlsx is a zip archive


def test_build_report_handles_empty_inputs() -> None:
    report = build_report(
        feature_name="empty",
        release_decision=None,
        customer_outcomes=pd.DataFrame(),
        onboarding_funnel=pd.DataFrame(),
        fair_value=pd.DataFrame(),
        protection_events=pd.DataFrame(),
    )
    assert report.summary.release_recommendation == "n/a"
    assert report.summary.assisted_onboarding_customers == 0
    # Rendering must not raise on empty frames.
    assert "Responsible Growth Decision Pack" in render_markdown(report)
    assert render_html(report).startswith("<!doctype html>")

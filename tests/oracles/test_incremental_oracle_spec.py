"""Incremental-correctness oracle specification tests (Plan 1, Task 7).

Gate G0.6: the tiny truth fixtures must distinguish full truth from the two
classic incremental failure modes — dropping late events and double-counting
duplicated deliveries. Each test simulates the faulty pipeline behaviour over
the raw fixtures and asserts the truth comparison detects it.
"""

import json
from pathlib import Path

from src.synthetic_truth.oracle import (
    canonical_events,
    classify_deliveries,
    compare_truth,
    compute_observed,
    load_scenario,
)

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = ROOT / "contracts" / "scenarios"
SPEC_DOC = ROOT / "docs" / "contracts" / "incremental-correctness.md"


def _load(scenario_id: str) -> tuple[dict, dict, list[dict]]:
    scenario = load_scenario(SCENARIOS_DIR / f"{scenario_id}.yml")
    with open(ROOT / scenario["truth_fixture"], encoding="utf-8") as f:
        truth = json.load(f)
    with open(ROOT / scenario["events_fixture"], encoding="utf-8") as f:
        deliveries = [json.loads(line) for line in f if line.strip()]
    return scenario, truth, deliveries


def _hours_between(a: str, b: str) -> float:
    from datetime import datetime

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(b, fmt) - datetime.strptime(a, fmt)).total_seconds() / 3600


def test_correct_pipeline_matches_truth() -> None:
    scenario, truth, _ = _load("late-arrival")
    observed = compute_observed(scenario)
    assert compare_truth(truth, observed) == []


def test_oracle_detects_dropped_late_events() -> None:
    """A pipeline that silently drops beyond-threshold arrivals must fail."""
    scenario, truth, deliveries = _load("late-arrival")
    threshold_h = scenario["late_threshold_hours"]
    kept = [
        e for e in deliveries if _hours_between(e["occurred_at"], e["ingested_at"]) <= threshold_h
    ]
    assert len(kept) < len(deliveries), "fixture must contain a late delivery to drop"

    valid, _ = classify_deliveries(kept)
    canonical = canonical_events(valid)
    faulty_observed = compute_observed(scenario)
    faulty_observed = dict(faulty_observed)
    faulty_observed["unique_business_events"] = len(canonical)
    qualified = [e for e in canonical if e["event_name"] == "referral-qualified"]
    faulty_observed["reconciliation"] = dict(faulty_observed["reconciliation"])
    faulty_observed["reconciliation"]["entitled_minor"] = (
        scenario["reward_amount_minor"] * len(qualified)
    )

    mismatches = compare_truth(truth, faulty_observed)
    assert mismatches, "dropping the late qualification must be detected"
    assert any("entitled_minor" in m or "unique_business_events" in m for m in mismatches)


def test_oracle_detects_duplicate_counting() -> None:
    """A pipeline that skips idempotency deduplication must fail."""
    scenario, truth, deliveries = _load("duplicate-delivery")
    valid, _ = classify_deliveries(deliveries)
    qualified_deliveries = [e for e in valid if e["event_name"] == "referral-qualified"]
    assert len(qualified_deliveries) == 2, "fixture must contain a duplicated delivery"

    faulty_observed = compute_observed(scenario)
    faulty_observed = dict(faulty_observed)
    # No dedup: every valid delivery becomes a business event and earns entitlement.
    faulty_observed["unique_business_events"] = len(valid)
    faulty_observed["duplicates"] = 0
    faulty_observed["reconciliation"] = dict(faulty_observed["reconciliation"])
    faulty_observed["reconciliation"]["entitled_minor"] = (
        scenario["reward_amount_minor"] * len(qualified_deliveries)
    )

    mismatches = compare_truth(truth, faulty_observed)
    assert mismatches, "double counting the duplicated qualification must be detected"
    assert any("entitled_minor" in m for m in mismatches), "financial double count must surface"


def test_oracle_detects_missed_freshness_outage() -> None:
    """A health check that reports a stale source as fresh must fail."""
    _, truth, _ = _load("freshness-outage")
    scenario, _, _ = _load("freshness-outage")
    faulty_observed = compute_observed(scenario)
    faulty_observed = dict(faulty_observed)
    faulty_observed["freshness"] = dict(faulty_observed["freshness"])
    faulty_observed["freshness"]["breached"] = False
    faulty_observed["freshness"]["max_gap_hours"] = 1.0
    assert compare_truth(truth, faulty_observed)


def test_incremental_contract_document_locks_required_semantics() -> None:
    text = SPEC_DOC.read_text(encoding="utf-8").lower()
    for marker in [
        "ingested_at",
        "occurred_at",
        "3-day",
        "lookback",
        "2 days 23 hours",
        "3 days 1 hour",
        "idempoten",
        "bounded backfill",
        "blue/green",
        "no tolerance",
    ]:
        assert marker in text, f"incremental contract must lock: {marker}"

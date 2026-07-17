"""Fault-scenario and truth-manifest tests (Plan 2, Task 3).

Every scenario must produce the exact expected defect and truth; changing the
seed changes identifiers and content but never the declared scenario
semantics. Verification uses the independent Plan 1 oracle
(src/synthetic_truth/oracle.py), not the injectors' own bookkeeping.
"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pytest

from src.event_simulator.config import SimulatorConfig, load_config
from src.event_simulator.generator import generate_valid_events
from src.event_simulator.scenarios import apply_faults
from src.synthetic_truth.oracle import canonical_events, classify_deliveries

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT / "config" / "simulator" / "tiny.yml")


def _hours(a: str, b: str) -> float:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return (datetime.strptime(b, fmt) - datetime.strptime(a, fmt)).total_seconds() / 3600


@pytest.fixture(scope="module")
def faulted():
    return apply_faults(generate_valid_events(CONFIG), CONFIG)


def test_manifest_delivery_counts_match_stream(faulted) -> None:
    manifest = faulted.manifest
    assert manifest["delivery_count"] == len(faulted.deliveries)
    by_name_version: dict[str, int] = defaultdict(int)
    for event in faulted.deliveries:
        by_name_version[f"{event['event_name']}:v{event['schema_version']}"] += 1
    assert manifest["deliveries_by_event"] == dict(by_name_version)


def test_duplicates_share_idempotency_and_count_once(faulted) -> None:
    valid, _ = classify_deliveries(faulted.deliveries)
    canonical = canonical_events(valid)
    observed_duplicates = len(valid) - len(canonical)
    assert observed_duplicates == faulted.manifest["expected_duplicates"] > 0
    assert len(canonical) == faulted.manifest["unique_business_events"]


def test_malformed_payloads_quarantine_without_state_mutation(faulted) -> None:
    valid, quarantined = classify_deliveries(faulted.deliveries)
    assert len(quarantined) == faulted.manifest["expected_quarantined"] > 0
    # Quarantined deliveries never contribute canonical business events: every
    # canonical event id is drawn from the valid set only.
    canonical_ids = {e["event_id"] for e in canonical_events(valid)}
    assert canonical_ids.isdisjoint({e["event_id"] for e in quarantined})


def test_late_and_beyond_lookback_arrivals_match_manifest(faulted) -> None:
    threshold_h = CONFIG.late_threshold_hours
    lookback_h = CONFIG.lookback_days * 24
    valid, _ = classify_deliveries(faulted.deliveries)
    late = [e for e in valid if _hours(e["occurred_at"], e["ingested_at"]) > threshold_h]
    beyond = [e for e in late if _hours(e["occurred_at"], e["ingested_at"]) > lookback_h]
    assert len(beyond) == faulted.manifest["expected_beyond_lookback"] > 0
    assert len(late) == faulted.manifest["expected_late_arrivals"] > 0
    assert faulted.manifest["expected_beyond_lookback"] <= faulted.manifest[
        "expected_late_arrivals"
    ]


def test_reversals_reconcile_exactly(faulted) -> None:
    manifest = faulted.manifest
    reversed_events = [
        e for e in faulted.deliveries if e["event_name"] == "reward-reversed"
    ]
    assert len(reversed_events) == manifest["expected_reversals"] > 0
    reversed_minor = sum(e["payload"]["amount_minor"] for e in reversed_events)
    assert reversed_minor == manifest["reconciliation"]["reversed_minor"]
    end_states = manifest["lifecycle_end_states"]
    assert sum(1 for s in end_states.values() if s == "reversed") == len(reversed_events)
    # No reward may be both settled and reversed.
    by_reward: dict[str, set[str]] = defaultdict(set)
    for event in faulted.deliveries:
        reward_id = event["payload"].get("reward_id")
        if reward_id:
            by_reward[reward_id].add(event["event_name"])
    assert not any({"reward-settled", "reward-reversed"} <= names for names in by_reward.values())


def test_reconciliation_breaks_create_missing_postings(faulted) -> None:
    manifest = faulted.manifest
    expected_breaks = CONFIG.scenario_mix.reconciliation_break_count
    exceptions = {e["reason"]: e["count"] for e in manifest["reconciliation"]["exceptions"]}
    assert exceptions.get("missing_posting") == expected_breaks
    # Independently: qualified referrals with no booked reward in the stream.
    valid, _ = classify_deliveries(faulted.deliveries)
    canonical = canonical_events(valid)
    qualified = {
        e["payload"]["referral_id"] for e in canonical if e["event_name"] == "referral-qualified"
    }
    booked = {
        e["payload"]["referral_id"] for e in canonical if e["event_name"] == "reward-booked"
    }
    assert len(qualified - booked) == expected_breaks


def test_ledger_totals_reconcile_with_stream(faulted) -> None:
    rec = faulted.manifest["reconciliation"]
    valid, _ = classify_deliveries(faulted.deliveries)
    canonical = canonical_events(valid)
    booked = sum(
        e["payload"]["amount_minor"] for e in canonical if e["event_name"] == "reward-booked"
    )
    settled = sum(
        e["payload"]["amount_minor"] for e in canonical if e["event_name"] == "reward-settled"
    )
    assert rec["booked_minor"] == booked
    assert rec["settled_minor"] == settled
    assert rec["outstanding_payable_minor"] == (
        rec["booked_minor"] - rec["settled_minor"] - rec["reversed_minor"]
    )


def test_v1_and_v2_coexist(faulted) -> None:
    versions = {
        e["schema_version"]
        for e in faulted.deliveries
        if e["event_name"] == "referral-qualified"
    }
    assert {1, 2} <= versions
    assert faulted.manifest["schema_evolution"]["referral_qualified_v2"] > 0


def test_freshness_outage_creates_declared_gap(faulted) -> None:
    freshness = faulted.manifest["freshness"]
    assert freshness["breached"] is True
    arrivals = sorted(e["ingested_at"] for e in faulted.deliveries)
    max_gap = max(_hours(a, b) for a, b in zip(arrivals, arrivals[1:], strict=False))
    assert max_gap > freshness["threshold_hours"]
    assert abs(max_gap - freshness["max_gap_hours"]) < 0.01


def test_manifest_records_reproducibility_metadata(faulted) -> None:
    manifest = faulted.manifest
    assert manifest["seed"] == CONFIG.seed
    assert manifest["profile"] == "tiny"
    assert manifest["generator_version"] == CONFIG.generator_version
    assert manifest["config_hash"]
    assert "journeys" in manifest["sub_seeds"] and "faults" in manifest["sub_seeds"]
    assert manifest["prohibited_interpretation"]
    assert manifest["limitations"]


def test_seed_change_alters_content_not_semantics(faulted) -> None:
    other_config = SimulatorConfig(**{**CONFIG.as_dict(), "seed": 43})
    other = apply_faults(generate_valid_events(other_config), other_config)
    assert {e["event_id"] for e in other.deliveries} != {
        e["event_id"] for e in faulted.deliveries
    }
    for key in ("expected_quarantined", "expected_beyond_lookback"):
        assert other.manifest[key] > 0, key
    assert other.manifest["expected_duplicates"] > 0
    assert other.manifest["freshness"]["breached"] is True
    exceptions = {e["reason"]: e["count"] for e in other.manifest["reconciliation"]["exceptions"]}
    assert exceptions.get("missing_posting") == CONFIG.scenario_mix.reconciliation_break_count


def test_fault_injection_is_deterministic(faulted) -> None:
    again = apply_faults(generate_valid_events(CONFIG), CONFIG)
    assert [e["event_id"] for e in again.deliveries] == [
        e["event_id"] for e in faulted.deliveries
    ]
    assert again.manifest == faulted.manifest

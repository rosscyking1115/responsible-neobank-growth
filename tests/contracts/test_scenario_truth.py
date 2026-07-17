"""scenario truth tests.

Every scenario manifest must validate against the scenario schema, reference
existing event/truth fixtures, and — critically — its hand-declared truth must
match what the independent oracle recomputes from the raw event fixture.
Altering any event count, duplicate count, ledger balance, lifecycle end state
or exception reason in the truth must fail validation.
"""

import copy
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from src.synthetic_truth.oracle import (
    TruthMismatchError,
    compare_truth,
    compute_observed,
    load_scenario,
    verify_scenario,
)

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = ROOT / "contracts" / "scenarios"

EXPECTED_SCENARIOS = {
    "happy-path",
    "duplicate-delivery",
    "late-arrival",
    "reversal",
    "malformed-quarantine",
    "referral-v1-to-v2",
    "freshness-outage",
    "reconciliation-break",
    "referral-known-truth",
}


def scenario_paths() -> list[Path]:
    return sorted(SCENARIOS_DIR.glob("*.yml"))


def scenario_ids() -> list[str]:
    return [p.stem for p in scenario_paths()]


def test_all_required_scenarios_exist() -> None:
    assert set(scenario_ids()) == EXPECTED_SCENARIOS


def test_scenario_manifests_validate_against_schema() -> None:
    with open(SCENARIOS_DIR / "scenario.schema.json", encoding="utf-8") as f:
        schema = json.load(f)
    for path in scenario_paths():
        with open(path, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
        jsonschema.validate(instance=manifest, schema=schema)
        assert manifest["scenario_id"] == path.stem


def test_scenario_fixture_files_exist() -> None:
    for path in scenario_paths():
        scenario = load_scenario(path)
        assert (ROOT / scenario["events_fixture"]).exists()
        assert (ROOT / scenario["truth_fixture"]).exists()


@pytest.mark.parametrize("scenario_id", sorted(EXPECTED_SCENARIOS))
def test_declared_truth_matches_recomputed_observation(scenario_id: str) -> None:
    verify_scenario(SCENARIOS_DIR / f"{scenario_id}.yml")


# --- mutation tests: tampered truth must fail -------------------------------


def _truth_and_observed(scenario_id: str) -> tuple[dict, dict]:
    scenario = load_scenario(SCENARIOS_DIR / f"{scenario_id}.yml")
    with open(ROOT / scenario["truth_fixture"], encoding="utf-8") as f:
        truth = json.load(f)
    observed = compute_observed(scenario)
    return truth, observed


@pytest.mark.parametrize("scenario_id", sorted(EXPECTED_SCENARIOS))
def test_altered_event_count_fails(scenario_id: str) -> None:
    truth, observed = _truth_and_observed(scenario_id)
    truth = copy.deepcopy(truth)
    truth["event_count"] += 1
    assert compare_truth(truth, observed), "tampered event_count must be detected"


def test_altered_duplicate_count_fails() -> None:
    truth, observed = _truth_and_observed("duplicate-delivery")
    truth = copy.deepcopy(truth)
    truth["duplicates"] += 1
    assert compare_truth(truth, observed)


def test_altered_late_arrival_count_fails() -> None:
    truth, observed = _truth_and_observed("late-arrival")
    truth = copy.deepcopy(truth)
    truth["late_arrivals"] = 0
    assert compare_truth(truth, observed)


def test_altered_quarantine_count_fails() -> None:
    truth, observed = _truth_and_observed("malformed-quarantine")
    truth = copy.deepcopy(truth)
    truth["quarantined"] = 0
    assert compare_truth(truth, observed)


def test_altered_ledger_balance_fails() -> None:
    truth, observed = _truth_and_observed("referral-known-truth")
    truth = copy.deepcopy(truth)
    truth["reconciliation"]["entitled_minor"] += 100
    assert compare_truth(truth, observed)


def test_altered_exception_reason_fails() -> None:
    truth, observed = _truth_and_observed("reconciliation-break")
    truth = copy.deepcopy(truth)
    assert truth["reconciliation"]["exceptions"], "fixture must declare an exception"
    truth["reconciliation"]["exceptions"][0]["reason"] = "duplicate_posting"
    assert compare_truth(truth, observed)


def test_altered_lifecycle_end_state_fails() -> None:
    truth, observed = _truth_and_observed("reversal")
    truth = copy.deepcopy(truth)
    (referral_id,) = [k for k, v in truth["lifecycle_end_states"].items() if v == "reversed"]
    truth["lifecycle_end_states"][referral_id] = "settled"
    assert compare_truth(truth, observed)


def test_altered_freshness_breach_fails() -> None:
    truth, observed = _truth_and_observed("freshness-outage")
    truth = copy.deepcopy(truth)
    truth["freshness"]["breached"] = False
    assert compare_truth(truth, observed)


def test_verify_scenario_raises_on_mismatch(tmp_path: Path) -> None:
    scenario = load_scenario(SCENARIOS_DIR / "happy-path.yml")
    with open(ROOT / scenario["truth_fixture"], encoding="utf-8") as f:
        truth = json.load(f)
    truth["unique_business_events"] += 1
    tampered_truth = tmp_path / "truth.json"
    tampered_truth.write_text(json.dumps(truth), encoding="utf-8")
    tampered = dict(scenario)
    tampered["truth_fixture"] = str(tampered_truth)
    tampered_manifest = tmp_path / "happy-path.yml"
    tampered_manifest.write_text(yaml.safe_dump(tampered), encoding="utf-8")
    with pytest.raises(TruthMismatchError):
        verify_scenario(tampered_manifest)


# --- required hand-built truth case --------------------


def test_known_truth_case_contains_all_mandatory_defects() -> None:
    truth, observed = _truth_and_observed("referral-known-truth")
    assert compare_truth(truth, observed) == []
    assert truth["duplicates"] >= 1, "must include a duplicated delivery"
    assert truth["late_arrivals"] >= 1, "must include a late arrival"
    assert truth["quarantined"] >= 1, "must include a malformed quarantined payload"
    assert "reversed" in truth["lifecycle_end_states"].values(), "must include a reversal"
    reasons = {e["reason"] for e in truth["reconciliation"]["exceptions"]}
    assert "missing_posting" in reasons, "must include an intentionally missing posting"
    assert truth["daily_entitlement_minor"], "must declare exact daily entitlement totals"
    assert truth["daily_booked_minor"], "must declare exact daily ledger totals"

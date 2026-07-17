"""Reward-reconciliation oracle specification tests (Plan 1, Task 7).

Gate G0.6: reconciliation truth must detect incorrect reversal treatment and
missing postings exactly, and the ledger invariants must hold on every tiny
fixture.
"""

import json
from pathlib import Path

from src.synthetic_truth.oracle import compare_truth, compute_observed, load_scenario

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = ROOT / "contracts" / "scenarios"
SPEC_DOC = ROOT / "docs" / "contracts" / "reward-reconciliation.md"


def _load(scenario_id: str) -> tuple[dict, dict]:
    scenario = load_scenario(SCENARIOS_DIR / f"{scenario_id}.yml")
    with open(ROOT / scenario["truth_fixture"], encoding="utf-8") as f:
        truth = json.load(f)
    return scenario, truth


def test_oracle_detects_incorrect_reversal_treatment() -> None:
    """A subledger that books a reversal as a settlement must fail."""
    scenario, truth = _load("reversal")
    faulty = compute_observed(scenario)
    faulty = dict(faulty)
    faulty["reconciliation"] = dict(faulty["reconciliation"])
    # Faulty treatment: the reversal amount lands in settled, reversals report zero.
    faulty["reconciliation"]["settled_minor"] += faulty["reconciliation"]["reversed_minor"]
    faulty["reconciliation"]["reversed_minor"] = 0
    faulty["lifecycle_end_states"] = {"ref_000030": "settled"}

    mismatches = compare_truth(truth, faulty)
    assert mismatches, "reversal booked as settlement must be detected"
    assert any("settled_minor" in m for m in mismatches)
    assert any("lifecycle_end_states" in m for m in mismatches)


def test_oracle_detects_missing_posting() -> None:
    """A reconciliation that fails to raise the missing_posting exception must fail."""
    scenario, truth = _load("reconciliation-break")
    faulty = compute_observed(scenario)
    faulty = dict(faulty)
    faulty["reconciliation"] = dict(faulty["reconciliation"])
    faulty["reconciliation"]["exceptions"] = []  # silently ignores the break

    mismatches = compare_truth(truth, faulty)
    assert mismatches, "an ignored missing posting must be detected"
    assert any("exceptions" in m for m in mismatches)


def test_known_truth_ledger_invariants_hold() -> None:
    """Outstanding payable must equal booked minus settled minus reversed."""
    for scenario_id in [
        "happy-path",
        "duplicate-delivery",
        "late-arrival",
        "reversal",
        "referral-v1-to-v2",
        "reconciliation-break",
        "referral-known-truth",
    ]:
        scenario, truth = _load(scenario_id)
        rec = truth["reconciliation"]
        assert rec["outstanding_payable_minor"] == (
            rec["booked_minor"] - rec["settled_minor"] - rec["reversed_minor"]
        ), f"{scenario_id}: payable balance invariant broken in declared truth"
        observed = compute_observed(scenario)
        assert compare_truth(truth, observed) == [], f"{scenario_id}: truth must reconcile"


def test_daily_totals_reconcile_to_overall_totals() -> None:
    _, truth = _load("referral-known-truth")
    assert sum(truth["daily_entitlement_minor"].values()) == (
        truth["reconciliation"]["entitled_minor"]
    )
    assert sum(truth["daily_booked_minor"].values()) == truth["reconciliation"]["booked_minor"]


def test_reconciliation_contract_document_locks_required_semantics() -> None:
    text = SPEC_DOC.read_text(encoding="utf-8").lower()
    for marker in [
        "invited",
        "qualified",
        "booked",
        "settled",
        "reversed",
        "referral_reward_expense",
        "referral_reward_payable",
        "reward_cash_clearing",
        "debit",
        "credit",
        "missing_posting",
        "duplicate_posting",
        "amount_mismatch",
        "not a claim about",
    ]:
        assert marker in text, f"reconciliation contract must lock: {marker}"

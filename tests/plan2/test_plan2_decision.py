"""Plan 2 acceptance evidence validator (Plan 2, Task 12).

The decision record fails validation when any mandatory gate result is
missing, a gate passes without an evidence path, a referenced repo artifact
does not exist, or the decision is inconsistent with the gate results.
"""

import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "artifacts" / "plan2" / "verification-results.json"
SUMMARY = ROOT / "artifacts" / "plan2" / "verification-summary.md"
DECISION_ADR = ROOT / "docs" / "adr" / "ADR-route-c-plan2-decision.md"

MANDATORY_GATES = [f"P2.{i}" for i in range(1, 10)]
ALLOWED_DECISIONS = {"go-to-plan-3", "revise", "route-b-fallback"}

pytestmark = pytest.mark.skipif(
    not RESULTS.exists(),
    reason="requires the Plan 2 decision record (written at the end of Task 12)",
)


def validate(results: dict) -> list[str]:
    errors: list[str] = []
    if results.get("decision") not in ALLOWED_DECISIONS:
        errors.append(f"decision must be one of {sorted(ALLOWED_DECISIONS)}")
    gates = results.get("gates", {})
    for gate_id in MANDATORY_GATES:
        if gate_id not in gates:
            errors.append(f"{gate_id}: mandatory gate result missing")
            continue
        gate = gates[gate_id]
        if gate.get("result") not in {"pass", "fail"}:
            errors.append(f"{gate_id}: result must be pass or fail")
        if not gate.get("items"):
            errors.append(f"{gate_id}: must record evaluated items")
        for item in gate.get("items", []):
            if item.get("result") == "pass" and not str(item.get("evidence", "")).strip():
                errors.append(f"{gate_id}: item passed without an evidence path")
    if results.get("decision") == "go-to-plan-3":
        failing = [g for g in MANDATORY_GATES if gates.get(g, {}).get("result") != "pass"]
        if failing:
            errors.append(f"decision is go-to-plan-3 but gates fail: {failing}")
    return errors


def load_results() -> dict:
    with open(RESULTS, encoding="utf-8") as f:
        return json.load(f)


def test_results_exist_and_validate() -> None:
    assert validate(load_results()) == []


def test_referenced_repo_evidence_paths_exist() -> None:
    for gate in load_results()["gates"].values():
        for item in gate["items"]:
            for evidence in str(item["evidence"]).split(";"):
                evidence = evidence.strip()
                if "/" in evidence and " " not in evidence:
                    assert (ROOT / evidence).exists(), f"missing evidence: {evidence}"


def test_missing_gate_fails_validator() -> None:
    results = copy.deepcopy(load_results())
    del results["gates"]["P2.4"]
    assert any("P2.4" in e for e in validate(results))


def test_pass_without_evidence_fails_validator() -> None:
    results = copy.deepcopy(load_results())
    results["gates"]["P2.1"]["items"][0]["evidence"] = ""
    assert any("without an evidence" in e for e in validate(results))


def test_blue_green_parity_artifact_backs_the_incremental_gate() -> None:
    with open(ROOT / "artifacts" / "plan2" / "blue-green-report.json", encoding="utf-8") as f:
        report = json.load(f)
    assert report["parity"] is True
    assert report["replay_idempotent"] is True
    assert report["pre_backfill_miss_demonstrated"] is True


def test_summary_and_adr_record_one_allowed_outcome() -> None:
    results = load_results()
    summary = SUMMARY.read_text(encoding="utf-8").lower()
    adr = DECISION_ADR.read_text(encoding="utf-8").lower()
    assert results["decision"] in summary
    assert results["decision"] in adr
    assert "user" in adr and "accept" in adr, "ADR must state Plan 3 waits for user acceptance"


def test_no_unauthorised_claims_in_summary() -> None:
    summary = SUMMARY.read_text(encoding="utf-8").lower()
    for forbidden in ["cheaper", "faster than", "% cost", "looker experience", "production scale"]:
        assert forbidden not in summary, f"summary must not claim: {forbidden}"


def test_open_items_are_recorded() -> None:
    results = load_results()
    assert results.get("open_items"), "known deferrals must be recorded, not hidden"


@pytest.mark.parametrize("gate_id", MANDATORY_GATES)
def test_every_gate_cites_at_least_two_evidence_items(gate_id: str) -> None:
    gate = load_results()["gates"][gate_id]
    assert len(gate["items"]) >= 2, f"{gate_id}: gates need substantive evidence"

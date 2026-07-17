"""Gate 0 decision evaluator (Plan 1, Task 10).

The evaluator fails when any mandatory gate result is missing, when a gate is
marked passed without an evidence path, or when the decision is inconsistent
with the gate results.
"""

import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "artifacts" / "gate0" / "route-c-gate0-results.json"
REPORT = ROOT / "artifacts" / "gate0" / "route-c-gate0-report.md"
DECISION_ADR = ROOT / "docs" / "adr" / "ADR-route-c-gate0-decision.md"
BUDGET_RUNBOOK = ROOT / "docs" / "runbooks" / "bigquery-budget-and-cleanup.md"

MANDATORY_GATES = [f"G0.{i}" for i in range(1, 9)]
ALLOWED_DECISIONS = {"go", "revise", "fallback-to-route-b", "stop"}


def validate_results(results: dict) -> list[str]:
    """Return one error per evaluator rule violation."""
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
        items = gate.get("items", [])
        if not items:
            errors.append(f"{gate_id}: must record at least one evaluated item")
        for item in items:
            if item.get("result") not in {"pass", "fail"}:
                errors.append(f"{gate_id}: item result must be pass or fail")
            if item.get("result") == "pass" and not str(item.get("evidence", "")).strip():
                errors.append(
                    f"{gate_id}: item {item.get('item', '?')!r} passed without an evidence path"
                )
        if gate.get("result") == "pass" and any(i.get("result") == "fail" for i in items):
            errors.append(f"{gate_id}: gate passes while an item fails")
    if results.get("decision") == "go":
        failing = [g for g in MANDATORY_GATES if gates.get(g, {}).get("result") != "pass"]
        if failing:
            errors.append(f"decision is go but gates fail: {failing}")
    return errors


def load_results() -> dict:
    with open(RESULTS, encoding="utf-8") as f:
        return json.load(f)


def test_gate0_results_exist_and_validate() -> None:
    assert validate_results(load_results()) == []


def test_every_referenced_repo_evidence_path_exists() -> None:
    results = load_results()
    for gate in results["gates"].values():
        for item in gate["items"]:
            for evidence in str(item["evidence"]).split(";"):
                evidence = evidence.strip()
                if "/" in evidence and " " not in evidence:
                    assert (ROOT / evidence).exists(), f"evidence path missing: {evidence}"


def test_missing_gate_fails_validator() -> None:
    results = copy.deepcopy(load_results())
    del results["gates"]["G0.3"]
    assert any("G0.3" in e for e in validate_results(results))


def test_pass_without_evidence_fails_validator() -> None:
    results = copy.deepcopy(load_results())
    results["gates"]["G0.1"]["items"][0]["evidence"] = ""
    assert any("without an evidence path" in e for e in validate_results(results))


def test_go_with_failing_gate_fails_validator() -> None:
    results = copy.deepcopy(load_results())
    results["gates"]["G0.8"]["result"] = "fail"
    for item in results["gates"]["G0.8"]["items"]:
        item["result"] = "fail"
    if results["decision"] == "go":
        assert any("decision is go" in e for e in validate_results(results))
    else:
        pytest.skip("decision is not go; consistency rule not applicable")


def test_report_and_adr_record_one_allowed_outcome() -> None:
    results = load_results()
    report = REPORT.read_text(encoding="utf-8").lower()
    adr = DECISION_ADR.read_text(encoding="utf-8").lower()
    assert results["decision"] in report
    assert results["decision"] in adr
    assert "user" in adr and "accept" in adr, (
        "ADR must state that Plan 2 waits for user acceptance"
    )


def test_budget_runbook_locks_cost_controls_without_false_claims() -> None:
    text = BUDGET_RUNBOOK.read_text(encoding="utf-8").lower()
    for marker in [
        "maximum_bytes_billed",
        "1 gb",
        "quota",
        "dry run",
        "information_schema.jobs",
        "expiry",
        "cleanup",
        "alerts are not hard caps",
        "explicit user acceptance",
    ]:
        assert marker in text, f"budget runbook must cover: {marker}"
    assert "alerts prevent spend" not in text

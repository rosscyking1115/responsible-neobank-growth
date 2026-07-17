"""Looker readiness tests (Plan 1, Task 9).

Gate G0.7: readiness fails if an Explore lacks its consumer question, source
interface, primary key, expected join relationship, headline measures, fixture
answers or validation/capture step. No Looker instance is activated and no
Looker experience is claimed in Plan 1.
"""

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LOOKER_README = ROOT / "looker" / "README.md"
FIELD_INVENTORY = ROOT / "docs" / "looker" / "explore-field-inventory.csv"
TRIAL_RUNBOOK = ROOT / "docs" / "looker" / "trial-runbook.md"
EVIDENCE_CHECKLIST = ROOT / "docs" / "looker" / "evidence-checklist.md"

EXPLORES = {
    "growth_acquisition",
    "referral_economics",
    "reward_reconciliation",
    "warehouse_health",
}

INVENTORY_COLUMNS = [
    "explore",
    "field_name",
    "field_type",
    "source_interface",
    "source_column",
    "description",
    "is_headline",
]


def load_inventory() -> list[dict]:
    with open(FIELD_INVENTORY, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == INVENTORY_COLUMNS
        return list(reader)


def test_all_explores_are_inventoried() -> None:
    assert {row["explore"] for row in load_inventory()} == EXPLORES


def test_every_explore_declares_a_primary_key() -> None:
    rows = load_inventory()
    for explore in EXPLORES:
        pks = [
            r for r in rows if r["explore"] == explore and r["field_type"] == "dimension_pk"
        ]
        assert pks, f"{explore}: must declare at least one primary-key dimension"


def test_every_explore_declares_headline_measures() -> None:
    rows = load_inventory()
    for explore in EXPLORES:
        headline = [
            r
            for r in rows
            if r["explore"] == explore
            and r["field_type"] == "measure"
            and r["is_headline"] == "yes"
        ]
        assert len(headline) >= 2, f"{explore}: needs at least two headline measures"


def test_every_field_maps_to_a_governed_interface_column() -> None:
    for row in load_inventory():
        assert row["source_interface"] in EXPLORES, row["field_name"]
        assert row["source_column"].strip(), row["field_name"]
        assert row["description"].strip(), row["field_name"]


@pytest.mark.parametrize("explore", sorted(EXPLORES))
def test_readme_states_question_source_and_join_for_each_explore(explore: str) -> None:
    text = LOOKER_README.read_text(encoding="utf-8").lower()
    assert explore in text
    for marker in [f"{explore} question", f"{explore} primary key", f"{explore} join"]:
        assert marker.lower() in text, f"looker/README.md must state: {marker}"


def test_readme_claims_no_looker_experience() -> None:
    text = LOOKER_README.read_text(encoding="utf-8").lower()
    assert "not been executed" in text or "no looker instance" in text, (
        "README must state that no Looker validation has happened yet"
    )


def test_trial_runbook_covers_connection_validation_and_cleanup() -> None:
    text = TRIAL_RUNBOOK.read_text(encoding="utf-8").lower()
    for marker in [
        "bigquery connection",
        "git",
        "lookml validat",
        "sql validat",
        "assert validat",
        "content validat",
        "trial expiry",
        "cleanup",
        "no-cost",
    ]:
        assert marker in text, f"trial runbook must cover: {marker}"


def test_evidence_checklist_covers_capture_and_fixture_answers() -> None:
    text = EVIDENCE_CHECKLIST.read_text(encoding="utf-8").lower()
    for marker in [
        "validator output",
        "screenshot",
        "walkthrough",
        "expected-versus-actual",
        "fixture answer",
        "no credential",
    ]:
        assert marker in text, f"evidence checklist must cover: {marker}"
    for explore in EXPLORES:
        assert explore in text, f"evidence checklist must record fixture answers for {explore}"

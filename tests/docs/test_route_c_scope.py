"""Route C scope and architecture decisions must exist and carry the locked boundaries.

These tests enforce Plan 1 Task 2: the approved identity, stakeholder question,
layer contract, Finance boundary, synthetic claim boundary and explicit
exclusions are recorded before any Route C implementation work.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SCOPE_DOC = ROOT / "docs" / "architecture" / "route-c-product-scope.md"

ADR_DOCS = {
    "event-boundary": ROOT / "docs" / "adr" / "ADR-route-c-event-boundary.md",
    "four-layer-interfaces": ROOT / "docs" / "adr" / "ADR-route-c-four-layer-interfaces.md",
    "dbt-looker-boundary": ROOT / "docs" / "adr" / "ADR-route-c-dbt-looker-boundary.md",
    "synthetic-truth": ROOT / "docs" / "adr" / "ADR-route-c-synthetic-truth.md",
}

# Disclaimers that must appear in the scope document (lowercase substring match).
REQUIRED_DISCLAIMERS = [
    "not a monzo simulation",
    "no affiliation",
    "synthetic",
    "not a production banking system",
    "not evidence of work with real bank customers",
]

# Forbidden-scope markers: the scope document must explicitly exclude these.
REQUIRED_EXCLUSIONS = [
    "fraud",
    "aml",
    "credit scoring",
    "lending",
    "general ledger",
    "kafka",
    "streaming",
    "real-time",
]

# Locked scope anchors that must be stated.
REQUIRED_SCOPE_ANCHORS = [
    "referral-reward",  # Finance boundary
    "primary stakeholder question",
    "landing",
    "normalised",
    "logical",
    "presentation",
]


def _read_lower(path: Path) -> str:
    assert path.exists(), f"missing required Route C document: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8").lower()


def test_scope_document_exists_with_required_disclaimers() -> None:
    text = _read_lower(SCOPE_DOC)
    missing = [marker for marker in REQUIRED_DISCLAIMERS if marker not in text]
    assert missing == [], f"scope document is missing required disclaimers: {missing}"


def test_scope_document_declares_explicit_exclusions() -> None:
    text = _read_lower(SCOPE_DOC)
    missing = [marker for marker in REQUIRED_EXCLUSIONS if marker not in text]
    assert missing == [], f"scope document is missing forbidden-scope markers: {missing}"


def test_scope_document_states_locked_scope_anchors() -> None:
    text = _read_lower(SCOPE_DOC)
    missing = [marker for marker in REQUIRED_SCOPE_ANCHORS if marker not in text]
    assert missing == [], f"scope document is missing locked-scope anchors: {missing}"


@pytest.mark.parametrize("name", sorted(ADR_DOCS))
def test_adr_exists_and_is_accepted(name: str) -> None:
    text = _read_lower(ADR_DOCS[name])
    assert "## status" in text, f"ADR {name} must have a Status section"
    assert "accepted" in text, f"ADR {name} must record an accepted status"
    assert "## decision" in text, f"ADR {name} must have a Decision section"
    assert "## consequences" in text, f"ADR {name} must have a Consequences section"


def test_event_boundary_adr_locks_the_envelope() -> None:
    text = _read_lower(ADR_DOCS["event-boundary"])
    for marker in ["idempotency_key", "occurred_at", "emitted_at", "ingested_at", "schema_version"]:
        assert marker in text, f"event-boundary ADR must lock envelope field: {marker}"


def test_four_layer_adr_locks_prefixes() -> None:
    text = _read_lower(ADR_DOCS["four-layer-interfaces"])
    for marker in ["lnd_", "nrm_", "lgl_", "prs_", "compatibility"]:
        assert marker in text, f"four-layer ADR must lock naming/compatibility marker: {marker}"


def test_dbt_looker_adr_locks_metric_ownership() -> None:
    text = _read_lower(ADR_DOCS["dbt-looker-boundary"])
    for marker in ["one authoritative", "lookml", "may not reimplement"]:
        assert marker in text, f"dbt/looker ADR must lock ownership marker: {marker}"


def test_synthetic_truth_adr_separates_claim_levels() -> None:
    text = _read_lower(ADR_DOCS["synthetic-truth"])
    for marker in ["engineering truth", "analytical method validation", "illustrative"]:
        assert marker in text, f"synthetic-truth ADR must separate claim level: {marker}"

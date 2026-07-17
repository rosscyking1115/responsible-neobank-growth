"""Public-claim audit tests (Plan 4, Task 3).

The audit must pass on the repository's public surfaces, and a seeded
unsupported claim must be detected.
"""

from tools.release.claim_audit import audit_text, load_registry_text, run_audit


def test_public_surfaces_carry_no_unsupported_claims() -> None:
    findings = run_audit()
    assert findings == [], "unsupported public claims:\n" + "\n".join(findings)


def test_seeded_forbidden_phrase_is_detected() -> None:
    registry_text = load_registry_text()
    findings = audit_text(
        "seeded.md",
        "This project demonstrates real Looker experience at production scale.",
        registry_text,
    )
    assert any("looker experience" in f for f in findings)
    assert any("production" in f for f in findings)


def test_seeded_unanchored_number_is_detected() -> None:
    findings = audit_text(
        "seeded.md",
        "The benchmark processed 32.99 TB of data.",
        registry_text="",  # empty registry: nothing is anchored
    )
    assert any("32.99" in f for f in findings)


def test_seeded_looker_validation_wording_is_detected() -> None:
    registry_text = load_registry_text()
    findings = audit_text(
        "seeded.md",
        "The dashboards were validated in our Looker deployment.",
        registry_text,
    )
    assert findings, "unqualified 'validated' near 'looker' must be flagged"

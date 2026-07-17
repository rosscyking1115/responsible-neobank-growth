"""Public-claim audit (Plan 4, Task 3).

Scans the public surfaces (README, docs, looker/README) for wording the
release branch forbids and for tracked numbers that must be anchored in the
evidence registry. The audit fails when a forbidden phrase appears or a
tracked number is used on a public surface without a registry claim carrying
it.

Usage: python -m tools.release.claim_audit
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PUBLIC_SURFACES = [
    "README.md",
    "looker/README.md",
    *[str(p.relative_to(ROOT)) for p in (ROOT / "docs").rglob("*.md")],
]

# Forbidden on the bigquery-only branch (ADR-route-c-release-branch).
FORBIDDEN_PHRASES = [
    "looker experience",
    "validated lookml",
    "validated in looker",
    "production scale",
    "production-scale",
    "cheaper like monzo",
    "60% cheaper",
    "real customers were",
    "monzo uses this",
]

# Numbers that may only appear on public surfaces if the registry anchors them.
TRACKED_NUMBERS = [
    "568,789", "568789", "560,360", "5,600 dupl", "2,829",
    "+1.95%", "1.95%", "62.7%", "64.7%", "523.9",
    "844 ", "32.99",
]


def load_registry_text() -> str:
    registry = (ROOT / "evidence" / "registry.yml").read_text(encoding="utf-8")
    return registry.lower()


NEGATION_TOKENS = [
    "no ", "not ", "never", "forbid", "without", "gap", "unvalidated",
    "cannot", "until", "would", "prohibit",
]


def _negated(window: str) -> bool:
    return any(token in window for token in NEGATION_TOKENS)


def audit_text(surface: str, text: str, registry_text: str) -> list[str]:
    findings: list[str] = []
    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        for match in re.finditer(re.escape(phrase), lowered):
            window = lowered[max(0, match.start() - 120): match.end() + 60]
            if not _negated(window):
                findings.append(
                    f"{surface}: forbidden phrase for this release branch: {phrase!r}"
                )
    for number in TRACKED_NUMBERS:
        if number.lower() in lowered and number.lower() not in registry_text:
            findings.append(
                f"{surface}: tracked number {number!r} is not anchored in the evidence registry"
            )
    # An affirmative 'validated' near 'looker' needs an explicit negation.
    for match in re.finditer(r"\bvalidated\b", lowered):
        window = lowered[max(0, match.start() - 120): match.end() + 80]
        if "looker" in window and not _negated(window):
            findings.append(
                f"{surface}: 'validated' near 'looker' without negation — check wording"
            )
    return findings


def run_audit() -> list[str]:
    registry_text = load_registry_text()
    findings: list[str] = []
    for surface in PUBLIC_SURFACES:
        path = ROOT / surface
        if not path.exists():
            continue
        findings.extend(audit_text(surface, path.read_text(encoding="utf-8"), registry_text))
    return findings


def main() -> int:
    findings = run_audit()
    for finding in findings:
        print(finding, file=sys.stderr)
    print(f"claim audit: {len(findings)} finding(s) across {len(PUBLIC_SURFACES)} surfaces")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

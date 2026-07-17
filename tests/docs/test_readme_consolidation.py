"""README and architecture consolidation tests (Plan 4, Task 4).

Fail for broken local links, an unresolved deployment contradiction, forbidden
release-branch terminology, or missing synthetic/no-affiliation boundaries.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
ADR_INDEX = ROOT / "docs" / "adr" / "README.md"


def _local_markdown_links(text: str) -> list[str]:
    links = []
    for match in re.finditer(r"\]\(([^)]+)\)", text):
        target = match.group(1).split("#")[0].strip()
        if target and not target.startswith(("http://", "https://", "mailto:")):
            links.append(target)
    return links


def test_readme_local_links_resolve() -> None:
    text = README.read_text(encoding="utf-8")
    missing = [t for t in _local_markdown_links(text) if not (ROOT / t).exists()]
    assert missing == [], f"README has broken local links: {missing}"


def test_adr_index_local_links_resolve() -> None:
    text = ADR_INDEX.read_text(encoding="utf-8")
    base = ADR_INDEX.parent
    missing = [t for t in _local_markdown_links(text) if not (base / t).exists()]
    assert missing == [], f"ADR index has broken local links: {missing}"


def test_readme_leads_with_analytics_engineering_identity() -> None:
    head = "\n".join(README.read_text(encoding="utf-8").splitlines()[:40]).lower()
    assert "analytics engineering" in head
    assert "event" in head and "interface" in head


def test_readme_states_synthetic_and_no_affiliation() -> None:
    text = README.read_text(encoding="utf-8").lower()
    assert "synthetic" in text
    assert "no affiliation" in text or "not affiliated" in text
    assert "monzo" in text  # framing must name the influence and disclaim it


def test_readme_uses_only_bigquery_only_branch_wording() -> None:
    text = README.read_text(encoding="utf-8").lower()
    for forbidden in ["looker experience", "validated lookml", "production scale"]:
        # allow only where explicitly negated
        for match in re.finditer(re.escape(forbidden), text):
            window = text[max(0, match.start() - 120): match.end() + 40]
            assert any(n in window for n in ["no ", "not ", "never", "without", "gap"]), (
                f"README uses forbidden phrase without negation: {forbidden!r}"
            )


def test_readme_terminology_is_accurate() -> None:
    text = README.read_text(encoding="utf-8").lower()
    # dbt marts/interfaces, not a Semantic Layer we did not build
    assert "semantic layer" not in text or "lookml semantic layer" in text


def test_scheduled_jobs_contradiction_is_resolved() -> None:
    warehouse = (ROOT / "docs" / "GCP_WAREHOUSE.md").read_text(encoding="utf-8").lower()
    # The stale blanket "not yet been deployed" claim for scheduled jobs must be
    # reconciled, not left standing.
    assert "smoke test" in warehouse and "2026-05-31" in warehouse
    assert "dated history" in warehouse


def test_readme_has_verified_results_table_linking_evidence() -> None:
    text = README.read_text(encoding="utf-8")
    assert "evidence/registry.yml" in text, "README must link the evidence registry"
    assert "artifacts/plan3" in text, "README must link BigQuery benchmark evidence"

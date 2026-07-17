"""Standards enforcement against the real dbt manifest.

Every governed model in the actual project must satisfy the interface
standards; a violation here fails CI, not just the fixtures. Requires a parsed
dbt project; skips with instructions otherwise.
"""

import json
from pathlib import Path

import pytest

from tools.standards.check_dbt_interfaces import check_manifest, load_rules

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "dbt_neobank" / "target" / "manifest.json"
RULES = ROOT / "tools" / "standards" / "rules.yml"

pytestmark = pytest.mark.skipif(
    not MANIFEST.exists(),
    reason="requires a parsed dbt project: uv run dbt parse --project-dir dbt_neobank "
    "--profiles-dir dbt_neobank --target dev",
)


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def test_real_manifest_has_governed_models(manifest) -> None:
    governed = [
        node["name"]
        for node in manifest["nodes"].values()
        if node.get("resource_type") == "model"
        and node["name"].startswith(("nrm_", "lgl_"))
    ]
    assert len(governed) >= 16, f"expected the governed models, got {len(governed)}"


def test_every_governed_model_satisfies_the_standards(manifest) -> None:
    violations = check_manifest(manifest, load_rules(RULES))
    formatted = [f"{v['rule']}: {v['message']}" for v in violations]
    assert violations == [], "standards violations in the real manifest:\n" + "\n".join(formatted)


def test_seeded_violation_is_detected_in_real_manifest(manifest) -> None:
    """Removing one owner from a real governed node must produce exactly that
    violation — the checker sees the real manifest, not just fixtures."""
    import copy

    broken = copy.deepcopy(manifest)
    target_node = next(
        node
        for node in broken["nodes"].values()
        if node.get("resource_type") == "model" and node["name"] == "lgl_growth_acquisition"
    )
    target_node.get("config", {}).get("meta", {}).pop("owner", None)
    target_node.get("meta", {}).pop("owner", None)
    violations = check_manifest(broken, load_rules(RULES))
    assert [v["rule"] for v in violations] == ["owner"]
    assert violations[0]["model"] == "lgl_growth_acquisition"

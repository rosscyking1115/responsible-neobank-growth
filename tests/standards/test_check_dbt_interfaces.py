"""Standards-as-code prototype tests.

Gate G0.5: standards violations must be mechanically detectable. Every invalid
manifest fixture fails for exactly one expected rule; the valid fixture passes.
The prototype inspects dbt-artifact-shaped JSON; the ingestion layer expands it to the real
manifest.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.standards.check_dbt_interfaces import check_manifest, load_rules

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "standards" / "fixtures"
RULES = ROOT / "tools" / "standards" / "rules.yml"

INVALID_FIXTURES = {
    "missing_owner.json": "owner",
    "missing_unique_key.json": "unique_key",
    "missing_freshness.json": "freshness_slo",
    "non_incremental_without_exception.json": "incremental_materialization",
    "missing_partition_policy.json": "partition_policy",
}


def run_check(manifest_name: str) -> list[dict]:
    with open(FIXTURES / manifest_name, encoding="utf-8") as f:
        manifest = json.load(f)
    return check_manifest(manifest, load_rules(RULES))


def test_valid_manifest_passes() -> None:
    assert run_check("valid_manifest.json") == []


@pytest.mark.parametrize(("fixture", "expected_rule"), sorted(INVALID_FIXTURES.items()))
def test_invalid_fixture_fails_for_exactly_one_reason(fixture: str, expected_rule: str) -> None:
    violations = run_check(fixture)
    assert len(violations) == 1, (
        f"{fixture}: expected exactly one violation, got "
        f"{[v['rule'] for v in violations]}"
    )
    assert violations[0]["rule"] == expected_rule
    assert violations[0]["model"], "violation must identify the model"
    assert violations[0]["message"], "violation must carry a human-readable message"


def test_non_governed_models_are_ignored() -> None:
    """Staging/presentation helper models are not held to interface standards."""
    with open(FIXTURES / "valid_manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    assert any(
        node["name"].startswith("stg_") for node in manifest["nodes"].values()
    ), "fixture must include a non-governed model to prove scoping"
    assert run_check("valid_manifest.json") == []


def test_incremental_exemption_is_honoured() -> None:
    """A documented exemption makes non-incremental materialisation acceptable."""
    with open(FIXTURES / "valid_manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    governed = [
        n for n in manifest["nodes"].values() if n["name"].startswith(("nrm_", "lgl_"))
    ]
    assert any(
        n["config"]["materialized"] != "incremental"
        and n["config"]["meta"].get("incremental_exemption")
        for n in governed
    ), "valid fixture must include an exempted non-incremental governed model"


def test_cli_exit_codes_and_json_output(tmp_path: Path) -> None:
    json_out = tmp_path / "report.json"
    ok = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.standards.check_dbt_interfaces",
            "--manifest",
            str(FIXTURES / "valid_manifest.json"),
            "--rules",
            str(RULES),
            "--json-output",
            str(json_out),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert json.loads(json_out.read_text(encoding="utf-8"))["violations"] == []

    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.standards.check_dbt_interfaces",
            "--manifest",
            str(FIXTURES / "missing_owner.json"),
            "--rules",
            str(RULES),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert bad.returncode == 1
    assert "owner" in bad.stdout

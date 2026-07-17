"""Governed interface contract tests (Plan 1, Task 6).

Gate G0.5: the four interface manifests must validate against the interface
schema; a manifest missing owner, grain, unique key, freshness, classification,
compatibility, tests or exposures must fail; and every headline metric must
have exactly one authoritative owner and persisted grain.
"""

import copy
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
INTERFACES_DIR = ROOT / "contracts" / "interfaces"
METRICS_FILE = ROOT / "docs" / "metrics" / "metric-ownership.yml"

EXPECTED_INTERFACES = {
    "growth_acquisition",
    "referral_economics",
    "reward_reconciliation",
    "warehouse_health",
}

# Plan 1 section 7.1 ownership assignments.
EXPECTED_OWNERS = {
    "growth_acquisition": "growth",
    "referral_economics": "growth",
    "reward_reconciliation": "finance",
    "warehouse_health": "platform",
}

REQUIRED_FIELDS = [
    "owner",
    "grain",
    "unique_key",
    "freshness_slo",
    "classification",
    "compatibility",
    "tests",
    "exposures",
]


def interface_schema() -> dict:
    with open(INTERFACES_DIR / "interface.schema.json", encoding="utf-8") as f:
        return json.load(f)


def load_interfaces() -> dict[str, dict]:
    manifests = {}
    for path in sorted(INTERFACES_DIR.glob("*.yml")):
        with open(path, encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
        manifests[manifest["name"]] = manifest
    return manifests


def load_metrics() -> list[dict]:
    with open(METRICS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)["metrics"]


def test_all_four_interfaces_exist() -> None:
    assert set(load_interfaces()) == EXPECTED_INTERFACES


def test_interface_manifests_validate() -> None:
    schema = interface_schema()
    for name, manifest in load_interfaces().items():
        jsonschema.validate(instance=manifest, schema=schema)
        assert manifest["owner"] == EXPECTED_OWNERS[name], (
            f"{name}: owner must follow Plan 1 section 7.1"
        )


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_manifest_missing_required_field_fails(field: str) -> None:
    schema = interface_schema()
    for manifest in load_interfaces().values():
        broken = copy.deepcopy(manifest)
        del broken[field]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=broken, schema=schema)


def test_manifest_with_empty_tests_or_exposures_fails() -> None:
    schema = interface_schema()
    manifest = copy.deepcopy(load_interfaces()["growth_acquisition"])
    manifest["tests"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=manifest, schema=schema)
    manifest = copy.deepcopy(load_interfaces()["growth_acquisition"])
    manifest["exposures"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=manifest, schema=schema)


def test_freshness_slo_declares_warn_and_error() -> None:
    for name, manifest in load_interfaces().items():
        slo = manifest["freshness_slo"]
        assert "warn_after" in slo and "error_after" in slo, name


def test_partition_policy_declared_or_explicitly_not_applicable() -> None:
    for name, manifest in load_interfaces().items():
        assert manifest["partition_policy"], name


def test_classification_is_synthetic() -> None:
    for name, manifest in load_interfaces().items():
        assert manifest["classification"] == "synthetic_restricted", name


# --- metric ownership --------------------------------------------------------


def test_every_metric_has_exactly_one_authoritative_owner() -> None:
    metrics = load_metrics()
    names = [m["name"] for m in metrics]
    duplicated = {n for n in names if names.count(n) > 1}
    assert not duplicated, f"metrics with more than one authoritative owner: {duplicated}"


def test_metric_owners_and_interfaces_are_valid() -> None:
    interfaces = load_interfaces()
    for metric in load_metrics():
        assert metric["owner"] in {"growth", "finance", "platform"}, metric["name"]
        assert metric["authoritative_interface"] in interfaces, (
            f"{metric['name']}: authoritative interface must be one of the four governed"
            " interfaces"
        )
        assert metric["authoritative_grain"], metric["name"]
        assert metric["definition"], metric["name"]


def test_duplicated_metric_owner_fixture_fails() -> None:
    metrics = load_metrics()
    tampered = metrics + [dict(metrics[0], owner="platform")]
    names = [m["name"] for m in tampered]
    duplicated = {n for n in names if names.count(n) > 1}
    assert duplicated, "the duplicate-detection logic must catch a second owner"


def test_reconciliation_metrics_are_finance_owned() -> None:
    for metric in load_metrics():
        if metric["authoritative_interface"] == "reward_reconciliation":
            assert metric["owner"] == "finance", metric["name"]


def test_warehouse_health_metrics_are_platform_owned() -> None:
    for metric in load_metrics():
        if metric["authoritative_interface"] == "warehouse_health":
            assert metric["owner"] == "platform", metric["name"]

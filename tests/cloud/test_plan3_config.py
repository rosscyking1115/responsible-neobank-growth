"""Plan 3 cloud configuration validation (Plan 3, Task 1).

Configuration validation fails for a missing run ID, region, labels, dataset
expiry, query ceiling, spend ceiling, approval state or cleanup command — and
the billable-execution guard stays closed until the user's spend-preflight
approval is recorded.
"""

import copy
from pathlib import Path

import pytest
import yaml

from tools.cloud.plan3_config import billable_execution_allowed, load_run_config, validate

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "cloud" / "gcp" / "plan3" / "run-config.yml"

REQUIRED_TOP_LEVEL = [
    "run_id",
    "region",
    "labels",
    "datasets",
    "dataset_expiry_days",
    "max_bytes_billed_per_query",
    "spend_ceiling_gbp",
    "stop_at_pct_of_ceiling",
    "approval",
    "cleanup",
]


@pytest.fixture()
def config() -> dict:
    return load_run_config(CONFIG)


def test_committed_config_validates(config) -> None:
    assert validate(config) == []


@pytest.mark.parametrize("key", REQUIRED_TOP_LEVEL)
def test_missing_key_fails(config, key) -> None:
    broken = copy.deepcopy(config)
    del broken[key]
    assert any(key in error for error in validate(broken)), key


def test_labels_must_scope_the_run(config) -> None:
    broken = copy.deepcopy(config)
    broken["labels"].pop("route_c", None)
    assert any("route_c" in error for error in validate(broken))


def test_expiry_and_ceilings_must_be_positive(config) -> None:
    for key in ("dataset_expiry_days", "max_bytes_billed_per_query", "spend_ceiling_gbp"):
        broken = copy.deepcopy(config)
        broken[key] = 0
        assert any(key in error for error in validate(broken)), key


def test_default_query_ceiling_is_one_gib(config) -> None:
    assert config["max_bytes_billed_per_query"] == 1_073_741_824


def test_spend_ceiling_within_plan_limit(config) -> None:
    assert 0 < config["spend_ceiling_gbp"] <= 10
    assert config["stop_at_pct_of_ceiling"] <= 80


def test_cleanup_runbook_exists_and_is_reviewed(config) -> None:
    assert config["cleanup"]["commands_reviewed"] is True
    runbook = ROOT / config["cleanup"]["runbook"]
    assert runbook.exists()
    assert config["cleanup"]["deadline"], "cleanup deadline must be scheduled"


def test_datasets_follow_isolated_naming(config) -> None:
    for dataset in config["datasets"]:
        assert dataset.startswith("neobank_p3_"), dataset
        assert config["run_id"].replace("-", "_") in dataset, (
            f"{dataset}: datasets carry the run identifier"
        )


def test_billable_execution_stays_blocked_without_user_approval(config) -> None:
    assert config["approval"]["spend_preflight_approved"] is False, (
        "the committed config must not pre-approve spend; only the user flips this"
    )
    assert billable_execution_allowed(config) is False

    approved = copy.deepcopy(config)
    approved["approval"].update(
        {"spend_preflight_approved": True, "approved_by": "ross", "approved_on": "2026-07-18"}
    )
    assert billable_execution_allowed(approved) is True

    unattributed = copy.deepcopy(config)
    unattributed["approval"]["spend_preflight_approved"] = True
    assert billable_execution_allowed(unattributed) is False, (
        "approval without approver/date is not approval"
    )


def test_config_is_valid_yaml_round_trip() -> None:
    with open(CONFIG, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert raw == load_run_config(CONFIG)

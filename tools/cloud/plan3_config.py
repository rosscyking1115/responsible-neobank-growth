"""Plan 3 run-configuration validation and the billable-execution guard.

Every Plan 3 script that could create a resource or run a query must call
``billable_execution_allowed`` first. The guard opens only when the committed
configuration records the user's explicit spend-preflight approval with
approver and date (Plan 3 §5.1); accepting the plan approved the design, not a
bill.
"""

from pathlib import Path

import yaml

REQUIRED_KEYS = {
    "run_id": str,
    "region": str,
    "gcp_project": str,
    "labels": dict,
    "datasets": list,
    "dataset_expiry_days": int,
    "max_bytes_billed_per_query": int,
    "custom_query_quota_gib_per_day": int,
    "spend_ceiling_gbp": (int, float),
    "stop_at_pct_of_ceiling": (int, float),
    "approval": dict,
    "cleanup": dict,
}


def load_run_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate(config: dict) -> list[str]:
    errors: list[str] = []
    for key, expected_type in REQUIRED_KEYS.items():
        if key not in config:
            errors.append(f"missing required key: {key}")
            continue
        if not isinstance(config[key], expected_type):
            errors.append(f"{key}: expected {expected_type}, got {type(config[key]).__name__}")

    if errors:
        return errors

    if not config["run_id"].strip():
        errors.append("run_id must be non-empty")
    if not config["region"].strip():
        errors.append("region must be non-empty")
    if config["labels"].get("route_c") != "plan3":
        errors.append("labels must include route_c: plan3 for resource isolation")
    if not config["datasets"]:
        errors.append("datasets must list the isolated Plan 3 datasets")
    if config["dataset_expiry_days"] <= 0:
        errors.append("dataset_expiry_days must be positive")
    if config["max_bytes_billed_per_query"] <= 0:
        errors.append("max_bytes_billed_per_query must be positive")
    if config["spend_ceiling_gbp"] <= 0:
        errors.append("spend_ceiling_gbp must be positive")
    if not 0 < config["stop_at_pct_of_ceiling"] <= 80:
        errors.append("stop_at_pct_of_ceiling must be within (0, 80]")

    approval = config["approval"]
    if "spend_preflight_approved" not in approval:
        errors.append("approval.spend_preflight_approved must be declared")
    for key in ("approved_by", "approved_on"):
        if key not in approval:
            errors.append(f"approval.{key} must be declared (null until approved)")

    cleanup = config["cleanup"]
    for key in ("deadline", "commands_reviewed", "runbook"):
        if not cleanup.get(key):
            errors.append(f"cleanup.{key} must be set")
    return errors


def billable_execution_allowed(config: dict) -> bool:
    """True only when the user's spend-preflight approval is fully recorded."""
    approval = config.get("approval", {})
    return (
        approval.get("spend_preflight_approved") is True
        and bool(approval.get("approved_by"))
        and bool(approval.get("approved_on"))
        and validate(config) == []
    )

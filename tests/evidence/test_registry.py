"""Evidence registry validation (Plan 4, Task 1).

Every public claim resolves to one allowed evidence level with real evidence
paths, limitations and surfaces. The registry fails for empty evidence paths,
unsupported levels, missing limitations, or any Looker claim above
`configured` without Plan 3 validator evidence.
"""

import copy
import json
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "evidence" / "registry.yml"
SCHEMA = ROOT / "evidence" / "schema.json"

ALLOWED_LEVELS = {
    "planned", "configured", "executed-local", "executed-bigquery",
    "measured", "validated-looker", "historical", "illustrative", "external",
}

REQUIRED_CLAIM_GROUPS = {
    "counts", "execution", "generation", "parity", "backfill",
    "reconciliation", "cost", "looker", "adapters", "cloud-history",
    "demo", "dataset",
}


def load_registry() -> dict:
    with open(REGISTRY, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema() -> dict:
    with open(SCHEMA, encoding="utf-8") as f:
        return json.load(f)


def validate(registry: dict) -> list[str]:
    """Registry-level rules beyond the JSON schema."""
    errors: list[str] = []
    try:
        jsonschema.validate(instance=registry, schema=load_schema())
    except jsonschema.ValidationError as invalid:
        errors.append(f"schema: {invalid.message}")
        return errors
    for claim in registry["claims"]:
        cid = claim["claim_id"]
        if claim["level"] not in ALLOWED_LEVELS:
            errors.append(f"{cid}: unsupported level {claim['level']}")
        for path in claim["evidence_paths"]:
            if not str(path).strip():
                errors.append(f"{cid}: empty evidence path")
        if not claim["limitations"].strip():
            errors.append(f"{cid}: missing limitations")
        if claim["level"] == "validated-looker" and not any(
            "artifacts/plan3/looker" in str(p) for p in claim["evidence_paths"]
        ):
            errors.append(f"{cid}: validated-looker requires Plan 3 validator evidence")
    return errors


def test_registry_validates() -> None:
    assert validate(load_registry()) == []


def test_every_repo_evidence_path_exists() -> None:
    for claim in load_registry()["claims"]:
        for path in claim["evidence_paths"]:
            path = str(path)
            if path.startswith("http"):
                continue
            assert (ROOT / path).exists(), f"{claim['claim_id']}: missing {path}"


def test_required_claim_groups_are_covered() -> None:
    groups = {claim["group"] for claim in load_registry()["claims"]}
    missing = REQUIRED_CLAIM_GROUPS - groups
    assert not missing, f"claim groups without records: {sorted(missing)}"


def test_release_branch_forbids_looker_execution_claims() -> None:
    registry = load_registry()
    assert registry["release_branch"] == "bigquery-only"
    for claim in registry["claims"]:
        if claim["group"] == "looker":
            assert claim["level"] in {"configured", "planned"}, (
                f"{claim['claim_id']}: BigQuery-only branch permits no Looker "
                "execution claim"
            )


def test_empty_evidence_path_fails() -> None:
    registry = copy.deepcopy(load_registry())
    registry["claims"][0]["evidence_paths"] = [""]
    assert any("empty evidence path" in e for e in validate(registry))


def test_unsupported_level_fails() -> None:
    registry = copy.deepcopy(load_registry())
    registry["claims"][0]["level"] = "verified-in-production"
    assert validate(registry), "an unsupported level must fail"


def test_missing_limitations_fails() -> None:
    registry = copy.deepcopy(load_registry())
    registry["claims"][0]["limitations"] = " " * 12  # schema-valid, semantically empty
    assert any("limitations" in e for e in validate(registry))


def test_looker_claim_without_validator_evidence_fails() -> None:
    registry = copy.deepcopy(load_registry())
    registry["claims"].append(
        {
            "claim_id": "bogus-looker",
            "group": "looker",
            "statement": "LookML validated in a Looker instance",
            "level": "validated-looker",
            "scope": "mutation test fixture",
            "evidence_paths": ["looker/README.md"],
            "commit": "abcdef0",
            "limitations": "mutation fixture only",
            "surfaces": ["README.md"],
        }
    )
    assert any("validator evidence" in e for e in validate(registry))


def test_measured_claims_carry_measurement_dates() -> None:
    for claim in load_registry()["claims"]:
        if claim["level"] == "measured":
            assert claim.get("measured_on"), f"{claim['claim_id']}: measured needs a date"

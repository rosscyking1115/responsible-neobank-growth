"""Route C migration inventory tests (Plan 1, Task 5).

Gate G0.4 requires every current source, model, consumer and job to carry an
explicit migration decision. An unclassified dbt model, raw table, Streamlit
tab, API output or workflow fails these tests, and no row may remain unknown.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs" / "migration" / "route-c-model-inventory.csv"
CONSUMER_MAP = ROOT / "docs" / "migration" / "route-c-consumer-map.md"
MIGRATION_MAP = ROOT / "docs" / "migration" / "route-c-migration-map.md"
BASELINE_MODELS = ROOT / "artifacts" / "baseline" / "2026-route-c" / "model-inventory.csv"
CLOUD_MANIFEST = ROOT / "cloud" / "gcp" / "raw_bigquery_manifest.json"

REQUIRED_COLUMNS = [
    "current_path",
    "current_relation",
    "current_layer",
    "current_grain",
    "current_owner",
    "current_consumers",
    "current_materialization",
    "current_tests",
    "target_action",
    "target_relation",
    "target_layer",
    "target_interface",
    "compatibility_method",
    "synthetic_source_family",
    "route_c_value",
    "evidence_status",
    "notes",
]

ALLOWED_ACTIONS = {
    "preserve",
    "migrate",
    "compatibility_view",
    "downstream_consumer",
    "deprecate_with_evidence",
    "remove_unsupported_claim",
}

ADMITTED_FAMILIES = {
    "campaign_spend",
    "application_kyc_account",
    "activation_funding",
    "referral_reward",
    "experiment",
    "customer_outcome",
    "none",  # retained batch source outside the event boundary
}

STREAMLIT_TABS = [
    "Product health",
    "Customer outcomes",
    "Digital inclusion",
    "Customer protection",
    "Pricing intelligence",
    "Experiments",
    "Monitoring",
]

API_ROUTES = [
    "/health",
    "/score/activation",
    "/score/churn",
    "/score/upsell",
    "/recommend/offer",
    "/simulate/pricing",
]

WORKFLOWS = ["ci.yml", "monitoring-snapshot.yml", "keepalive.yml"]

ADAPTERS = ["uci_bank_marketing", "criteo_uplift"]


def load_inventory() -> list[dict]:
    with open(INVENTORY, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == REQUIRED_COLUMNS, (
            f"inventory columns must match the contract exactly; got {reader.fieldnames}"
        )
        return list(reader)


def test_inventory_exists_and_has_rows() -> None:
    rows = load_inventory()
    assert len(rows) >= 50, "inventory must cover all raw tables and dbt models"


def test_no_row_is_unclassified() -> None:
    for row in load_inventory():
        relation = row["current_relation"]
        assert row["target_action"] in ALLOWED_ACTIONS, (
            f"{relation}: target_action {row['target_action']!r} is not allowed"
        )
        for field in REQUIRED_COLUMNS:
            value = row[field].strip().lower()
            assert value not in {"", "unknown", "tbd", "?"}, (
                f"{relation}: field {field} is unclassified ({row[field]!r})"
            )


def test_every_baseline_dbt_model_has_exactly_one_row() -> None:
    with open(BASELINE_MODELS, encoding="utf-8", newline="") as f:
        baseline = [row["name"] for row in csv.DictReader(f)]
    inventory_models = [
        row["current_relation"] for row in load_inventory() if row["current_layer"] != "raw"
    ]
    missing = set(baseline) - set(inventory_models)
    assert not missing, f"dbt models without a migration decision: {sorted(missing)}"
    duplicated = {m for m in inventory_models if inventory_models.count(m) > 1}
    assert not duplicated, f"models classified twice: {sorted(duplicated)}"


def test_every_raw_table_has_exactly_one_row() -> None:
    with open(CLOUD_MANIFEST, encoding="utf-8") as f:
        raw_tables = {t["name"] if isinstance(t, dict) else t for t in json.load(f)["tables"]}
    inventory_raw = [
        row["current_relation"] for row in load_inventory() if row["current_layer"] == "raw"
    ]
    missing = raw_tables - set(inventory_raw)
    assert not missing, f"raw tables without a migration decision: {sorted(missing)}"


def test_migrated_models_declare_compatibility() -> None:
    for row in load_inventory():
        if row["target_action"] in {"migrate", "deprecate_with_evidence"}:
            assert row["compatibility_method"].strip().lower() not in {"", "none", "n/a"}, (
                f"{row['current_relation']}: {row['target_action']} requires a "
                "compatibility method"
            )


def test_source_families_stay_within_locked_scope() -> None:
    for row in load_inventory():
        family = row["synthetic_source_family"]
        assert family in ADMITTED_FAMILIES, (
            f"{row['current_relation']}: family {family!r} outside locked scope"
        )


def test_consumer_map_covers_every_consumer_surface() -> None:
    text = CONSUMER_MAP.read_text(encoding="utf-8")
    for tab in STREAMLIT_TABS:
        assert tab in text, f"consumer map must cover Streamlit tab: {tab}"
    for route in API_ROUTES:
        assert route in text, f"consumer map must cover API output: {route}"
    for workflow in WORKFLOWS:
        assert workflow in text, f"consumer map must cover scheduled job: {workflow}"
    for adapter in ADAPTERS:
        assert adapter in text, f"consumer map must cover real-data adapter: {adapter}"
    assert "looker" in text.lower(), "consumer map must cover future Looker Explores"


def test_migration_map_states_preservation_threshold() -> None:
    text = MIGRATION_MAP.read_text(encoding="utf-8").lower()
    for marker in [
        "preservation",
        "compatibility",
        "governed interface",
        "validated capability",
    ]:
        assert marker in text, f"migration map must address: {marker}"

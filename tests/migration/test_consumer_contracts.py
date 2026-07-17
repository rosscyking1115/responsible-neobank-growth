"""Consumer compatibility contract tests (Plan 2, Task 10).

Each preserved consumer path must work through a compatibility relation over
the governed interfaces: required columns and grain hold, no consumer needs
landing payloads, and a real existing consumer (the Welch/CUPED estimator
behind the Experiments tab) runs end to end on the compatibility relation.
Requires the built local pipeline; skips with instructions otherwise.
"""

from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE_DB = ROOT / "neobank.duckdb"

pytestmark = pytest.mark.skipif(
    not WAREHOUSE_DB.exists(),
    reason="requires the built local pipeline (generate -> load -> dbt build)",
)

# Required columns per compatibility relation: the contract each preserved
# consumer actually depends on (Task 5 consumer map).
REQUIRED_CONTRACTS = {
    "main_compatibility.cmp_fct_activation": {
        "key": "user_id",
        "columns": {
            "user_id",
            "signup_ts",
            "signup_date",
            "signup_week",
            "signup_channel",
            "first_transaction_ts",
            "first_transaction_date",
            "activated_ever",
            "activated_d7",
        },
    },
    "main_compatibility.cmp_fct_experiment_user_metrics": {
        "key": "user_id",
        "columns": {
            "experiment_name",
            "user_id",
            "variant",
            "signup_date",
            "signup_channel",
            "activated_d7",
            "activated_ever",
            "support_contacts",
            "complaints",
        },
    },
    "main_compatibility.cmp_stg_referrals": {
        "key": "referral_id",
        "columns": {
            "referral_id",
            "referrer_user_id",
            "referee_user_id",
            "created_at",
            "created_date",
            "referrer_reward_gbp",
        },
    },
    "main_compatibility.cmp_fct_customer_outcomes": {
        "key": "user_id",
        "columns": {"user_id", "outcome_events", "complaint_count", "max_severity_rank"},
    },
}


@pytest.fixture(scope="module")
def connection():
    con = duckdb.connect(str(WAREHOUSE_DB), read_only=True)
    yield con
    con.close()


@pytest.mark.parametrize("relation", sorted(REQUIRED_CONTRACTS))
def test_compatibility_relation_serves_required_columns(connection, relation) -> None:
    contract = REQUIRED_CONTRACTS[relation]
    frame = connection.sql(f"select * from {relation} limit 0").df()
    missing = contract["columns"] - set(frame.columns)
    assert not missing, f"{relation}: missing required columns {sorted(missing)}"


@pytest.mark.parametrize("relation", sorted(REQUIRED_CONTRACTS))
def test_compatibility_relation_grain_holds(connection, relation) -> None:
    contract = REQUIRED_CONTRACTS[relation]
    total, distinct = connection.sql(
        f"select count(*), count(distinct {contract['key']}) from {relation}"
    ).fetchone()
    assert total > 0, f"{relation}: compatibility relation must not be empty"
    assert total == distinct, f"{relation}: grain violated on {contract['key']}"


def test_no_compatibility_relation_reads_landing_payloads() -> None:
    for path in (ROOT / "dbt_neobank" / "models" / "compatibility").glob("*.sql"):
        text = path.read_text(encoding="utf-8")
        assert "lnd_" not in text, (
            f"{path.name}: compatibility relations read governed interfaces, "
            "never version-specific landing models"
        )
        assert "payload" not in text.lower(), path.name


def test_existing_experiment_consumer_runs_on_governed_data(connection) -> None:
    """The Welch estimator behind the Experiments tab runs unchanged on the
    compatibility relation — the anchor consumer works end to end."""
    from src.experiments.analysis import difference_in_means, sample_ratio_mismatch

    frame = connection.sql(
        "select variant, cast(activated_d7 as int) as activated_d7"
        " from main_compatibility.cmp_fct_experiment_user_metrics"
    ).df()
    assert set(frame["variant"]) == {"control", "treatment"}

    estimate = difference_in_means(frame, "activated_d7")
    assert estimate.control_n >= 2 and estimate.treatment_n >= 2
    assert -1.0 <= estimate.effect <= 1.0

    srm = sample_ratio_mismatch(frame)
    assert srm.p_value >= 0.0
    assert set(srm.counts) == {"control", "treatment"}


def test_activated_d7_implies_activated_ever(connection) -> None:
    violations = connection.sql(
        "select count(*) from main_compatibility.cmp_fct_activation"
        " where activated_d7 and not activated_ever"
    ).fetchone()[0]
    assert violations == 0

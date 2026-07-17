"""Reward reconciliation execution oracle (Plan 2, Task 7).

Compares the *built* DuckDB warehouse against the generation run's truth
manifest: exact ledger totals, lifecycle states and exception identities for
the tiny profile. Requires the local pipeline to have run
(generate -> load -> dbt build); skips with instructions otherwise.
"""

import json
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "data" / "generated" / "tiny-a"
WAREHOUSE_DB = ROOT / "neobank.duckdb"

pytestmark = pytest.mark.skipif(
    not (GENERATED / "manifest.json").exists() or not WAREHOUSE_DB.exists(),
    reason=(
        "requires the local event pipeline: "
        "uv run python -m src.event_simulator.cli generate --profile tiny "
        "--output data/generated/tiny-a && "
        "uv run python -m src.ingestion.event_loader --source data/generated/tiny-a "
        "--warehouse data/warehouse && dbt build"
    ),
)


@pytest.fixture(scope="module")
def truth() -> dict:
    with open(GENERATED / "manifest.json", encoding="utf-8") as f:
        return json.load(f)["truth"]


@pytest.fixture(scope="module")
def connection():
    con = duckdb.connect(str(WAREHOUSE_DB), read_only=True)
    yield con
    con.close()


def test_entitlement_totals_match_truth(connection, truth) -> None:
    booked, settled, reversed_, outstanding = connection.sql(
        "select sum(booked_minor), sum(settled_minor), sum(reversed_minor),"
        " sum(outstanding_payable_minor) from main_logical.lgl_reward_entitlement"
    ).fetchone()
    rec = truth["reconciliation"]
    assert booked == rec["booked_minor"]
    assert settled == rec["settled_minor"]
    assert reversed_ == rec["reversed_minor"]
    assert outstanding == rec["outstanding_payable_minor"]
    entitled = connection.sql(
        "select sum(entitled_minor) from main_logical.lgl_reward_entitlement"
    ).fetchone()[0]
    assert entitled == rec["entitled_minor"]


def test_exception_identities_match_truth_exactly(connection, truth) -> None:
    rows = connection.sql(
        "select exception_reason, count(*) from main_logical.lgl_reward_entitlement"
        " where exception_reason is not null group by 1 order by 1"
    ).fetchall()
    observed = [{"reason": reason, "count": count} for reason, count in rows]
    assert observed == truth["reconciliation"]["exceptions"]


def test_lifecycle_states_match_truth(connection, truth) -> None:
    rows = connection.sql(
        "select referral_id, lifecycle_status from main_logical.lgl_reward_entitlement"
    ).fetchall()
    observed = dict(rows)
    expected = {
        referral: state
        for referral, state in truth["lifecycle_end_states"].items()
        if state != "invited"  # entitlement starts at qualification
    }
    assert observed == expected


def test_ledger_balances_and_final_day_agree(connection) -> None:
    debit, credit = connection.sql(
        "select sum(case when entry_side = 'debit' then amount_minor end),"
        " sum(case when entry_side = 'credit' then amount_minor end)"
        " from main_normalised.nrm_reward_ledger_entry"
    ).fetchone()
    assert debit == credit

    unbalanced = connection.sql(
        "select count(*) from main_logical.lgl_reward_ledger_reconciliation"
        " where not is_balanced"
    ).fetchone()[0]
    assert unbalanced == 0


def test_every_exception_traces_to_source_events(connection) -> None:
    orphans = connection.sql(
        "select count(*) from main_logical.lgl_reward_entitlement as entitlement"
        " where exception_reason is not null and not exists ("
        "   select 1 from main_normalised.nrm_referral_event as events"
        "   where events.referral_id = entitlement.referral_id"
        "   and events.event_type = 'referral_qualified')"
    ).fetchone()[0]
    assert orphans == 0

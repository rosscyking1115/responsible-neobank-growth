"""Build the tiny Route C event fixtures (Plan 1, Task 4).

Deterministic and literal-driven: no randomness, no wall clock. Rerunning
rewrites ``fixtures/events/tiny/*.jsonl`` and ``fixtures/truth/tiny/*.json``
with byte-identical content.

The truth dictionaries below are hand-declared numbers, not computed from the
events — the independent oracle (``src/synthetic_truth/oracle.py``) recomputes
observation from the raw events and the tests fail on any disagreement.

Run: ``uv run python tools/fixtures/build_tiny_fixtures.py``
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS_OUT = ROOT / "fixtures" / "events" / "tiny"
TRUTH_OUT = ROOT / "fixtures" / "truth" / "tiny"
GENERATOR_VERSION = "0.1.0"
REWARD_MINOR = 5000  # £50.00 per qualified referral


def _ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _fmt(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class ScenarioBuilder:
    def __init__(self, scenario_id: str, prefix: str):
        self.scenario_id = scenario_id
        self.prefix = prefix
        self.seq = 0
        self.events: list[dict] = []

    def add(
        self,
        event_name: str,
        schema_version: int,
        idempotency_key: str,
        source_service: str,
        trace_id: str,
        occurred_at: str,
        payload: dict,
        ingested_at: str | None = None,
    ) -> None:
        self.seq += 1
        occurred = _ts(occurred_at)
        emitted = occurred + timedelta(seconds=1)
        ingested = _ts(ingested_at) if ingested_at else emitted + timedelta(seconds=2)
        self.events.append(
            {
                "event_id": f"evt_{self.prefix}{self.seq:06d}",
                "idempotency_key": f"idk_{idempotency_key}",
                "event_name": event_name,
                "source_service": source_service,
                "occurred_at": _fmt(occurred),
                "emitted_at": _fmt(emitted),
                "ingested_at": _fmt(ingested),
                "schema_version": schema_version,
                "producer_id": f"{source_service}-01",
                "trace_id": f"trc_{trace_id}",
                "payload": payload,
                "generator_version": GENERATOR_VERSION,
                "scenario_id": self.scenario_id,
            }
        )

    # Convenience emitters -------------------------------------------------

    def invited(self, ref: str, referrer: str, occurred: str, **kw) -> None:
        self.add(
            "referral-invited",
            1,
            f"inv_{ref}",
            "referral-service",
            f"ref_{ref}",
            occurred,
            {
                "referral_id": f"ref_{ref}",
                "referrer_customer_id": f"cus_{referrer}",
                "invite_channel": "in_app_link",
            },
            **kw,
        )

    def qualified_v1(self, ref: str, referrer: str, referred: str, occurred: str, **kw) -> None:
        self.add(
            "referral-qualified",
            1,
            f"qual_{ref}",
            "referral-service",
            f"ref_{ref}",
            occurred,
            {
                "referral_id": f"ref_{ref}",
                "referrer_customer_id": f"cus_{referrer}",
                "referred_customer_id": f"cus_{referred}",
                "qualified_reason": "first_funding_completed",
            },
            **kw,
        )

    def qualified_v2(
        self, ref: str, referrer: str, referred: str, occurred: str, malformed: bool = False, **kw
    ) -> None:
        payload = {
            "referral_id": f"ref_{ref}",
            "referrer_customer_id": f"cus_{referrer}",
            "referred_customer_id": f"cus_{referred}",
            "qualified_reason": "first_funding_completed",
            "qualification_rule": "rule_v2_first_funding_within_30d",
            "qualifying_account_id": None,
        }
        if malformed:
            del payload["qualification_rule"]  # required in v2 -> quarantine
        self.add(
            "referral-qualified",
            2,
            f"qual_{ref}",
            "referral-service",
            f"ref_{ref}",
            occurred,
            payload,
            **kw,
        )

    def booked(self, ref: str, rwd: str, beneficiary: str, occurred: str, **kw) -> None:
        self.add(
            "reward-booked",
            1,
            f"book_{rwd}",
            "rewards-service",
            f"ref_{ref}",
            occurred,
            {
                "reward_id": f"rwd_{rwd}",
                "referral_id": f"ref_{ref}",
                "beneficiary_customer_id": f"cus_{beneficiary}",
                "amount_minor": REWARD_MINOR,
                "currency": "GBP",
            },
            **kw,
        )

    def settled(self, ref: str, rwd: str, stl: str, occurred: str, **kw) -> None:
        self.add(
            "reward-settled",
            1,
            f"settle_{rwd}",
            "rewards-service",
            f"ref_{ref}",
            occurred,
            {
                "reward_id": f"rwd_{rwd}",
                "settlement_id": f"stl_{stl}",
                "amount_minor": REWARD_MINOR,
                "currency": "GBP",
            },
            **kw,
        )

    def reversed_(self, ref: str, rwd: str, rev: str, occurred: str, **kw) -> None:
        self.add(
            "reward-reversed",
            1,
            f"reverse_{rwd}",
            "rewards-service",
            f"ref_{ref}",
            occurred,
            {
                "reward_id": f"rwd_{rwd}",
                "reversal_id": f"rev_{rev}",
                "amount_minor": REWARD_MINOR,
                "currency": "GBP",
                "reversal_reason": "qualification_withdrawn",
            },
            **kw,
        )


def build_happy_path() -> ScenarioBuilder:
    b = ScenarioBuilder("happy-path", "hp")
    b.add(
        "campaign-spend-recorded",
        1,
        "spend_cmp_spring_boost_20260101",
        "campaign-service",
        "cmp_spring_boost",
        "2026-01-01T09:00:00Z",
        {
            "campaign_id": "cmp_spring_boost",
            "spend_date": "2026-01-01",
            "amount_minor": 250000,
            "currency": "GBP",
            "channel": "paid_social",
        },
    )
    b.add(
        "application-submitted",
        1,
        "app_000001",
        "onboarding-service",
        "app_000001",
        "2026-01-05T09:00:00Z",
        {
            "application_id": "app_000001",
            "customer_id": "cus_b00001",
            "channel": "referral",
            "campaign_id": None,
            "referral_id": "ref_000001",
            "requested_product": "current_account",
        },
    )
    b.add(
        "kyc-decisioned",
        1,
        "kyc_app_000001",
        "kyc-service",
        "app_000001",
        "2026-01-05T09:10:00Z",
        {
            "application_id": "app_000001",
            "customer_id": "cus_b00001",
            "decision": "approved",
            "decision_source": "automated",
        },
    )
    b.add(
        "account-activated",
        1,
        "act_acc_000001",
        "account-service",
        "app_000001",
        "2026-01-05T09:20:00Z",
        {
            "account_id": "acc_000001",
            "customer_id": "cus_b00001",
            "application_id": "app_000001",
        },
    )
    b.add(
        "account-funded",
        1,
        "fund_acc_000001_1",
        "account-service",
        "app_000001",
        "2026-01-05T09:30:00Z",
        {
            "account_id": "acc_000001",
            "customer_id": "cus_b00001",
            "amount_minor": 10000,
            "currency": "GBP",
            "funding_method": "bank_transfer",
            "is_first_funding": True,
        },
    )
    b.invited("000001", "a00001", "2026-01-04T18:00:00Z")
    b.qualified_v1("000001", "a00001", "b00001", "2026-01-05T09:31:00Z")
    b.booked("000001", "000001", "a00001", "2026-01-05T10:00:00Z")
    b.settled("000001", "000001", "000001", "2026-01-06T10:00:00Z")
    return b


TRUTH_HAPPY_PATH = {
    "scenario_id": "happy-path",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 9,
    "unique_business_events": 9,
    "duplicates": 0,
    "quarantined": 0,
    "late_arrivals": 0,
    "lifecycle_end_states": {"ref_000001": "settled"},
    "reconciliation": {
        "entitled_minor": 5000,
        "booked_minor": 5000,
        "settled_minor": 5000,
        "reversed_minor": 0,
        "outstanding_payable_minor": 0,
        "exceptions": [],
    },
}


def build_duplicate_delivery() -> ScenarioBuilder:
    b = ScenarioBuilder("duplicate-delivery", "dd")
    b.invited("000010", "a00010", "2026-01-05T09:00:00Z")
    b.qualified_v1("000010", "a00010", "b00010", "2026-01-05T10:00:00Z")
    # Redelivery of the same business event: same idempotency key, new event_id,
    # later ingestion.
    b.qualified_v1(
        "000010", "a00010", "b00010", "2026-01-05T10:00:00Z", ingested_at="2026-01-05T10:15:00Z"
    )
    b.booked("000010", "000010", "a00010", "2026-01-05T11:00:00Z")
    b.settled("000010", "000010", "000010", "2026-01-06T11:00:00Z")
    return b


TRUTH_DUPLICATE_DELIVERY = {
    "scenario_id": "duplicate-delivery",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 5,
    "unique_business_events": 4,
    "duplicates": 1,
    "quarantined": 0,
    "late_arrivals": 0,
    "lifecycle_end_states": {"ref_000010": "settled"},
    "reconciliation": {
        "entitled_minor": 5000,
        "booked_minor": 5000,
        "settled_minor": 5000,
        "reversed_minor": 0,
        "outstanding_payable_minor": 0,
        "exceptions": [],
    },
}


def build_late_arrival() -> ScenarioBuilder:
    b = ScenarioBuilder("late-arrival", "la")
    b.invited("000020", "a00020", "2026-01-05T09:00:00Z")
    # Qualification arrives 48h after it occurred: inside the 3-day lookback,
    # beyond the 24h late threshold.
    b.qualified_v1(
        "000020", "a00020", "b00020", "2026-01-05T10:00:00Z", ingested_at="2026-01-07T10:00:00Z"
    )
    b.booked("000020", "000020", "a00020", "2026-01-05T11:00:00Z")
    b.settled("000020", "000020", "000020", "2026-01-06T11:00:00Z")
    return b


TRUTH_LATE_ARRIVAL = {
    "scenario_id": "late-arrival",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 4,
    "unique_business_events": 4,
    "duplicates": 0,
    "quarantined": 0,
    "late_arrivals": 1,
    "lifecycle_end_states": {"ref_000020": "settled"},
    "reconciliation": {
        "entitled_minor": 5000,
        "booked_minor": 5000,
        "settled_minor": 5000,
        "reversed_minor": 0,
        "outstanding_payable_minor": 0,
        "exceptions": [],
    },
}


def build_reversal() -> ScenarioBuilder:
    b = ScenarioBuilder("reversal", "rv")
    b.invited("000030", "a00030", "2026-01-05T09:00:00Z")
    b.qualified_v1("000030", "a00030", "b00030", "2026-01-05T10:00:00Z")
    b.booked("000030", "000030", "a00030", "2026-01-05T11:00:00Z")
    b.reversed_("000030", "000030", "000030", "2026-01-06T10:00:00Z")
    return b


TRUTH_REVERSAL = {
    "scenario_id": "reversal",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 4,
    "unique_business_events": 4,
    "duplicates": 0,
    "quarantined": 0,
    "late_arrivals": 0,
    "lifecycle_end_states": {"ref_000030": "reversed"},
    "reconciliation": {
        "entitled_minor": 5000,
        "booked_minor": 5000,
        "settled_minor": 0,
        "reversed_minor": 5000,
        "outstanding_payable_minor": 0,
        "exceptions": [],
    },
}


def build_malformed_quarantine() -> ScenarioBuilder:
    b = ScenarioBuilder("malformed-quarantine", "mq")
    b.invited("000040", "a00040", "2026-01-05T09:00:00Z")
    # v2 payload missing its required qualification_rule -> quarantine; the
    # referral never reaches a canonical qualified state.
    b.qualified_v2("000040", "a00040", "b00040", "2026-01-05T10:00:00Z", malformed=True)
    return b


TRUTH_MALFORMED_QUARANTINE = {
    "scenario_id": "malformed-quarantine",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 2,
    "unique_business_events": 1,
    "duplicates": 0,
    "quarantined": 1,
    "late_arrivals": 0,
    "lifecycle_end_states": {"ref_000040": "invited"},
    "reconciliation": {
        "entitled_minor": 0,
        "booked_minor": 0,
        "settled_minor": 0,
        "reversed_minor": 0,
        "outstanding_payable_minor": 0,
        "exceptions": [],
    },
}


def build_referral_v1_to_v2() -> ScenarioBuilder:
    b = ScenarioBuilder("referral-v1-to-v2", "vv")
    b.invited("000050", "a00050", "2026-01-05T09:00:00Z")
    b.qualified_v1("000050", "a00050", "b00050", "2026-01-05T10:00:00Z")
    b.booked("000050", "000050", "a00050", "2026-01-05T11:00:00Z")
    b.settled("000050", "000050", "000050", "2026-01-06T11:00:00Z")
    b.invited("000051", "a00051", "2026-01-05T09:30:00Z")
    b.qualified_v2("000051", "a00051", "b00051", "2026-01-05T10:30:00Z")
    b.booked("000051", "000051", "a00051", "2026-01-05T11:30:00Z")
    b.settled("000051", "000051", "000051", "2026-01-06T11:30:00Z")
    return b


TRUTH_REFERRAL_V1_TO_V2 = {
    "scenario_id": "referral-v1-to-v2",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 8,
    "unique_business_events": 8,
    "duplicates": 0,
    "quarantined": 0,
    "late_arrivals": 0,
    "lifecycle_end_states": {"ref_000050": "settled", "ref_000051": "settled"},
    "reconciliation": {
        "entitled_minor": 10000,
        "booked_minor": 10000,
        "settled_minor": 10000,
        "reversed_minor": 0,
        "outstanding_payable_minor": 0,
        "exceptions": [],
    },
}


def build_freshness_outage() -> ScenarioBuilder:
    b = ScenarioBuilder("freshness-outage", "fo")
    b.add(
        "campaign-spend-recorded",
        1,
        "spend_cmp_winter_20260105",
        "campaign-service",
        "cmp_winter",
        "2026-01-05T09:00:00Z",
        {
            "campaign_id": "cmp_winter",
            "spend_date": "2026-01-05",
            "amount_minor": 100000,
            "currency": "GBP",
            "channel": "paid_search",
        },
    )
    # 96-hour arrival gap: nothing lands between 05 Jan and 09 Jan.
    b.add(
        "campaign-spend-recorded",
        1,
        "spend_cmp_winter_20260109",
        "campaign-service",
        "cmp_winter",
        "2026-01-09T09:00:00Z",
        {
            "campaign_id": "cmp_winter",
            "spend_date": "2026-01-09",
            "amount_minor": 100000,
            "currency": "GBP",
            "channel": "paid_search",
        },
    )
    return b


TRUTH_FRESHNESS_OUTAGE = {
    "scenario_id": "freshness-outage",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 2,
    "unique_business_events": 2,
    "duplicates": 0,
    "quarantined": 0,
    "late_arrivals": 0,
    "lifecycle_end_states": {},
    "reconciliation": {
        "entitled_minor": 0,
        "booked_minor": 0,
        "settled_minor": 0,
        "reversed_minor": 0,
        "outstanding_payable_minor": 0,
        "exceptions": [],
    },
    "freshness": {"threshold_hours": 72, "max_gap_hours": 96.0, "breached": True},
}


def build_reconciliation_break() -> ScenarioBuilder:
    b = ScenarioBuilder("reconciliation-break", "rb")
    b.invited("000060", "a00060", "2026-01-05T09:00:00Z")
    b.qualified_v1("000060", "a00060", "b00060", "2026-01-05T10:00:00Z")
    # Intentionally no reward-booked event: the entitlement exists but the
    # posting is missing.
    return b


TRUTH_RECONCILIATION_BREAK = {
    "scenario_id": "reconciliation-break",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 2,
    "unique_business_events": 2,
    "duplicates": 0,
    "quarantined": 0,
    "late_arrivals": 0,
    "lifecycle_end_states": {"ref_000060": "qualified"},
    "reconciliation": {
        "entitled_minor": 5000,
        "booked_minor": 0,
        "settled_minor": 0,
        "reversed_minor": 0,
        "outstanding_payable_minor": 0,
        "exceptions": [{"reason": "missing_posting", "count": 1}],
    },
}


def build_referral_known_truth() -> ScenarioBuilder:
    """Plan 1 section 8.3: the mandatory hand-built combined referral case."""
    b = ScenarioBuilder("referral-known-truth", "kt")
    # ref_100001 — valid invite + qualification that settles normally (05 Jan).
    b.invited("100001", "a10001", "2026-01-04T18:00:00Z")
    b.qualified_v1("100001", "a10001", "b10001", "2026-01-05T09:00:00Z")
    b.booked("100001", "100001", "a10001", "2026-01-05T10:00:00Z")
    b.settled("100001", "100001", "100001", "2026-01-06T10:00:00Z")
    # ref_100002 — duplicated delivery sharing an idempotency key (05 Jan).
    b.invited("100002", "a10002", "2026-01-04T18:30:00Z")
    b.qualified_v1("100002", "a10002", "b10002", "2026-01-05T09:30:00Z")
    b.qualified_v1(
        "100002", "a10002", "b10002", "2026-01-05T09:30:00Z", ingested_at="2026-01-05T09:45:00Z"
    )
    b.booked("100002", "100002", "a10002", "2026-01-05T10:30:00Z")
    b.settled("100002", "100002", "100002", "2026-01-06T10:30:00Z")
    # ref_100003 — qualification arrives 36h after occurrence (06 Jan).
    b.invited("100003", "a10003", "2026-01-05T18:00:00Z")
    b.qualified_v1(
        "100003", "a10003", "b10003", "2026-01-06T09:00:00Z", ingested_at="2026-01-07T21:00:00Z"
    )
    b.booked("100003", "100003", "a10003", "2026-01-06T10:00:00Z")
    b.settled("100003", "100003", "100003", "2026-01-07T10:00:00Z")
    # ref_100004 — booked reward later reversed (06-07 Jan).
    b.invited("100004", "a10004", "2026-01-05T18:30:00Z")
    b.qualified_v1("100004", "a10004", "b10004", "2026-01-06T09:30:00Z")
    b.booked("100004", "100004", "a10004", "2026-01-06T10:30:00Z")
    b.reversed_("100004", "100004", "100004", "2026-01-07T10:30:00Z")
    # ref_100005 — malformed v2 payload sent to quarantine (06 Jan).
    b.invited("100005", "a10005", "2026-01-05T19:00:00Z")
    b.qualified_v2("100005", "a10005", "b10005", "2026-01-06T09:45:00Z", malformed=True)
    # ref_100006 — qualified but the reward posting is intentionally missing (06 Jan).
    b.invited("100006", "a10006", "2026-01-05T19:30:00Z")
    b.qualified_v1("100006", "a10006", "b10006", "2026-01-06T09:50:00Z")
    return b


TRUTH_REFERRAL_KNOWN_TRUTH = {
    "scenario_id": "referral-known-truth",
    "seed": 42,
    "generator_version": GENERATOR_VERSION,
    "event_count": 21,
    "unique_business_events": 19,
    "duplicates": 1,
    "quarantined": 1,
    "late_arrivals": 1,
    "lifecycle_end_states": {
        "ref_100001": "settled",
        "ref_100002": "settled",
        "ref_100003": "settled",
        "ref_100004": "reversed",
        "ref_100005": "invited",
        "ref_100006": "qualified",
    },
    "reconciliation": {
        "entitled_minor": 25000,
        "booked_minor": 20000,
        "settled_minor": 15000,
        "reversed_minor": 5000,
        "outstanding_payable_minor": 0,
        "exceptions": [{"reason": "missing_posting", "count": 1}],
    },
    "daily_entitlement_minor": {"2026-01-05": 10000, "2026-01-06": 15000},
    "daily_booked_minor": {"2026-01-05": 10000, "2026-01-06": 10000},
}


SCENARIOS: list[tuple[ScenarioBuilder, dict]] = []


def build_all() -> list[tuple[ScenarioBuilder, dict]]:
    return [
        (build_happy_path(), TRUTH_HAPPY_PATH),
        (build_duplicate_delivery(), TRUTH_DUPLICATE_DELIVERY),
        (build_late_arrival(), TRUTH_LATE_ARRIVAL),
        (build_reversal(), TRUTH_REVERSAL),
        (build_malformed_quarantine(), TRUTH_MALFORMED_QUARANTINE),
        (build_referral_v1_to_v2(), TRUTH_REFERRAL_V1_TO_V2),
        (build_freshness_outage(), TRUTH_FRESHNESS_OUTAGE),
        (build_reconciliation_break(), TRUTH_RECONCILIATION_BREAK),
        (build_referral_known_truth(), TRUTH_REFERRAL_KNOWN_TRUTH),
    ]


def main() -> None:
    EVENTS_OUT.mkdir(parents=True, exist_ok=True)
    TRUTH_OUT.mkdir(parents=True, exist_ok=True)
    for builder, truth in build_all():
        events_path = EVENTS_OUT / f"{builder.scenario_id}.jsonl"
        lines = [json.dumps(event, sort_keys=True) for event in builder.events]
        events_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        truth_path = TRUTH_OUT / f"{builder.scenario_id}.json"
        truth_path.write_text(
            json.dumps(truth, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"{builder.scenario_id}: {len(builder.events)} deliveries")


if __name__ == "__main__":
    main()

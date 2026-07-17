"""Valid domain lifecycle tests (Plan 2, Task 2).

Only Gate 0-approved lifecycle transitions may be emitted; valid paths produce
schema-valid events with deterministic identity and time. Invalid transitions
raise before any event exists.
"""

from collections import defaultdict
from pathlib import Path

import pytest

from src.event_simulator.config import load_config
from src.event_simulator.generator import generate_valid_events
from src.event_simulator.state import LifecycleError, ReferralLifecycle
from src.synthetic_truth.oracle import classify_deliveries

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT / "config" / "simulator" / "tiny.yml")


@pytest.fixture(scope="module")
def generation():
    return generate_valid_events(CONFIG)


def test_every_generated_event_is_schema_valid(generation) -> None:
    valid, quarantined = classify_deliveries(generation.events)
    assert quarantined == [], (
        "Task 2 generates only valid events; the first quarantined event is "
        f"{quarantined[0] if quarantined else None}"
    )
    assert len(valid) == len(generation.events)


def test_delivery_volume_respects_profile_cap(generation) -> None:
    assert 0 < len(generation.events) <= CONFIG.max_deliveries


def test_timestamps_are_ordered_and_inside_window(generation) -> None:
    for event in generation.events:
        assert CONFIG.clock_start.isoformat().startswith(event["occurred_at"][:4]) or (
            event["occurred_at"] >= CONFIG.clock_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        assert event["occurred_at"] <= event["emitted_at"] <= event["ingested_at"]
        assert event["ingested_at"] <= CONFIG.clock_end.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_lifecycle_transitions_are_valid(generation) -> None:
    """KYC after application; activation after approval; funding after
    activation; qualification only for funded referred customers; rewards only
    after qualification."""
    events_by_customer: dict[str, list[dict]] = defaultdict(list)
    referral_events: dict[str, list[dict]] = defaultdict(list)
    for event in sorted(generation.events, key=lambda e: (e["occurred_at"], e["event_id"])):
        payload = event["payload"]
        if payload.get("customer_id"):
            events_by_customer[payload["customer_id"]].append(event)
        if payload.get("referral_id"):
            referral_events[payload["referral_id"]].append(event)

    for customer_id, events in events_by_customer.items():
        seen = [e["event_name"] for e in events]
        if "kyc-decisioned" in seen:
            assert "application-submitted" in seen[: seen.index("kyc-decisioned")], customer_id
        if "account-activated" in seen:
            decision = next(e for e in events if e["event_name"] == "kyc-decisioned")
            assert decision["payload"]["decision"] == "approved", customer_id
        if "account-funded" in seen:
            assert "account-activated" in seen[: seen.index("account-funded")], customer_id

    for referral_id, events in referral_events.items():
        names = [e["event_name"] for e in events]
        assert names[0] == "referral-invited", referral_id
        if "referral-qualified" in names:
            assert names.index("referral-qualified") > names.index("referral-invited")
        for reward_event in ("reward-booked",):
            if reward_event in names:
                assert "referral-qualified" in names[: names.index(reward_event)], referral_id


def test_rewards_settle_or_stay_booked_never_both(generation) -> None:
    by_reward: dict[str, set[str]] = defaultdict(set)
    for event in generation.events:
        reward_id = event["payload"].get("reward_id")
        if reward_id:
            by_reward[reward_id].add(event["event_name"])
    for reward_id, names in by_reward.items():
        assert "reward-booked" in names, reward_id
        assert not ({"reward-settled", "reward-reversed"} <= names), (
            f"{reward_id}: valid generation must not both settle and reverse"
        )


def test_truth_counters_match_emitted_events(generation) -> None:
    counted: dict[str, int] = defaultdict(int)
    for event in generation.events:
        counted[event["event_name"]] += 1
    assert generation.truth.event_counts == dict(counted)
    settled = {
        r for r, state in generation.truth.referral_end_states.items() if state == "settled"
    }
    assert settled, "tiny generation must settle at least one referral"


def test_generation_is_deterministic_for_first_events(generation) -> None:
    again = generate_valid_events(CONFIG)
    assert [e["event_id"] for e in generation.events[:50]] == [
        e["event_id"] for e in again.events[:50]
    ]
    assert generation.truth.event_counts == again.truth.event_counts


def test_invalid_referral_transition_raises() -> None:
    lifecycle = ReferralLifecycle("ref_x000001")
    lifecycle.advance("invited")
    with pytest.raises(LifecycleError, match="booked"):
        lifecycle.advance("booked")  # must qualify first
    lifecycle.advance("qualified")
    lifecycle.advance("booked")
    lifecycle.advance("settled")
    with pytest.raises(LifecycleError, match="settled"):
        lifecycle.advance("reversed")  # terminal state reached

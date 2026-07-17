"""Route C event contract tests (Plan 1, Task 3).

Locked by ADR-route-c-event-boundary: every synthetic backend event validates
against the shared envelope schema plus its registered payload schema/version.
Invalid envelopes, unknown events/versions, wrong currency types, naive
timestamps, missing idempotency keys and incompatible v2 payloads must fail.
"""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
EVENTS_DIR = ROOT / "contracts" / "events"

ADMITTED_FAMILIES = {
    "campaign_spend",
    "application_kyc_account",
    "activation_funding",
    "referral_reward",
    "experiment",
    "customer_outcome",
}


def load_registry() -> dict:
    with open(EVENTS_DIR / "registry.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema(relative: str) -> dict:
    with open(EVENTS_DIR / relative, encoding="utf-8") as f:
        return json.load(f)


def envelope_schema() -> dict:
    return load_schema("event-envelope.schema.json")


def payload_schema(event_name: str, version: int) -> dict:
    registry = load_registry()
    events = {e["name"]: e for e in registry["events"]}
    if event_name not in events:
        raise KeyError(f"unknown event: {event_name}")
    schemas = events[event_name]["schemas"]
    if version not in schemas:
        raise KeyError(f"unknown version {version} for event {event_name}")
    return load_schema(schemas[version])


def valid_envelope(**overrides) -> dict:
    event = {
        "event_id": "evt_0a1b2c3d4e5f",
        "idempotency_key": "idk_ref_q_000001",
        "event_name": "referral-qualified",
        "source_service": "referral-service",
        "occurred_at": "2026-01-05T10:00:00Z",
        "emitted_at": "2026-01-05T10:00:01Z",
        "ingested_at": "2026-01-05T10:00:05Z",
        "schema_version": 1,
        "producer_id": "referral-service-01",
        "trace_id": "trc_referral_000001",
        "payload": valid_referral_qualified_v1(),
        "generator_version": "0.1.0",
        "scenario_id": "happy-path",
    }
    event.update(overrides)
    return event


def valid_referral_qualified_v1() -> dict:
    return {
        "referral_id": "ref_000001",
        "referrer_customer_id": "cus_a00001",
        "referred_customer_id": "cus_b00001",
        "qualified_reason": "first_funding_completed",
    }


def valid_reward_booked_v1() -> dict:
    return {
        "reward_id": "rwd_000001",
        "referral_id": "ref_000001",
        "beneficiary_customer_id": "cus_a00001",
        "amount_minor": 5000,
        "currency": "GBP",
    }


def assert_valid(instance: dict, schema: dict) -> None:
    jsonschema.validate(instance=instance, schema=schema)


def assert_invalid(instance: dict, schema: dict) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=schema)


# --- envelope ---------------------------------------------------------------


def test_valid_envelope_passes() -> None:
    assert_valid(valid_envelope(), envelope_schema())


@pytest.mark.parametrize(
    "field",
    [
        "event_id",
        "idempotency_key",
        "event_name",
        "source_service",
        "occurred_at",
        "emitted_at",
        "ingested_at",
        "schema_version",
        "producer_id",
        "trace_id",
        "payload",
        "generator_version",
        "scenario_id",
    ],
)
def test_envelope_missing_required_field_fails(field: str) -> None:
    event = valid_envelope()
    del event[field]
    assert_invalid(event, envelope_schema())


def test_naive_timestamp_fails() -> None:
    assert_invalid(
        valid_envelope(occurred_at="2026-01-05T10:00:00"), envelope_schema()
    )


def test_non_utc_offset_timestamp_fails() -> None:
    assert_invalid(
        valid_envelope(ingested_at="2026-01-05T10:00:00+01:00"), envelope_schema()
    )


def test_zero_or_negative_schema_version_fails() -> None:
    assert_invalid(valid_envelope(schema_version=0), envelope_schema())
    assert_invalid(valid_envelope(schema_version=-1), envelope_schema())


def test_unknown_envelope_field_fails() -> None:
    assert_invalid(valid_envelope(surprise_field="x"), envelope_schema())


# --- registry ---------------------------------------------------------------


def test_unknown_event_name_fails() -> None:
    with pytest.raises(KeyError):
        payload_schema("card-transaction-authorised", 1)


def test_unknown_version_fails() -> None:
    with pytest.raises(KeyError):
        payload_schema("referral-qualified", 99)


def test_registry_families_stay_within_locked_scope() -> None:
    registry = load_registry()
    families = {e["family"] for e in registry["events"]}
    unapproved = families - ADMITTED_FAMILIES
    assert not unapproved, f"unapproved event families: {unapproved}"


def test_registry_schema_files_exist_and_are_complete() -> None:
    registry = load_registry()
    referenced = set()
    for event in registry["events"]:
        for version, relative in event["schemas"].items():
            assert isinstance(version, int) and version >= 1
            path = EVENTS_DIR / relative
            assert path.exists(), f"registry references missing schema: {relative}"
            referenced.add(path.resolve())
    on_disk = {
        p.resolve()
        for pattern in ("v1/*.schema.json", "v2/*.schema.json")
        for p in EVENTS_DIR.glob(pattern)
    }
    assert on_disk == referenced, "every payload schema on disk must be registered exactly"


def test_registry_uses_fictional_namespace_only() -> None:
    text = (EVENTS_DIR / "registry.yml").read_text(encoding="utf-8").lower()
    for brand in ["monzo", "starling", "revolut", "barclays", "hsbc", "natwest"]:
        assert brand not in text, f"registry must not reference a real bank brand: {brand}"
    registry = load_registry()
    for service in registry["services"]:
        assert service["name"].endswith("-service")


# --- payload rules ----------------------------------------------------------


def test_all_registered_payload_examples_validate() -> None:
    registry = load_registry()
    for event in registry["events"]:
        for relative in event["schemas"].values():
            schema = load_schema(relative)
            example = schema.get("examples", [None])[0]
            assert example is not None, f"{relative} must embed one example payload"
            jsonschema.validate(instance=example, schema=schema)


def test_wrong_currency_type_fails() -> None:
    # JSON Schema treats a zero-fraction float (50.0) as a valid integer, so the
    # schema layer guards against fractional major units and string amounts;
    # rejecting float *representations* is the ingestion layer's job (Plan 2).
    schema = payload_schema("reward-booked", 1)
    payload = valid_reward_booked_v1()
    payload["amount_minor"] = 50.5  # fractional major units are forbidden
    assert_invalid(payload, schema)
    payload["amount_minor"] = "5000"
    assert_invalid(payload, schema)
    payload["amount_minor"] = 0  # rewards must be positive
    assert_invalid(payload, schema)


def test_missing_idempotency_key_fails() -> None:
    event = valid_envelope()
    del event["idempotency_key"]
    assert_invalid(event, envelope_schema())


# --- v1/v2 compatibility ----------------------------------------------------


def valid_referral_qualified_v2() -> dict:
    return {
        **valid_referral_qualified_v1(),
        "qualification_rule": "rule_v2_first_funding_within_30d",
        "qualifying_account_id": "acc_000001",
    }


def test_v2_payload_fails_v1_schema() -> None:
    assert_invalid(valid_referral_qualified_v2(), payload_schema("referral-qualified", 1))


def test_v1_payload_fails_v2_schema() -> None:
    assert_invalid(valid_referral_qualified_v1(), payload_schema("referral-qualified", 2))


def test_v2_payload_passes_v2_schema() -> None:
    assert_valid(valid_referral_qualified_v2(), payload_schema("referral-qualified", 2))

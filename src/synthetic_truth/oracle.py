"""Independent truth oracle for the tiny event fixtures.

The oracle recomputes observable facts (delivery counts, duplicates,
quarantines, late arrivals, lifecycle end states, subledger totals and
reconciliation exceptions) directly from a scenario's raw event fixture and
compares them with the hand-declared truth manifest. Truth manifests are never
generated from this code — that separation is what makes a mismatch meaningful.

Semantics locked by the event-boundary contract and the synthetic-truth contract:

- a delivery is quarantined when its envelope or registered payload schema
  fails validation; quarantined deliveries never mutate canonical state;
- canonical (business) events are unique ``idempotency_key`` values among valid
  deliveries, keeping the first delivery by ``ingested_at``;
- a delivery is late when ``ingested_at`` exceeds ``occurred_at`` by more than
  the scenario's ``late_threshold_hours``;
- referral lifecycle states progress invited -> qualified -> booked -> settled,
  with a reward reversal terminating the referral at ``reversed``;
- entitlement is ``reward_amount_minor`` per canonically qualified referral;
- reconciliation exceptions: ``missing_posting`` (qualified referral with no
  booked reward) and ``duplicate_posting`` (more than one booked reward for one
  referral).
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
EVENTS_DIR = ROOT / "contracts" / "events"

_STATE_ORDER = ["invited", "qualified", "booked", "settled"]


class TruthMismatchError(AssertionError):
    """Raised when a truth manifest disagrees with the recomputed observation."""


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_scenario(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _registry_schemas() -> dict[tuple[str, int], dict]:
    registry = yaml.safe_load((EVENTS_DIR / "registry.yml").read_text(encoding="utf-8"))
    schemas: dict[tuple[str, int], dict] = {}
    for event in registry["events"]:
        for version, relative in event["schemas"].items():
            schemas[(event["name"], int(version))] = _load_json(EVENTS_DIR / relative)
    return schemas


def _parse_ts(value: str) -> datetime:
    return datetime.strptime(value.replace("+00:00", "Z"), "%Y-%m-%dT%H:%M:%SZ")


def classify_deliveries(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split deliveries into (valid, quarantined) using envelope + payload schemas."""
    envelope = _load_json(EVENTS_DIR / "event-envelope.schema.json")
    payload_schemas = _registry_schemas()
    valid: list[dict] = []
    quarantined: list[dict] = []
    for event in events:
        try:
            jsonschema.validate(instance=event, schema=envelope)
            key = (event["event_name"], event["schema_version"])
            if key not in payload_schemas:
                raise jsonschema.ValidationError(f"unregistered event/version: {key}")
            jsonschema.validate(instance=event["payload"], schema=payload_schemas[key])
        except jsonschema.ValidationError:
            quarantined.append(event)
        else:
            valid.append(event)
    return valid, quarantined


def canonical_events(valid: list[dict]) -> list[dict]:
    """First delivery per idempotency_key, ordered by ingestion."""
    first: dict[str, dict] = {}
    for event in sorted(valid, key=lambda e: (_parse_ts(e["ingested_at"]), e["event_id"])):
        first.setdefault(event["idempotency_key"], event)
    return sorted(first.values(), key=lambda e: (_parse_ts(e["occurred_at"]), e["event_id"]))


def compute_observed(scenario: dict) -> dict:
    events_path = ROOT / scenario["events_fixture"]
    reward_amount = scenario["reward_amount_minor"]
    late_threshold_h = scenario["late_threshold_hours"]

    with open(events_path, encoding="utf-8") as f:
        deliveries = [json.loads(line) for line in f if line.strip()]

    valid, quarantined = classify_deliveries(deliveries)
    canonical = canonical_events(valid)

    late = [
        e
        for e in valid
        if (_parse_ts(e["ingested_at"]) - _parse_ts(e["occurred_at"])).total_seconds()
        > late_threshold_h * 3600
    ]

    # Referral lifecycle reconstruction over canonical events only.
    states: dict[str, str] = {}
    qualified_dates: dict[str, str] = {}
    booked_by_referral: dict[str, list[dict]] = defaultdict(list)
    reward_to_referral: dict[str, str] = {}
    booked = settled = reversed_ = 0
    daily_entitlement: dict[str, int] = defaultdict(int)
    daily_booked: dict[str, int] = defaultdict(int)

    def advance(referral_id: str, state: str) -> None:
        current = states.get(referral_id)
        if current == "reversed":
            return
        if state == "reversed" or current is None:
            states[referral_id] = state
            return
        if _STATE_ORDER.index(state) > _STATE_ORDER.index(current):
            states[referral_id] = state

    for event in canonical:
        name, payload = event["event_name"], event["payload"]
        day = event["occurred_at"][:10]
        if name == "referral-invited":
            advance(payload["referral_id"], "invited")
        elif name == "referral-qualified":
            advance(payload["referral_id"], "qualified")
            qualified_dates[payload["referral_id"]] = day
            daily_entitlement[day] += reward_amount
        elif name == "reward-booked":
            referral_id = payload["referral_id"]
            reward_to_referral[payload["reward_id"]] = referral_id
            booked_by_referral[referral_id].append(event)
            booked += payload["amount_minor"]
            daily_booked[day] += payload["amount_minor"]
            advance(referral_id, "booked")
        elif name == "reward-settled":
            settled += payload["amount_minor"]
            referral_id = reward_to_referral.get(payload["reward_id"])
            if referral_id:
                advance(referral_id, "settled")
        elif name == "reward-reversed":
            reversed_ += payload["amount_minor"]
            referral_id = reward_to_referral.get(payload["reward_id"])
            if referral_id:
                advance(referral_id, "reversed")

    exceptions: dict[str, int] = defaultdict(int)
    for referral_id in qualified_dates:
        postings = len(booked_by_referral.get(referral_id, []))
        if postings == 0:
            exceptions["missing_posting"] += 1
        elif postings > 1:
            exceptions["duplicate_posting"] += 1

    observed = {
        "event_count": len(deliveries),
        "unique_business_events": len(canonical),
        "duplicates": len(valid) - len(canonical),
        "quarantined": len(quarantined),
        "late_arrivals": len(late),
        "lifecycle_end_states": dict(sorted(states.items())),
        "reconciliation": {
            "entitled_minor": reward_amount * len(qualified_dates),
            "booked_minor": booked,
            "settled_minor": settled,
            "reversed_minor": reversed_,
            "outstanding_payable_minor": booked - settled - reversed_,
            "exceptions": [
                {"reason": reason, "count": count}
                for reason, count in sorted(exceptions.items())
            ],
        },
        "daily_entitlement_minor": dict(sorted(daily_entitlement.items())),
        "daily_booked_minor": dict(sorted(daily_booked.items())),
    }

    gap_threshold_h = scenario.get("freshness_gap_hours")
    if gap_threshold_h is not None:
        arrivals = sorted(_parse_ts(e["ingested_at"]) for e in deliveries)
        max_gap_h = max(
            (
                (b - a).total_seconds() / 3600
                for a, b in zip(arrivals, arrivals[1:], strict=False)
            ),
            default=0.0,
        )
        observed["freshness"] = {
            "threshold_hours": gap_threshold_h,
            "max_gap_hours": max_gap_h,
            "breached": max_gap_h > gap_threshold_h,
        }
    return observed


def compare_truth(truth: dict, observed: dict) -> list[str]:
    """Return one message per declared truth field that disagrees with observation."""
    mismatches: list[str] = []
    comparable = [
        "event_count",
        "unique_business_events",
        "duplicates",
        "quarantined",
        "late_arrivals",
        "lifecycle_end_states",
        "daily_entitlement_minor",
        "daily_booked_minor",
        "freshness",
    ]
    for field in comparable:
        if field in truth and truth[field] != observed.get(field):
            mismatches.append(
                f"{field}: declared {truth[field]!r} != observed {observed.get(field)!r}"
            )
    declared_rec = truth.get("reconciliation", {})
    observed_rec = observed["reconciliation"]
    for field, declared in declared_rec.items():
        if field == "exceptions":
            declared_sorted = sorted(declared, key=lambda e: e["reason"])
            if declared_sorted != observed_rec["exceptions"]:
                mismatches.append(
                    f"reconciliation.exceptions: declared {declared_sorted!r} "
                    f"!= observed {observed_rec['exceptions']!r}"
                )
        elif declared != observed_rec.get(field):
            observed_value = observed_rec.get(field)
            mismatches.append(
                f"reconciliation.{field}: declared {declared!r} != observed {observed_value!r}"
            )
    return mismatches


def verify_scenario(path: Path) -> None:
    scenario = load_scenario(path)
    truth_path = Path(scenario["truth_fixture"])
    if not truth_path.is_absolute():
        truth_path = ROOT / truth_path
    truth = _load_json(truth_path)
    observed = compute_observed(scenario)
    mismatches = compare_truth(truth, observed)
    if mismatches:
        detail = "\n  ".join(mismatches)
        raise TruthMismatchError(f"{scenario['scenario_id']}: truth mismatch:\n  {detail}")

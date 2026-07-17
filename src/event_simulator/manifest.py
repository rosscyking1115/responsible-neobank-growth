"""Truth-manifest construction.

Business truth (lifecycle end states, ledger totals, expected exceptions) is
carried by the injectors' explicit bookkeeping. Delivery-level counts
(duplicates, quarantine, lateness, freshness) are derived from the final
stream using the event registry — a separate implementation from the contract layer
oracle that the tests use for verification.
"""

import hashlib
import json
from collections import defaultdict
from datetime import datetime

import jsonschema

from src.event_simulator.config import SimulatorConfig
from src.event_simulator.registry import EventRegistry, UnknownEventError
from src.event_simulator.scenarios import schema_evolution
from src.event_simulator.state import GenerationTruth

_FMT = "%Y-%m-%dT%H:%M:%SZ"

PROHIBITED_INTERPRETATION = (
    "Synthetic engineering benchmark only. Volumes, rates and amounts are "
    "generated for oracle coverage and carry no information about real "
    "customers, real funnels or Monzo."
)
LIMITATIONS = (
    "Deterministic seeded generation with injected defects; no concurrency, "
    "no realistic timing distributions, no real-world calibration of failure "
    "rates. Engineering truth only (the synthetic-truth contract)."
)


def _hours(a: str, b: str) -> float:
    return (datetime.strptime(b, _FMT) - datetime.strptime(a, _FMT)).total_seconds() / 3600


def _classify(deliveries: list[dict], registry: EventRegistry) -> tuple[list[dict], list[dict]]:
    valid: list[dict] = []
    quarantined: list[dict] = []
    for event in deliveries:
        try:
            if not registry.envelope_validator.is_valid(event):
                raise jsonschema.ValidationError("invalid envelope")
            validator = registry.payload_validator(
                event["event_name"], event["schema_version"]
            )
            if not validator.is_valid(event["payload"]):
                raise jsonschema.ValidationError("invalid payload")
        except (jsonschema.ValidationError, UnknownEventError):
            quarantined.append(event)
        else:
            valid.append(event)
    return valid, quarantined


def config_hash(config: SimulatorConfig) -> str:
    data = config.as_dict()
    data["clock_start"] = config.clock_start.isoformat()
    data["clock_end"] = config.clock_end.isoformat()
    data["scenario_mix"] = dict(sorted(vars(config.scenario_mix).items()))
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_manifest(
    config: SimulatorConfig,
    deliveries: list[dict],
    truth: GenerationTruth,
    missing_postings: int,
    outage: dict | None,
) -> dict:
    registry = EventRegistry.load()
    valid, quarantined = _classify(deliveries, registry)
    unique_keys = {e["idempotency_key"] for e in valid}

    threshold_h = config.late_threshold_hours
    lookback_h = config.lookback_days * 24
    late = [e for e in valid if _hours(e["occurred_at"], e["ingested_at"]) > threshold_h]
    beyond = [e for e in late if _hours(e["occurred_at"], e["ingested_at"]) > lookback_h]

    by_event: dict[str, int] = defaultdict(int)
    for event in deliveries:
        by_event[f"{event['event_name']}:v{event['schema_version']}"] += 1

    reversed_deliveries = [e for e in deliveries if e["event_name"] == "reward-reversed"]

    exceptions = []
    if missing_postings:
        exceptions.append({"reason": "missing_posting", "count": missing_postings})

    freshness: dict = {"breached": False, "threshold_hours": None, "max_gap_hours": 0.0}
    if outage is not None:
        arrivals = sorted(e["ingested_at"] for e in deliveries)
        max_gap = max(
            (_hours(a, b) for a, b in zip(arrivals, arrivals[1:], strict=False)),
            default=0.0,
        )
        freshness = {
            "breached": max_gap > outage["threshold_hours"],
            "threshold_hours": outage["threshold_hours"],
            "max_gap_hours": round(max_gap, 4),
            "outage_start": outage["outage_start"],
            "outage_end": outage["outage_end"],
            "delayed_deliveries": outage["delayed_deliveries"],
        }

    return {
        "profile": config.profile,
        "seed": config.seed,
        "generator_version": config.generator_version,
        "config_hash": config_hash(config),
        "sub_seeds": {
            "journeys": f"{config.seed}:journeys",
            "faults": f"{config.seed}:faults",
        },
        "clock_start": config.clock_start.strftime(_FMT),
        "clock_end": config.clock_end.strftime(_FMT),
        "delivery_count": len(deliveries),
        "deliveries_by_event": dict(by_event),
        "unique_business_events": len(unique_keys),
        "expected_duplicates": len(valid) - len(unique_keys),
        "expected_quarantined": len(quarantined),
        "expected_late_arrivals": len(late),
        "expected_beyond_lookback": len(beyond),
        "expected_reversals": len(reversed_deliveries),
        "schema_evolution": schema_evolution.summarise(deliveries),
        "lifecycle_end_states": dict(sorted(truth.referral_end_states.items())),
        "reconciliation": {
            "entitled_minor": truth.entitled_minor,
            "booked_minor": truth.booked_minor,
            "settled_minor": truth.settled_minor,
            "reversed_minor": truth.reversed_minor,
            "outstanding_payable_minor": (
                truth.booked_minor - truth.settled_minor - truth.reversed_minor
            ),
            "exceptions": exceptions,
        },
        "freshness": freshness,
        "prohibited_interpretation": PROHIBITED_INTERPRETATION,
        "limitations": LIMITATIONS,
    }

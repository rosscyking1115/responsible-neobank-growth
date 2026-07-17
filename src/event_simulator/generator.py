"""Valid-lifecycle event generation.

Walks each synthetic customer through the approved funnel and emits
schema-valid events in deterministic order. Randomness comes only from seeded
``random.Random`` instances with per-domain sub-seeds;
time comes from offsets against the configured virtual window. Fault injection
(duplicates, late arrivals, reversals, malformed payloads, outages) is layered
on top by ``scenarios`` in so truth stays separable from defects.
"""

import random
from datetime import datetime, timedelta

from src.event_simulator.config import SimulatorConfig
from src.event_simulator.domains import (
    account,
    acquisition,
    campaigns,
    experiments,
    outcomes,
    referral,
    rewards,
)
from src.event_simulator.ids import DeterministicIds
from src.event_simulator.registry import EventRegistry
from src.event_simulator.state import GenerationResult, GenerationTruth


def _fmt(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class Emitter:
    """Builds envelope-complete events with deterministic identity and time."""

    def __init__(self, config: SimulatorConfig, ids: DeterministicIds, scenario_id: str):
        self.config = config
        self.ids = ids
        self.scenario_id = scenario_id
        self.registry = EventRegistry.load()
        self.events: list[dict] = []
        self.truth = GenerationTruth()
        self._sequence = 0

    def emit(
        self,
        event_name: str,
        schema_version: int,
        business_key: str,
        occurred: datetime,
        payload: dict,
        trace: str,
        ingest_delay_seconds: int = 2,
    ) -> dict:
        self._sequence += 1
        emitted = occurred + timedelta(seconds=1)
        ingested = emitted + timedelta(seconds=ingest_delay_seconds)
        source_service = self.registry.source_service(event_name)
        event = {
            "event_id": self.ids.event_id(event_name, self._sequence),
            "idempotency_key": self.ids.idempotency_key(business_key),
            "event_name": event_name,
            "source_service": source_service,
            "occurred_at": _fmt(occurred),
            "emitted_at": _fmt(emitted),
            "ingested_at": _fmt(ingested),
            "schema_version": schema_version,
            "producer_id": f"{source_service}-01",
            "trace_id": self.ids.trace_id(trace),
            "payload": payload,
            "generator_version": self.config.generator_version,
            "scenario_id": self.scenario_id,
        }
        self.events.append(event)
        self.truth.count(event_name)
        return event


def generate_valid_events(
    config: SimulatorConfig, scenario_id: str | None = None
) -> GenerationResult:
    ids = DeterministicIds(config.seed)
    emitter = Emitter(config, ids, scenario_id or f"{config.profile}-valid")

    campaigns.generate(config, emitter)

    journey_rng = random.Random(f"{config.seed}:journeys")
    window_days = (config.clock_end - config.clock_start).days
    latest_start_day = max(1, window_days - 21)

    for sequence in range(config.customers):
        start_offset = timedelta(
            days=journey_rng.uniform(0, latest_start_day),
            minutes=journey_rng.randrange(0, 24 * 60),
        )
        journey_start = config.clock_start + start_offset

        applied = acquisition.generate(config, emitter, ids, journey_rng, sequence, journey_start)
        if applied.referred:
            referral.invite(config, emitter, ids, journey_rng, applied)
        if applied.kyc_decision != "approved":
            continue

        funded_at = account.generate(config, emitter, ids, journey_rng, applied)
        experiments.generate(config, emitter, ids, journey_rng, applied)
        outcomes.generate(config, emitter, ids, journey_rng, applied)

        if applied.referred and funded_at is not None:
            qualified = referral.qualify(config, emitter, ids, journey_rng, applied, funded_at)
            if qualified:
                rewards.generate(config, emitter, ids, journey_rng, applied, funded_at)

    if len(emitter.events) > config.max_deliveries:
        raise ValueError(
            f"{config.profile} generation produced {len(emitter.events)} deliveries; "
            f"cap is {config.max_deliveries}"
        )
    emitter.events.sort(key=lambda e: (e["ingested_at"], e["event_id"]))
    return GenerationResult(events=emitter.events, truth=emitter.truth)

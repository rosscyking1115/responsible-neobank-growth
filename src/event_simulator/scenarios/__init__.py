"""Fault injection over valid lifecycles (Plan 2 section 5.5).

Faults are applied *after* valid generation so the truth manifest can
distinguish intended business state from delivery defects. Injectors mutate a
copy of the delivery stream and the business-truth aggregates explicitly; the
manifest then derives final delivery-level counts from the resulting stream.
Verification is independent: tests recompute everything with the Plan 1 oracle.
"""

import random
from dataclasses import dataclass, field, replace

from src.event_simulator.config import SimulatorConfig
from src.event_simulator.ids import DeterministicIds
from src.event_simulator.manifest import build_manifest
from src.event_simulator.scenarios import (
    duplicates,
    freshness_outage,
    late_arrivals,
    malformed,
    reconciliation_break,
    reversals,
)
from src.event_simulator.state import GenerationResult, GenerationTruth


@dataclass
class FaultedGeneration:
    deliveries: list[dict]
    manifest: dict
    truth: GenerationTruth = field(repr=False, default=None)


def _copy_events(events: list[dict]) -> list[dict]:
    return [{**event, "payload": dict(event["payload"])} for event in events]


def apply_faults(result: GenerationResult, config: SimulatorConfig) -> FaultedGeneration:
    deliveries = _copy_events(result.events)
    truth = replace(
        result.truth,
        event_counts=dict(result.truth.event_counts),
        referral_end_states=dict(result.truth.referral_end_states),
    )
    rng = random.Random(f"{config.seed}:faults")
    ids = DeterministicIds(config.seed)

    # Business-state scenarios first (they change intended truth)...
    reversed_rewards = reversals.inject(deliveries, truth, config, rng, ids)
    missing_postings = reconciliation_break.inject(
        deliveries, truth, config, rng, exclude_rewards=reversed_rewards
    )
    # ...then delivery defects (they must never change intended truth).
    duplicates.inject(deliveries, config, rng, ids)
    late_arrivals.inject(deliveries, config, rng)
    malformed.inject(deliveries, config, rng, ids)
    outage = freshness_outage.inject(deliveries, config, rng)

    deliveries.sort(key=lambda e: (e["ingested_at"], e["event_id"]))
    if len(deliveries) > config.max_deliveries:
        raise ValueError(
            f"fault injection pushed deliveries to {len(deliveries)}; "
            f"cap is {config.max_deliveries}"
        )

    manifest = build_manifest(
        config,
        deliveries,
        truth,
        missing_postings=missing_postings,
        outage=outage,
    )
    return FaultedGeneration(deliveries=deliveries, manifest=manifest, truth=truth)

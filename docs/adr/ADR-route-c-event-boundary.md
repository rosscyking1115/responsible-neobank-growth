# ADR: Route C versioned backend-event boundary

## Status

Accepted — 2026-07-17 (Plan 1, Task 2).

## Context

The current platform generates batch entity tables directly. That hides the hard
Analytics Engineering problems this project now wants to prove: late arrivals,
duplicated deliveries, corrections, reversals, malformed payloads and schema
evolution all have no representation, so no downstream model can demonstrate that it
handles them correctly. Route C replaces the batch source boundary with versioned
synthetic backend events whose truth is known exactly.

## Decision

Every synthetic backend event shares one envelope, validated against a JSON Schema
registry under `contracts/events/`:

| Field | Rule |
|---|---|
| `event_id` | globally unique immutable identifier per emitted delivery |
| `idempotency_key` | stable across delivery duplicates of one business event |
| `event_name` | version-independent business event name |
| `source_service` | fictional producer from the approved service registry |
| `occurred_at` | UTC business occurrence time |
| `emitted_at` | UTC producer emission time (not before occurrence unless a clock-skew scenario is injected) |
| `ingested_at` | UTC warehouse arrival time; may be deliberately late |
| `schema_version` | positive integer validated against the event registry |
| `producer_id` | fictional producer instance identifier |
| `trace_id` | groups a bounded business workflow |
| `payload` | JSON object validated against the named event/version schema |
| `generator_version` | exact generator release |
| `scenario_id` | links to the scenario/truth manifest |

Currency values use integer minor units. Timestamps are stored in UTC. Fictional
identifiers must not resemble real account credentials.

Compatibility policy: envelope changes are additive within a major generator version;
removing or retyping a required payload field requires a new `schema_version`;
consumers read through normalised models, never version-specific landing payloads;
v1 and v2 events coexist in at least one deterministic fixture.

## Alternatives considered

- **Route B (keep batch sources):** retained as the explicit fallback if the event
  boundary cannot reproduce core activation/referral/experiment inputs without
  inventing an unbounded bank system.
- **Kafka/streaming:** rejected — out of scope; the project proves warehouse-side
  correctness, not transport infrastructure.

## Consequences

- The hard failure modes become first-class, testable fixtures with exact truth.
- The event generator must be deterministic (seeded, virtual-clock) so truth
  manifests stay exact; wall-clock time and random identity are prohibited in
  deterministic paths.
- Existing consumers keep working through compatibility relations while the source
  boundary migrates underneath them (see ADR-route-c-four-layer-interfaces).
- Gate 0 fails if the envelope and admitted payload schemas cannot express the
  required duplicate/late/reversal/malformed/evolution scenarios.

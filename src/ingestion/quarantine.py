"""Delivery classification for ingestion.

Quarantine is evidence, not silent dropping: every invalid delivery records
identifiers where recoverable, the failing rule, a retriable classification and
the raw payload hash. A conflicting duplicate (same idempotency key, different
payload hash) is quarantined at high severity; an exact redelivery is valid
delivery evidence and deduplicates downstream, never here.
"""

import hashlib
import json
from dataclasses import dataclass

import jsonschema

from src.event_simulator.registry import EventRegistry, UnknownEventError


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Classification:
    status: str  # "valid" | "quarantined"
    error_code: str | None = None
    error_message: str | None = None
    retriable: bool = False
    severity: str | None = None


def classify(event: dict, registry: EventRegistry, keymap: dict[str, str]) -> Classification:
    """Classify one delivery against the registry and the idempotency keymap.

    ``keymap`` maps idempotency_key -> payload_hash for previously accepted
    deliveries; the caller updates it after accepting a valid delivery.
    """
    try:
        envelope_error = next(registry.envelope_validator.iter_errors(event), None)
        if envelope_error is not None:
            raise envelope_error
        validator = registry.payload_validator(event["event_name"], event["schema_version"])
        payload_error = next(validator.iter_errors(event["payload"]), None)
        if payload_error is not None:
            raise payload_error
    except UnknownEventError as unknown:
        return Classification(
            status="quarantined",
            error_code="unknown_event_version",
            error_message=str(unknown),
            retriable=False,
            severity="medium",
        )
    except jsonschema.ValidationError as invalid:
        return Classification(
            status="quarantined",
            error_code="schema_validation_failed",
            error_message=invalid.message[:500],
            retriable=False,
            severity="medium",
        )

    key = event["idempotency_key"]
    incoming_hash = payload_hash(event["payload"])
    known_hash = keymap.get(key)
    if known_hash is not None and known_hash != incoming_hash:
        return Classification(
            status="quarantined",
            error_code="conflicting_duplicate",
            error_message=(
                f"idempotency key {key} was previously accepted with a different payload hash"
            ),
            retriable=False,
            severity="high",
        )
    return Classification(status="valid")

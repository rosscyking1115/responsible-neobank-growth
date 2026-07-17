"""Event registry access for the simulator (Plan 2, Task 1).

The registry under ``contracts/events/`` is the single source of truth for
event names, versions, payload schemas and producer services. The simulator
may only emit what the registry admits.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
EVENTS_DIR = ROOT / "contracts" / "events"


class UnknownEventError(KeyError):
    """Raised for an event name or version the registry does not admit."""


@dataclass(frozen=True)
class EventRegistry:
    events: dict
    services: dict
    envelope: dict
    # Precompiled validators: compiling a Draft 2020-12 validator per event is
    # ~10x cheaper than jsonschema.validate() per delivery, which matters at
    # the standard profile's volume.
    envelope_validator: jsonschema.Draft202012Validator = field(repr=False, default=None)
    payload_validators: dict = field(repr=False, default_factory=dict)

    @classmethod
    def load(cls, events_dir: Path = EVENTS_DIR) -> "EventRegistry":
        with open(events_dir / "registry.yml", encoding="utf-8") as f:
            registry = yaml.safe_load(f)
        with open(events_dir / "event-envelope.schema.json", encoding="utf-8") as f:
            envelope = json.load(f)
        events = {}
        payload_validators = {}
        for event in registry["events"]:
            schemas = {}
            for version, relative in event["schemas"].items():
                with open(events_dir / relative, encoding="utf-8") as f:
                    schema = json.load(f)
                schemas[int(version)] = schema
                payload_validators[(event["name"], int(version))] = (
                    jsonschema.Draft202012Validator(schema)
                )
            events[event["name"]] = {
                "family": event["family"],
                "source_service": event["source_service"],
                "schemas": schemas,
            }
        services = {s["name"]: s for s in registry["services"]}
        return cls(
            events=events,
            services=services,
            envelope=envelope,
            envelope_validator=jsonschema.Draft202012Validator(envelope),
            payload_validators=payload_validators,
        )

    def payload_validator(self, event_name: str, version: int) -> jsonschema.Draft202012Validator:
        key = (event_name, version)
        if key not in self.payload_validators:
            raise UnknownEventError(f"unknown event/version: {key}")
        return self.payload_validators[key]

    def payload_schema(self, event_name: str, version: int) -> dict:
        if event_name not in self.events:
            raise UnknownEventError(f"unknown event: {event_name}")
        schemas = self.events[event_name]["schemas"]
        if version not in schemas:
            raise UnknownEventError(f"unknown version {version} for event {event_name}")
        return schemas[version]

    def source_service(self, event_name: str) -> str:
        if event_name not in self.events:
            raise UnknownEventError(f"unknown event: {event_name}")
        return self.events[event_name]["source_service"]

    def family(self, event_name: str) -> str:
        if event_name not in self.events:
            raise UnknownEventError(f"unknown event: {event_name}")
        return self.events[event_name]["family"]

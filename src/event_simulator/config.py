"""Typed, validated simulator configuration.

Profiles are locked by the synthetic-truth contract: ``tiny`` (capped at 5,000
deliveries, exact truth committed) and ``standard`` (generated on demand).
``stress`` remains deferred and is rejected here on purpose.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ALLOWED_PROFILES = {"tiny", "standard"}
TINY_DELIVERY_CAP = 5000

ADMITTED_FAMILIES = {
    "campaign_spend",
    "application_kyc_account",
    "activation_funding",
    "referral_reward",
    "experiment",
    "customer_outcome",
}


class ConfigError(ValueError):
    """Raised when a simulator configuration violates the locked contract."""


def _require_utc(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ConfigError(f"{name} must be a timezone-aware UTC timestamp")


@dataclass(frozen=True)
class ScenarioMix:
    duplicate_delivery_rate: float = 0.0
    late_arrival_rate: float = 0.0
    beyond_lookback_count: int = 0
    reversal_rate: float = 0.0
    malformed_rate: float = 0.0
    v2_share: float = 0.0
    freshness_outage: bool = False
    reconciliation_break_count: int = 0

    def __post_init__(self) -> None:
        for name in (
            "duplicate_delivery_rate",
            "late_arrival_rate",
            "reversal_rate",
            "malformed_rate",
            "v2_share",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ConfigError(f"scenario_mix.{name} must be within [0, 1]")
        if self.beyond_lookback_count < 0 or self.reconciliation_break_count < 0:
            raise ConfigError("scenario_mix counts must be non-negative")


@dataclass(frozen=True)
class SimulatorConfig:
    profile: str
    seed: int
    generator_version: str
    clock_start: datetime
    clock_end: datetime
    customers: int
    max_deliveries: int
    event_families: list[str]
    reward_amount_minor: int
    late_threshold_hours: int
    lookback_days: int
    scenario_mix: ScenarioMix = field(default_factory=ScenarioMix)

    def __post_init__(self) -> None:
        if self.profile not in ALLOWED_PROFILES:
            raise ConfigError(
                f"profile {self.profile!r} is not supported; allowed: {sorted(ALLOWED_PROFILES)}"
            )
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ConfigError("seed must be a non-negative integer")
        _require_utc(self.clock_start, "clock_start")
        _require_utc(self.clock_end, "clock_end")
        if self.clock_end <= self.clock_start:
            raise ConfigError("clock_end must be after clock_start")
        if self.customers < 1:
            raise ConfigError("customers must be positive")
        if self.max_deliveries < 1:
            raise ConfigError("max_deliveries must be positive")
        if self.profile == "tiny" and self.max_deliveries > TINY_DELIVERY_CAP:
            raise ConfigError(
                f"tiny profile is capped at {TINY_DELIVERY_CAP} deliveries "
                f"(got {self.max_deliveries})"
            )
        unknown = set(self.event_families) - ADMITTED_FAMILIES
        if unknown:
            raise ConfigError(f"unknown event family: {sorted(unknown)}")
        if self.reward_amount_minor < 1:
            raise ConfigError("reward_amount_minor must be a positive integer (minor units)")
        if self.late_threshold_hours < 1 or self.lookback_days < 1:
            raise ConfigError("late_threshold_hours and lookback_days must be positive")

    def as_dict(self) -> dict:
        data = asdict(self)
        data["scenario_mix"] = self.scenario_mix
        return data


def load_config(path: Path) -> SimulatorConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    try:
        clock = raw.pop("clock")
        mix = ScenarioMix(**raw.pop("scenario_mix", {}))
        volumes = raw.pop("volumes")
        return SimulatorConfig(
            clock_start=_parse_ts(clock["start"]),
            clock_end=_parse_ts(clock["end"]),
            customers=volumes["customers"],
            max_deliveries=volumes["max_deliveries"],
            scenario_mix=mix,
            **raw,
        )
    except KeyError as missing:
        raise ConfigError(f"configuration is missing required key: {missing}") from missing
    except TypeError as bad:
        raise ConfigError(f"configuration has an unexpected or missing field: {bad}") from bad


def _parse_ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed

"""Simulator configuration and determinism-utility tests.

Invalid seeds, naive timestamps, unsupported profiles, unknown event families
and uncontrolled wall-clock/random-identity access must fail before any
generation code exists.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.event_simulator.clock import VirtualClock
from src.event_simulator.config import ConfigError, SimulatorConfig, load_config
from src.event_simulator.ids import DeterministicIds
from src.event_simulator.registry import EventRegistry, UnknownEventError

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config" / "simulator"
SIMULATOR_SRC = ROOT / "src" / "event_simulator"


# --- profile configs ---------------------------------------------------------


def test_tiny_profile_loads_and_is_bounded() -> None:
    config = load_config(CONFIG_DIR / "tiny.yml")
    assert config.profile == "tiny"
    assert config.seed == 42
    assert config.max_deliveries <= 5000, "tiny profile is capped at 5,000 deliveries"
    assert config.clock_start.tzinfo is not None
    assert config.lookback_days == 3
    assert config.reward_amount_minor == 5000


def test_standard_profile_loads() -> None:
    config = load_config(CONFIG_DIR / "standard.yml")
    assert config.profile == "standard"
    assert config.max_deliveries == 1_000_000


def test_negative_seed_fails() -> None:
    config = load_config(CONFIG_DIR / "tiny.yml")
    with pytest.raises(ConfigError, match="seed"):
        SimulatorConfig(**{**config.as_dict(), "seed": -1})


def test_unsupported_profile_fails() -> None:
    config = load_config(CONFIG_DIR / "tiny.yml")
    with pytest.raises(ConfigError, match="profile"):
        SimulatorConfig(**{**config.as_dict(), "profile": "stress"})


def test_unknown_event_family_fails() -> None:
    config = load_config(CONFIG_DIR / "tiny.yml")
    families = [*config.event_families, "card_authorisation"]
    with pytest.raises(ConfigError, match="family"):
        SimulatorConfig(**{**config.as_dict(), "event_families": families})


def test_naive_clock_start_fails() -> None:
    config = load_config(CONFIG_DIR / "tiny.yml")
    with pytest.raises(ConfigError, match="UTC"):
        SimulatorConfig(
            **{**config.as_dict(), "clock_start": datetime(2026, 1, 1)}  # noqa: DTZ001
        )


def test_clock_end_before_start_fails() -> None:
    config = load_config(CONFIG_DIR / "tiny.yml")
    with pytest.raises(ConfigError, match="end"):
        SimulatorConfig(
            **{**config.as_dict(), "clock_end": config.clock_start - timedelta(days=1)}
        )


def test_tiny_over_delivery_cap_fails() -> None:
    config = load_config(CONFIG_DIR / "tiny.yml")
    with pytest.raises(ConfigError, match="5,?000|5000"):
        SimulatorConfig(**{**config.as_dict(), "max_deliveries": 6000})


# --- virtual clock -----------------------------------------------------------


def test_virtual_clock_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="UTC"):
        VirtualClock(datetime(2026, 1, 1))  # noqa: DTZ001


def test_virtual_clock_is_deterministic() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    clock = VirtualClock(start)
    assert clock.now() == start
    clock.advance(timedelta(hours=2))
    assert clock.now() == start + timedelta(hours=2)
    with pytest.raises(ValueError, match="backward"):
        clock.advance(timedelta(hours=-1))


# --- deterministic identities -------------------------------------------------


def test_ids_are_deterministic_and_pattern_conformant() -> None:
    ids_a = DeterministicIds(seed=42)
    ids_b = DeterministicIds(seed=42)
    assert ids_a.customer_id(1) == ids_b.customer_id(1)
    assert ids_a.customer_id(1) != ids_a.customer_id(2)
    assert ids_a.customer_id(1).startswith("cus_")
    assert ids_a.event_id("referral-qualified", 7).startswith("evt_")
    assert DeterministicIds(seed=43).customer_id(1) != ids_a.customer_id(1)


# --- no uncontrolled wall clock or randomness --------------------------------


def test_no_wall_clock_or_random_identity_in_simulator_source() -> None:
    forbidden = ["datetime.now(", "datetime.utcnow(", "time.time(", "uuid4", "random.random("]
    offenders = []
    for path in SIMULATOR_SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                offenders.append(f"{path.name}: {marker}")
    assert offenders == [], f"uncontrolled time/randomness in deterministic paths: {offenders}"


# --- CLI skeleton -------------------------------------------------------------


def test_cli_validate_accepts_known_profiles_and_rejects_unknown() -> None:
    from src.event_simulator.cli import main

    assert main(["validate", "--profile", "tiny"]) == 0
    assert main(["validate", "--profile", "stress"]) == 2


def test_cli_generate_rejects_unknown_profile() -> None:
    from src.event_simulator.cli import main

    assert main(["generate", "--profile", "stress", "--output", "data/generated/x"]) == 2


# --- registry ----------------------------------------------------------------


def test_registry_loads_and_validates() -> None:
    registry = EventRegistry.load()
    schema = registry.payload_schema("referral-qualified", 2)
    assert schema["title"].startswith("referral-qualified v2")
    assert registry.source_service("reward-booked") == "rewards-service"


def test_registry_unknown_event_or_version_fails() -> None:
    registry = EventRegistry.load()
    with pytest.raises(UnknownEventError):
        registry.payload_schema("card-transaction-authorised", 1)
    with pytest.raises(UnknownEventError):
        registry.payload_schema("referral-qualified", 99)

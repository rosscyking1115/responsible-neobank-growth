"""Simulator CLI (Plan 2). Task 1 ships the skeleton: ``validate`` works;
``generate`` lands with the domain lifecycles and writers (Tasks 2–4)."""

import argparse
import sys
from pathlib import Path

from src.event_simulator.config import ConfigError, load_config

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config" / "simulator"


def _config_path(profile: str) -> Path:
    return CONFIG_DIR / f"{profile}.yml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="event_simulator", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="validate a profile configuration")
    validate.add_argument("--profile", required=True)

    generate = subcommands.add_parser("generate", help="generate a deterministic event set")
    generate.add_argument("--profile", required=True)
    generate.add_argument("--output", required=True, type=Path)

    args = parser.parse_args(argv)

    try:
        config = load_config(_config_path(args.profile))
    except FileNotFoundError:
        print(f"error: no configuration for profile {args.profile!r}", file=sys.stderr)
        return 2
    except ConfigError as invalid:
        print(f"error: invalid configuration: {invalid}", file=sys.stderr)
        return 2

    if args.command == "validate":
        print(
            f"{config.profile}: seed={config.seed} customers={config.customers} "
            f"max_deliveries={config.max_deliveries} "
            f"window={config.clock_start.isoformat()}..{config.clock_end.isoformat()}"
        )
        return 0

    print(
        "error: generation is not implemented yet (Plan 2 Tasks 2-4); "
        "configuration validated successfully",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

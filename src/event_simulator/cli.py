"""Simulator CLI (Plan 2, Tasks 1 and 4).

``validate`` checks a profile configuration; ``generate`` produces the
deterministic delivery batches and truth manifest; ``compare`` verifies two
outputs by logical content, never file timestamps.
"""

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

    compare = subcommands.add_parser("compare", help="compare two generated outputs logically")
    compare.add_argument("--left", required=True, type=Path)
    compare.add_argument("--right", required=True, type=Path)

    args = parser.parse_args(argv)

    if args.command == "compare":
        from src.event_simulator.writers import compare_outputs

        differences = compare_outputs(args.left, args.right)
        for difference in differences:
            print(f"difference: {difference}", file=sys.stderr)
        if not differences:
            print("outputs are logically identical")
        return 1 if differences else 0

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

    from src.event_simulator.generator import generate_valid_events
    from src.event_simulator.scenarios import apply_faults
    from src.event_simulator.writers import write_output

    faulted = apply_faults(generate_valid_events(config), config)
    summary = write_output(faulted, config, args.output)
    print(
        f"{config.profile}: wrote {summary['deliveries']} deliveries in "
        f"{summary['batches']} batches to {args.output} "
        f"(logical checksum {summary['logical_checksum'][:16]}…)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

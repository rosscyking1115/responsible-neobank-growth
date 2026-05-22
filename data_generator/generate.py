"""Entry point for the synthetic neobank event generator."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date
from pathlib import Path

import polars as pl

from data_generator.config import GeneratorConfig
from data_generator.experiments import assign_onboarding_experiment, experiment_ground_truth
from data_generator.features import generate_feature_usage
from data_generator.referrals import generate_referrals
from data_generator.sessions import generate_sessions
from data_generator.support import generate_support_contacts
from data_generator.transactions import generate_transactions
from data_generator.users import generate_users
from data_generator.utils import ensure_output_dir, write_parquet


def build_dataset(config: GeneratorConfig) -> dict[str, pl.DataFrame]:
    users = generate_users(config)
    experiments = assign_onboarding_experiment(users, config)
    transactions, activation = generate_transactions(users, experiments, config)
    sessions = generate_sessions(users, activation, config)
    features = generate_feature_usage(users, activation, config)
    support_contacts = generate_support_contacts(users, config)
    referrals, region_daily_signups = generate_referrals(users, activation, config)
    ground_truth = experiment_ground_truth(config)

    return {
        "users": users,
        "experiment_assignments": experiments,
        "activation_ground_truth": activation,
        "transactions": transactions,
        "sessions": sessions,
        "feature_events": features,
        "support_contacts": support_contacts,
        "referrals": referrals,
        "region_daily_signups": region_daily_signups,
        "experiment_ground_truth": ground_truth,
    }


def write_dataset(frames: dict[str, pl.DataFrame], output_dir: Path) -> None:
    ensure_output_dir(output_dir)
    for name, frame in frames.items():
        write_parquet(frame, output_dir, name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic neobank event data.")
    parser.add_argument("--users", type=int, default=50_000)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("raw"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = GeneratorConfig(
        users=args.users,
        months=args.months,
        start_date=args.start_date,
        seed=args.seed,
    )
    frames = build_dataset(config)
    write_dataset(frames, args.output_dir)
    print(f"Wrote {len(frames)} parquet files to {args.output_dir.resolve()}")
    for name, frame in frames.items():
        print(f"- {name}: {frame.height:,} rows")
    print(f"Config: {asdict(config)}")


if __name__ == "__main__":
    main()

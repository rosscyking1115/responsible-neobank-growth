# Synthetic Data Generator

The Phase 1 generator creates a reproducible synthetic neobank event stream with
known causal ground truth for later experimentation chapters.

## Outputs

- `users.parquet`: signup cohorts, region, channel, device, income segment, and
  customer-outcome flags.
- `experiment_assignments.parquet`: deterministic 50/50 onboarding experiment
  assignment with embedded D7 activation lift.
- `activation_ground_truth.parquet`: generated activation outcomes used to verify
  the experiment chapter.
- `transactions.parquet`: card transactions with heavy-tailed amounts and merchant
  categories.
- `sessions.parquet`: app-session events with duration and crash guardrail.
- `feature_events.parquet`: product adoption events for pots, savings, salary
  sorter, and referrals.
- `support_contacts.parquet`: support, complaint, and vulnerable-customer guardrail
  events.
- `referrals.parquet`: referral graph with regional incentive treatment and
  incrementality ground truth.
- `region_daily_signups.parquet`: region-day panel for DiD and synthetic control.
- `experiment_ground_truth.parquet`: true causal parameters embedded in the data.

## Run

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --output-dir raw/phase1_full
```

The generator is intentionally deterministic for a fixed seed. Tests cover output
presence, deterministic assignment, and basic business invariants.

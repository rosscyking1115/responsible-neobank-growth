---
title: Readme
marimo-version: 0.23.7
---

# Notebooks

Marimo notebooks will live here as `.py` files so analytical work stays
reactive, reproducible, and reviewable in Git.

## Available notebooks

- `01_eda_activation_drivers.py`: product EDA over the dbt metrics layer,
  answering five activation, retention, feature-adoption, acquisition, and churn
  questions.

Run with:

```powershell
uv run python -m data_generator.generate --users 50000 --months 12 --seed 42 --output-dir raw/phase1_full
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --vars "{raw_path: raw/phase1_full}"
uv run marimo edit notebooks/01_eda_activation_drivers.py
```
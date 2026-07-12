# Real-Data Cross-Check — Criteo Uplift (experimentation)

The platform's fairness analysis is cross-checked on real data via the
[UCI adapter](REAL_DATA_ADAPTER.md). This adapter does the same for the **experimentation**
chapter: it runs the platform's *own* A/B estimators on a **real randomised experiment**.

## The dataset

**Criteo Uplift** (Diemert, Betlei, Renaudin & Amini, 2018) — ~13M rows from a real
randomised advertising experiment. Columns: `treatment` (exposed vs held out),
`conversion` / `visit` (binary outcomes), `exposure`, and 12 anonymised dense user
features `f0`..`f11`.

- Source: <https://ailab.criteo.com/criteo-uplift-prediction-dataset/> (cite Diemert et al. 2018).
- The file is large; the adapter reads a slice (`--sample-rows`, default 1,000,000) so it
  runs on a laptop.

## Honest boundary — read this first

This is **ad-tech, not fintech**, and — unlike the synthetic geo / onboarding chapters —
there is **no known ground-truth lift** to recover. So this cross-check validates that the
estimators *behave correctly on real randomised data* (a sensible effect, CUPED variance
reduction, a clean SRM); it does **not** validate *recovery of a true effect*. Recovering a
known truth is exactly what the synthetic synthetic-control chapter is for, and is a core
reason the platform's centrepiece stays synthetic. See [CREDIBILITY.md](CREDIBILITY.md).

The CUPED covariate is one of the anonymised **pre-randomisation** features `f0`..`f11`
(auto-selected as the most outcome-correlated). CUPED stays unbiased for any pre-treatment
covariate, so this improves variance reduction without biasing the estimated effect — but
note it is a feature proxy, not an observed pre-period metric like the synthetic chapter uses.

## Where it lives

| Concern | Location |
| --- | --- |
| Adapter (load + Welch + CUPED + SRM) | [`src/adapters/criteo_uplift.py`](../src/adapters/criteo_uplift.py) |
| Tests (offline fixture) | [`tests/test_criteo_adapter.py`](../tests/test_criteo_adapter.py) |

It **reuses `src.experiments.analysis`** — `difference_in_means`, `cuped_adjusted_effect`,
and `sample_ratio_mismatch` — the identical estimators the synthetic A/B chapter uses, so the
experiment methodology is the same across real and synthetic data.

## Run it

```powershell
# after downloading criteo-uplift-v2.1.csv
uv run python -m src.adapters.criteo_uplift --csv path/to/criteo-uplift-v2.1.csv
# options: --metric conversion|visit  --covariate auto|f0..f11  --sample-rows N (0 = full file)
```

The readout prints an SRM check, a Welch difference-in-means, the CUPED-adjusted estimate,
and the CUPED variance reduction — all carrying the ad-tech / no-ground-truth caveat above.

## Boundary

This analyses *aggregate treatment effects* on a public, consented research dataset. It makes
no individual inferences and uses no customer PII.

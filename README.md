# Responsible Neobank Growth — Analytics Engineering Platform

[![CI](https://github.com/rosscyking1115/responsible-neobank-growth/actions/workflows/ci.yml/badge.svg)](https://github.com/rosscyking1115/responsible-neobank-growth/actions/workflows/ci.yml)
[![Monitoring Snapshot](https://github.com/rosscyking1115/responsible-neobank-growth/actions/workflows/monitoring-snapshot.yml/badge.svg)](https://github.com/rosscyking1115/responsible-neobank-growth/actions/workflows/monitoring-snapshot.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Live dashboard](https://img.shields.io/badge/demo-Streamlit-ff4b4b)](https://neobank-appuct-analytics.streamlit.app/)

A governed **event-to-interface Analytics Engineering platform** on synthetic
neobank data: deterministic, versioned, failure-injected service events flow
through a four-layer dbt warehouse into governed Growth and referral-reward
interfaces that downstream analytics, a referral-reward subledger, and a
decision-support app consume. It exists to show, end to end, how a data team
turns duplicated, late, reversed and schema-evolving backend events into
trusted interfaces — and to prove an incremental warehouse produces the same
truth at a measured cost.

> A reference project built entirely on **synthetic** data. **No affiliation**
> with Monzo or any bank; no real customer, internal, or proprietary data is
> used. Monzo's public engineering writing informed the problem framing, not
> any internal implementation. See [Safety & ethics](#safety--ethics).

**Achieved-evidence status** (every figure traces to
[`evidence/registry.yml`](evidence/registry.yml)):

- the four-layer warehouse **executed on BigQuery** under a preflight-approved,
  capped budget (a dated benchmark run, not production operation);
- full-refresh and incremental lineages reached **exact parity** at every
  governed interface across base, delta and repair phases;
- the benchmark **measured** bytes, runtime, slot use and cost — a mixed result,
  reported as measured (see [Benchmark](#bigquery-benchmark-executed));
- a complete LookML project is **authored/configured, not validated** — the
  Looker trial was access-limited, so no Looker execution is claimed anywhere.

## Why synthetic event truth

In most analytics demos the source data is clean and growth is the only goal.
Neither holds in a real neobank. Backend events arrive late, duplicated,
corrected, reversed and with evolving schemas; and in financial services a bad
growth decision can push a vulnerable customer toward a worse outcome. This
project builds a source of events whose **truth is known exactly** — every
duplicate, late arrival, reversal, malformed payload and reconciliation break
is injected against a manifest — so the warehouse's correctness can be
*checked*, not asserted. That known truth is what makes the incremental-vs-full
cost comparison and the reward reconciliation meaningful.

## Architecture

```text
Synthetic service events        (campaign, application/KYC, activation/funding,
  (versioned envelope)           referral/reward, experiment, customer-outcome)
        |
        v
Immutable delivery batches + quarantine     (append-only; evidence, not dropping)
        |
        v
Landing (lnd_*)  ->  Normalised (nrm_*)  ->  Logical / governed interfaces (lgl_*)
        |                 |                          |
        |            SCD2 / current state           v
        |                                    Presentation (prs_*)
        |                                          |
        |                          +---------------+----------------+
        |                          v               v                v
        |                     Looker (LookML   Streamlit /      ML features /
        |                     authored)        decision app     scoring
        v
Truth manifest  ->  correctness + reward-reconciliation oracle
BigQuery job metadata  ->  warehouse-health interface
```

Only normalised and logical models become governed interfaces; presentation
models are replaceable consumers. Existing analytics reach the new interfaces
through compatibility relations, so nothing that was validated is discarded.
See [docs/adr/](docs/adr/README.md) for the architecture decisions and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full local and cloud view.

## Verified results

Every claim below resolves to a record in
[`evidence/registry.yml`](evidence/registry.yml); the public-claim audit
(`tools/release/claim_audit.py`) fails CI on any unanchored number.

| Result | Evidence |
|---|---|
| Standard profile: 568,789 deliveries / 356 batches, deterministic (identical checksums across two runs) | [phase manifest](artifacts/plan3/phase-manifest.json) |
| BigQuery run: 68 dbt models + 215 data tests green (supersedes the historical 13-table/107-check record) | [current-graph summary](artifacts/plan3/current-graph/summary.json) |
| Full vs incremental: **exact parity** at all six governed interfaces (base/delta/repair) | [base](artifacts/plan3/base-parity.json) · [delta](artifacts/plan3/delta-parity.json) · [repair](artifacts/plan3/repair-parity.json) |
| Cost (measured, mixed): incremental billed **+1.95% bytes** but used **−62.7% compute**; partitioning cut one query's scan **523.9×** | [benchmark summary](artifacts/plan3/benchmark-summary.json) · [results CSV](artifacts/plan3/warehouse-cost-results.csv) |
| Late-event recovery: held-back day missed by lookback, recovered by bounded backfill; two staleness defects found and fixed at scale | [run record](artifacts/plan3/run-record.md) |
| Reward reconciliation: debits = credits, opening + movements = closing, every injected exception detected | [execution oracle](tests/oracles/test_reward_reconciliation_execution.py) |
| Local suite reproducible from a clean clone with no cloud credentials | [reproducibility](artifacts/plan4/reproducibility.md) |
| Spend: 844 jobs, 32.99 GB billed ≈ £0.21 (likely £0 under the free tier) vs a £10 approved ceiling | [run record](artifacts/plan3/run-record.md) |

## Quick start (local, no cloud account)

**Prerequisites:** Python 3.12+ and [`uv`](https://docs.astral.sh/uv/). The
entire local platform runs on DuckDB.

Inspect the committed `tiny` truth fixtures and reproduce them:

```powershell
uv sync --group dev
uv run python -m src.event_simulator.cli generate --profile tiny --output data/generated/tiny-a
uv run python -m src.event_simulator.cli generate --profile tiny --output data/generated/tiny-b
uv run python -m src.event_simulator.cli compare --left data/generated/tiny-a --right data/generated/tiny-b
```

Run the full local proof end to end (generation, ingestion, dbt build,
standards, blue/green parity, tests):

```powershell
uv run python -m tools.ci.verify_plan2
```

## Governed interfaces

Each interface answers one stakeholder question and has one authoritative grain
and owner ([`docs/metrics/metric-ownership.yml`](docs/metrics/metric-ownership.yml)):

| Interface | Question | Owner |
|---|---|---|
| `growth_acquisition` | Where do applicants progress or drop between application, approval and funded activation? | Growth |
| `referral_economics` | Do referrals create incremental activated customers at sustainable reward cost? | Growth / Finance |
| `reward_reconciliation` | Which expected rewards are missing, duplicated, mismatched, stale or wrongly reversed? | Finance |
| `warehouse_health` | Which interfaces are stale, failing, expensive or slower than baseline? | Platform |

Contracts: [`contracts/interfaces/`](contracts/interfaces/); standards are
enforced against the real dbt manifest (`tools/standards/check_dbt_interfaces.py`).

## BigQuery benchmark (executed)

The benchmark compares, on an identical final event state, rebuilding all
history after a fixed new-event batch against processing that batch plus the
frozen lookback. Phases (Base/Delta/Repair, 90/9/1 by ingestion) were
registered before any output was inspected. **Result, reported as measured:**
on the 569k-delivery run, incremental processing billed +1.95% more bytes than
a full rebuild while using 62.7% less compute (median slot-ms). The byte parity
is expected — the raw event store is unpartitioned, so every strategy scans the
full landing view; the physical-design ablation shows where byte savings live
(523.9× fewer bytes on partitioned storage for the same query). No result is
extrapolated to production or Monzo scale. Method and absolute values:
[docs/case-study/analytics-engineering-case-study.md](docs/case-study/analytics-engineering-case-study.md).

## Looker (authored, not validated)

A complete LookML project — model, four Explores, three dashboards, Assert
tests — is authored against the governed BigQuery interfaces in
[`looker/`](looker/README.md). It has **not** been validated in a Looker
instance: the trial signup returned a sales-contact outcome with no instance
provisioned, so **no Looker experience or validated LookML is claimed**. If a
genuine no-cost trial is provisioned before the resource cleanup deadline, the
validators run and the record is upgraded by dated addendum
([Plan 3 decision](docs/adr/ADR-route-c-plan3-decision.md)).

## Downstream consumers (responsible-growth methodology)

The project's data-science methodology is preserved as **consumers of the
governed interfaces**, reached through compatibility relations rather than
rewritten:

- **Experimentation** — CUPED, SRM, heterogeneous effects, DiD with clustered
  standard errors, parallel-trends, placebo-in-space and synthetic control; the
  Welch/CUPED/SRM estimators run unchanged on the governed
  `growth_acquisition` data ([worked decision](docs/WORKED_DECISION_ONBOARDING_AB.md)).
- **Responsible release-gate engine** — evidence + customer-outcome guardrails
  resolve to `ship / limited_rollout / experiment_only / needs_human_review /
  block`, where a harm signal overrides commercial uplift
  ([framework](docs/RELEASE_DECISION_FRAMEWORK.md)).
- **Fairness, wellbeing, inclusion and protection** modules, and a fair-value
  pricing governance check, over synthetic proxies with executable use
  boundaries and RBAC ([access control](docs/ACCESS_CONTROL.md)).
- **Activation model + FastAPI service** — calibrated scoring served from the
  governed feature interface.
- **Real-data cross-checks** — the same estimators re-run on real public data
  (UCI Bank Marketing, Criteo Uplift) as method validation
  ([UCI](docs/REAL_DATA_ADAPTER.md) · [Criteo](docs/REAL_DATA_CRITEO.md)).

These are surfaced in the Streamlit decision app (seven tabs).

![Responsible Neobank Growth Platform dashboard](docs/assets/streamlit-product-health.png)

## Synthetic-data validation and limitations

Results are one of three kinds, kept distinct in
[docs/CREDIBILITY.md](docs/CREDIBILITY.md):

- **engineering truth** — exact outcomes known from the generator's manifest
  (event, duplicate, quarantine, ledger and exception counts);
- **analytical method validation** — causal/statistical recovery against seeded
  truth and the two real-data adapters;
- **illustrative business magnitude** — activation rates, £CLV and fairness-gap
  sizes are *not* evidence about real customers.

The synthetic data is engineered for oracle coverage, not calibrated to any
real bank; the non-circularity guarantee (generation and analysis are separate)
is tested (`tests/test_no_circularity.py`).

## Technology stack

| Layer | Tools |
|---|---|
| Language / runtime | Python 3.12+, `uv` |
| Event simulator | seeded generators, virtual clock, JSON Schema contracts |
| Ingestion | append-only Parquet, checksum-gated batch registry, quarantine |
| Analytics engineering | dbt (four layers, incremental, contracts, unit tests), DuckDB local / BigQuery |
| Semantic / BI | LookML (authored), Streamlit decision app |
| Experimentation | CUPED, SRM, DiD, synthetic control (`scipy`, `statsmodels`, `linearmodels`) |
| Modelling | `scikit-learn`, isotonic calibration, model card, batch scoring |
| Application | Streamlit dashboard, FastAPI service |
| Quality | `pytest`, `ruff`, GitHub Actions, standards-as-code |

## Repository map

```text
contracts/        event/interface/scenario JSON-Schema + YAML contracts
src/
  event_simulator/  deterministic generator (domains, scenarios, writers)
  ingestion/        append-only loader + quarantine
  experiments/ modelling/ wellbeing/ inclusion/ release_decisions/ protection/  downstream consumers
  adapters/         real-data method-validation adapters
dbt_neobank/      four-layer warehouse (landing/normalised/logical/presentation/compatibility)
looker/           LookML project (authored)
tools/            standards, reconciliation harness, cloud runner, release audit
docs/             architecture, ADRs, contracts, case study, module docs
evidence/         claim registry (source of every public number)
artifacts/        dated baseline / gate0 / plan2 / plan3 / plan4 evidence
tests/            pytest suite
```

Deeper documentation: [docs/adr/](docs/adr/README.md) ·
[docs/CREDIBILITY.md](docs/CREDIBILITY.md) ·
[docs/case-study/analytics-engineering-case-study.md](docs/case-study/analytics-engineering-case-study.md) ·
[docs/GCP_WAREHOUSE.md](docs/GCP_WAREHOUSE.md) ·
[docs/CLOUD_RUN_DEPLOYMENT.md](docs/CLOUD_RUN_DEPLOYMENT.md).

## Safety & ethics

This project uses **synthetic data** and is **not** a production banking, fraud,
credit, eligibility, or financial-advice system, and **not affiliated** with
Monzo or any bank. Vulnerability, wellbeing and inclusion fields are synthetic
proxies for evaluating product decisions and must not be used to deny services,
set prices unfairly, determine creditworthiness, or make punitive decisions.
The customer-protection module is a supportive-intervention simulation, not a
fraud engine.

## Licence and citation

Released under the [MIT License](LICENSE) © 2026 Cheng-Yuan King. This is an
independent synthetic reference project; if you cite it, please cite the
repository and commit. No affiliation with Monzo Bank Ltd is claimed or implied.

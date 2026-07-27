# Public launch pack

How to post this project publicly, or point a CV or application at it, without
overstating what it is.

The copy below is deliberately conservative. Everything in it is checkable from
this repository, and the wording matches
[the README](README.md) and [docs/CREDIBILITY.md](docs/CREDIBILITY.md). If you
edit one, edit the others.

## The one rule

**Never describe the cloud work as running infrastructure.** There is no standing
API, no scheduled job, no live warehouse, no alerting. What exists is:

- nine plan-renderer modules (`src/cloud/*_plan.py`) that emit checked deployment
  commands from a versioned manifest, unit-tested;
- Cloud Build configs (`cloudbuild.api.yaml`, `cloudbuild.jobs.yaml`) and two
  Dockerfiles, both images built in CI;
- **one dated BigQuery benchmark run** under a small capped budget.

Say "deployment plans and one dated benchmark run", not "Cloud Run API,
scheduled jobs and monitoring alerts". The word *production-grade* is not used
about this project.

## Project identity

Use this name everywhere:

```text
Responsible Neobank Growth — Analytics Engineering Platform
```

The repository, the dashboard and every published link use the slug
`responsible-neobank-growth`. Older material called this "Customer Growth &
Pricing Intelligence Platform"; that name is retired. Do not reuse it.

## GitHub summary

Repository description:

```text
Synthetic neobank event platform whose backend events misbehave on purpose — late, duplicated, reversed, schema-evolving — and a governed four-layer dbt warehouse that turns them into trusted Growth and referral-reward interfaces, checked against a known-truth manifest.
```

Suggested topics:

```text
analytics-engineering, data-engineering, dbt, duckdb, bigquery, data-quality,
data-contracts, streamlit, fastapi, experimentation, causal-inference, python, sql
```

## LinkedIn post

```text
I built a synthetic neobank whose backend events misbehave on purpose — late, duplicated, reversed, schema-evolving — and a governed dbt warehouse that turns them into trusted Growth and referral-reward interfaces.

The point is that the events are generated against a known-truth manifest. Every duplicate, late arrival, reversal, malformed payload and missing posting is injected deliberately, so the warehouse's correctness can be checked rather than asserted.

What's actually in it:
- A four-layer dbt warehouse (landing → normalised → logical → presentation), 68 models, running locally on DuckDB.
- Governance that runs: a standards checker fails CI when a governed model omits an owner, grain, unique key, freshness SLO or declared consumers — checked against the real dbt manifest, with deliberately-invalid fixtures proving each rule catches its violation.
- A blue/green harness asserting full-refresh and incremental builds produce identical output at all six governed interfaces, with no tolerance on keys or financial values.
- History models rebuilt from business occurrence time, never ingestion time, so a replayed delivery can't rewrite when something happened.
- Experimentation and causal work (CUPED, SRM, DiD, synthetic control) as consumers of the governed interfaces, cross-checked on two real public datasets.

And an honest cost benchmark, which I report as measured because it partly contradicts what I expected: on 569k deliveries, incremental billed 1.95% MORE bytes than a full rebuild, while using 62.7% LESS compute. The raw event store is unpartitioned, so every strategy scans the whole landing view. The ablation shows where byte savings actually come from — the same query scanned 523.9x fewer bytes on partitioned storage.

All data is synthetic. No affiliation with any bank. The cloud side is deployment-plan modules and one dated BigQuery benchmark run, not standing infrastructure.

Repo: https://github.com/rosscyking1115/responsible-neobank-growth
Dashboard: https://responsible-neobank-growth.streamlit.app/
```

Shorter version:

```text
I built a synthetic neobank whose events misbehave on purpose — late, duplicated, reversed, schema-evolving — and a governed four-layer dbt warehouse that turns them into trusted Growth and referral interfaces.

Because the events are generated against a known-truth manifest, correctness is checked rather than asserted: a standards checker enforces interface rules against the real dbt manifest in CI, and a blue/green harness proves full-refresh and incremental builds agree exactly at all six governed interfaces.

The cost benchmark came out mixed and I report it that way — incremental billed +1.95% bytes but used −62.7% compute, because the raw store is unpartitioned.

All data is synthetic; no affiliation with any bank.

Repo: https://github.com/rosscyking1115/responsible-neobank-growth
Dashboard: https://responsible-neobank-growth.streamlit.app/
```

## CV bullet

```text
Built a synthetic neobank analytics-engineering platform (Python, SQL, dbt, DuckDB, BigQuery, Streamlit, FastAPI): generated deliberately-malformed event streams against a known-truth manifest, modelled them in a governed four-layer dbt warehouse, and enforced interface standards as code against the real dbt manifest in CI; proved full-refresh and incremental builds agree exactly at all six governed interfaces, and benchmarked their cost on BigQuery.
```

Shorter CV version:

```text
Built a governed four-layer dbt/DuckDB warehouse over deliberately-malformed synthetic neobank events generated against a known-truth manifest, with standards-as-code enforced in CI, blue/green full-vs-incremental reconciliation, and a measured BigQuery cost benchmark.
```

## Numbers you may quote

Measured on 2026-07-26 at the current working tree. Re-measure before reusing.

| Claim | Value | How to reproduce |
|---|---|---|
| pytest suite | 400 passed, 0 failed, 0 skipped | `uv run pytest` |
| dbt build | `PASS=289` (68 models, 217 data tests, 4 unit tests) plus 4 exposures as NO-OP | `uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank --target dev` |
| Standard profile | 568,789 deliveries in 356 batches, identical checksum across two runs | `cli generate` ×2 + `cli compare` |
| Governed interfaces reconciled | 6, exact match full vs incremental | `tools/reconcile/compare_interfaces.py` |
| Cost benchmark | incremental +1.95% bytes, −62.7% compute; partitioning cut one query's scan 523.9× | dated BigQuery run |

Quote the cost result **with both halves**. The byte figure going the wrong way
is the most credible thing in the project; reporting only the compute win would
be dishonest and a good interviewer will find it.

## The honesty boundary

State this whenever the project is presented:

- The core data is **synthetic**, generated against a known-truth manifest.
- Method validation additionally runs on **two real public datasets** — UCI Bank
  Marketing and Criteo Uplift.
- Results split three ways and the split is kept visible: **engineering truth**
  (exact outcomes from the manifest), **method validation** (recovery against
  seeded truth and the two real adapters), and **illustrative magnitude**
  (activation rates, £CLV, fairness-gap sizes — not evidence about real
  customers).

Never quote an illustrative-magnitude figure as real-world performance. Never
imply affiliation with Monzo or any bank.

## Demo script

1. Open the README and say up front that the data is synthetic and the events
   are broken on purpose against a known-truth manifest.
2. Show why known truth matters — correctness can be checked, not asserted.
3. Open `tools/standards/rules.yml` and the fixtures in
   `tests/standards/fixtures/`: the rules run against the real manifest in CI,
   and the invalid fixtures prove each rule fails when violated.
4. Show the blue/green harness: full-refresh and incremental agree exactly at all
   six governed interfaces.
5. Show a history model (`nrm_account_history.sql`) and point out the ordering is
   business occurrence time, never ingestion time.
6. Open the dashboard and walk two or three of its seven tabs — Product health,
   Customer outcomes, Monitoring.
7. Close on the cost benchmark, including the byte result that went against the
   thesis, and say plainly that the cloud side is deployment plans plus one dated
   benchmark run.

## Screenshot checklist

- README first viewport: title, live link, dashboard screenshot.
- Streamlit Product health tab, top metrics and first charts
  (`docs/assets/streamlit-product-health.png`).
- Streamlit Customer outcomes tab showing the release verdict.
- Streamlit Monitoring tab.
- A passing GitHub Actions CI run.
- dbt docs lineage for the governed `lgl_` models.

Do **not** screenshot a Cloud Run or Cloud Monitoring console as if it were this
project's running infrastructure.

## Pre-post checklist

- Project name is "Responsible Neobank Growth", not the retired one.
- No claim of standing cloud infrastructure anywhere in the copy.
- The word "production-grade" does not appear.
- Every number re-measured, or the measurement date stated.
- The cost result is quoted with both the byte and compute halves.
- Synthetic-data statement present.
- README and dashboard links resolve.
- CI badge is green.

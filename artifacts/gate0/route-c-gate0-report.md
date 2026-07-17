# Route C — Gate 0 Report

> **Date:** 2026-07-17 · **Branch:** `feat/route-c-plan1-gate0` (10 commits on
> baseline `9d680ab`) · **Decision:** **go** (pending user acceptance)
> Machine-readable results: [route-c-gate0-results.json](route-c-gate0-results.json)

## Question Gate 0 answered

> Can the existing project be migrated to a versioned backend-event boundary and
> governed four-layer warehouse without destroying its valid Growth evidence,
> duplicating business logic, or expanding into a general banking simulator?

**Yes.** All eight mandatory gates pass with repository evidence; the migration
inventory shows a compatibility route for every validated capability; the tiny
truth fixtures prove the contracts express the difficult cases; and no cloud,
Looker or public-release action occurred.

## Final verification (this branch, clean run)

| Check | Result | Evidence |
|---|---|---|
| `uv run ruff check .` | All checks passed | `artifacts/gate0/final-ruff.txt` |
| `uv run pytest` | 345 passed (217 baseline + 128 new contract/oracle/standards/readiness tests) | `artifacts/gate0/final-pytest.txt` |
| `uv run dbt build … --target dev` | PASS=133 WARN=0 ERROR=0 | `artifacts/gate0/final-dbt-build.txt` |
| `git diff --check` | clean | — |

## Gate summary

| Gate | Result | Highlights |
|---|---|---|
| G0.1 Baseline integrity | pass | Baseline reproduced exactly (217 tests, 133 dbt checks, 16 raw tables); claims inventoried; historical BigQuery evidence stays labelled historical |
| G0.2 Scope control | pass | 12 events across the 6 locked families; Finance bounded to referral rewards; scope tests enforce exclusions |
| G0.3 Contract expressiveness | pass | Envelope + 13 payload schemas; v1/v2 coexistence fixture; 9 scenarios with independently recomputed exact truth |
| G0.4 Migration preservation | pass | 50-row inventory, zero unclassified; anchor consumer = Experiments tab via `growth_acquisition` |
| G0.5 Interface governance | pass | 4 manifests validate; 19 metrics each with one authoritative owner; standards checker fails all invalid fixtures |
| G0.6 Reliability oracle | pass | Oracle detects dropped-late, duplicate-counting, reversal-as-settlement, missing and duplicate postings |
| G0.7 Looker legitimacy | pass | 4 Explores with questions, PKs, joins, fixture answers; no experience claimed |
| G0.8 Cost and safety | pass | £0 spent; controls and cleanup specified; alerts explicitly not caps |

## Known limitations carried forward

1. **Documentation contradiction** (scheduled jobs deployed vs not) is *flagged*,
   not fixed — resolution with dated history is Plan 4 §7.3 scope.
2. Exception fixtures cover `missing_posting` and (test-synthesised)
   `duplicate_posting`; the remaining six reason codes are Plan 2 fault-injection
   scope, specified in `docs/contracts/reward-reconciliation.md`.
3. Grain statements for four preserved engagement marts are recorded as-built
   and should be confirmed when Plan 2 adds contracts.
4. The beyond-lookback (3 days 1 hour) fixture is specified but exercised only
   in Plan 2, where incremental processing actually exists.

## Unresolved risks

- The event simulator (Plan 2) may prove harder to keep deterministic at
  `standard` volume than at `tiny`; the reproducibility contract (Plan 2 §5.2)
  is the control.
- The Looker trial's terms may change before Plan 3; the runbook requires
  re-verification of no-cost terms at activation time.

## Plan 2 authorisation (effective on user acceptance)

Per Plan 1 §18, a `go` authorises Plan 2 to implement only: the deterministic
generator for the approved schemas/scenarios; the four-layer models required by
the four interfaces; incremental correctness, late-event/backfill and reward
reconciliation; compatibility paths for approved consumers; full standards
checks against real dbt artifacts; local DuckDB proof and BigQuery-compilation
readiness. No Looker activation, no paid BigQuery, no public release.

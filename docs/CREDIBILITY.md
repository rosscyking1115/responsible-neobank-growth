# Credibility & how to read the numbers

This project runs on **synthetic** customer-level data by design (the domain — per-customer
transactions joined to vulnerability, complaints, and outcomes — is PII in a regulated
sector and is not, and should not be, public). Synthetic data raises a fair question from a
reviewer:

> *Is a result here real signal, or just a generator the author tuned?*

This page answers it directly. The short version: **every number falls into one of two
piles, and they earn trust in different ways.** Read a figure's pile before you read its
value.

---

## The two piles

### Pile A — method-validation (ground-truth-backed)

These are **trustworthy on their own terms**, because the synthetic generator embeds a
*known* answer and the method is judged on whether it recovers it. Synthetic data makes
these *stronger*, not weaker: you cannot check whether a causal estimator recovers the truth
on real data, because the true counterfactual is never observed.

| Claim | Why it holds |
| --- | --- |
| CUPED variance-reduction %, delta-method SEs | Mechanical properties of the estimator on the data; reproducible. |
| SRM chi-square (assignment validity) | A statistical check on the realised split, not a tuned output. |
| Synthetic-control / DiD **recovers the embedded incrementality within CI** | The generator sets `referral_incrementality`; the method must land on it. That *is* the test. |
| Release-gate resolution logic | Deterministic mapping from signals to `ship / limited_rollout / … / block`; unit-tested. |
| Calibration reliability, RBAC redaction | Verified against held-out data / access rules, not authored. |

### Pile B — illustrative-magnitude (synthetic, not real-world performance)

These show the **method working end to end**, but their *magnitudes are illustrative* — they
reflect the generator's assumptions, not a real neobank. Never quote them as real-world
performance.

- D7 activation base rate, retention-curve shape, £CLV proxy, referral rates.
- **All wellbeing / fairness disparities** (segment outcome gaps, digital-inclusion
  abandonment, vulnerable-customer shares).
- The specific `limited_rollout` verdict in the worked decision (the *reasoning* is Pile A;
  the +4.5pp / +1.2pp *magnitudes* are Pile B).

**Labelling convention** used across the docs and dashboard:

> 🟢 *ground-truth-validated* (Pile A) &nbsp;·&nbsp; 🟡 *synthetic — illustrative of method,
> not real-world performance* (Pile B)

Two independent guards keep Pile B honest: magnitudes are **calibrated to real UK public
benchmarks** where one exists ([PUBLIC_DATA_CALIBRATION.md](PUBLIC_DATA_CALIBRATION.md),
[REAL_DATA_PROVENANCE.md](REAL_DATA_PROVENANCE.md)), and the **same code is re-run on real
public data** as a cross-check (see [Real-data cross-checks](#real-data-cross-checks)).

---

## Separation of generation and analysis (no circularity)

The sharpest failure mode for a synthetic project is **circularity**: the generator writes a
disparity in, the analysis "discovers" it, and the gate acts on it — the same assumption
counted three times. This project had exactly that bug once (an earlier release gate read a
*baseline* income gap as if the treatment had caused it) and fixed it, so the risk is treated
as real, not hypothetical.

The contract that prevents it:

1. **The generator's mechanism is documented and fixed up front** — see
   [`data_generator/wellbeing.py`](../data_generator/wellbeing.py) (wellbeing proxies from
   income/age priors + independent noise),
   [`data_generator/experiments.py`](../data_generator/experiments.py) (the embedded
   `true_d7_lift_pp`), and [`data_generator/config.py`](../data_generator/config.py) (all
   knobs: `d7_treatment_lift`, `referral_incrementality`, region effects).

2. **The analysis consumes only *observable* columns** — outcomes and features a real bank
   would have. It never reads the generator's parameters or the `true_*` ground-truth
   columns. Ground truth is used **only** to *score* a method afterwards, never as an input
   to it.

3. **This is enforced by tests, not just prose.**
   [`tests/test_no_circularity.py`](../tests/test_no_circularity.py) injects a deliberately
   wrong `true_d7_lift_pp` into the analysis frames and asserts the estimates are unchanged
   — proving the estimators follow the observed data, not the label — and asserts the
   release-gate inputs (`ReleaseSignals`) carry no generator-only field.

4. **Fairness is measured as the treatment's *effect*, not the baseline.** The release gate
   consumes `treatment_fairness_gap` — how much a change *widens* a segment gap (0 if it
   narrows) — so a beneficial change is never blocked for inequality it did not cause. See
   [RELEASE_DECISION_FRAMEWORK.md](RELEASE_DECISION_FRAMEWORK.md).

---

## Real-data cross-checks

The platform is not *limited* to synthetic data. The same analysis code is run on real
public datasets so a reviewer can see it operate on inputs the author did not generate:

| Cross-check | Real dataset | What it validates | Doc |
| --- | --- | --- | --- |
| **Fairness / outcomes** | UCI Bank Marketing (41,188 real records, CC BY 4.0) | The *same* `outcome_gap` code finds intuitive, real disparities (e.g. age). | [REAL_DATA_ADAPTER.md](REAL_DATA_ADAPTER.md) |
| **Experimentation** | Criteo Uplift (real randomised A/B, ~13M rows) | The *same* Welch / CUPED / SRM estimators behave correctly on a real treatment/control split. | [REAL_DATA_CRITEO.md](REAL_DATA_CRITEO.md) |

Honest boundary on the cross-checks: neither is a neobank, and the Criteo slice has **no
known ground-truth lift** to recover (it is ad-tech, and validates estimator *behaviour*, not
*recovery*). They demonstrate the pipeline runs on real inputs; they do not turn the
synthetic magnitudes into real-world performance.

> **Related — the same ground-truth discipline in another domain.** The absorbed
> marketing-measurement methodology validates its estimator the same way: it recovers *known*
> generating parameters and reports interval calibration honestly (finding and regression-
> testing a real posterior bug along the way) — see
> [parameter-recovery-validation.md](methodology/parameter-recovery-validation.md) and the
> [MMM ↔ experiment reconciliation](case-studies/mmm-experiment-reconciliation.md) case study.

---

## Why not just use real data?

Because switching would **weaken** the centrepiece. The project's thesis is *method* —
validating causal and decision machinery. That validation needs a known ground truth that
only synthetic data provides, in a domain where the joined per-customer object is
legitimately private and not available publicly. So the responsible choice is: synthetic
core, calibrated to real aggregates, cross-checked on real public slices, with every
magnitude labelled for what it is.

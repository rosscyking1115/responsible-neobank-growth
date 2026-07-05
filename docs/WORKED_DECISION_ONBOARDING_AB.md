# Worked Decision — Personalised Onboarding A/B

A single growth decision walked end to end, the way a product data scientist would
present it to a squad. Everything below is reproduced from the platform's own output on
the synthetic dataset (commands at the bottom).

---

## Recommendation (TL;DR)

**`LIMITED ROLLOUT`.** The personalised onboarding prompt lifts D7 activation by a clear,
significant **+4.5pp** and — importantly under Consumer Duty — it **narrows** the
activation gap between income groups rather than widening it. The one caveat is a small
but real **+1.2pp rise in support contacts**, which trips a guardrail. So: ship it to a
**capped share of traffic**, monitor support burden, and test an assisted-onboarding
variant before a full rollout.

---

## 1. The decision

A product squad proposes replacing the generic onboarding flow with a **personalised
"set up a savings pot" prompt**. The question is not "does activation go up?" — it's:

> Is the activation uplift real and large enough to act on, **and** does the change
> improve customer outcomes evenly (not just for the already-advantaged), without
> increasing complaints or support burden?

Primary metric: **D7 activation** (first card transaction within 7 days of signup).
Guardrails: support-contact rate, complaint rate, app-stability. Fairness lens: activation
by income band and vulnerability. Decision surface: `ship / limited_rollout /
experiment_only / needs_human_review / block`.

## 2. Experiment validity

| Check | Result |
| --- | --- |
| Assignment | control 2,485 · treatment 2,515 |
| Sample-ratio mismatch (SRM) | χ² = 0.18, p = 0.67 → **passes** (no assignment imbalance) |

SRM is the first thing to check — a failed SRM invalidates everything downstream. Here the
split is clean, so the readout is trustworthy.

## 3. Primary readout — D7 activation

| Variant | Users | D7 activation |
| --- | ---: | ---: |
| Control | 2,485 | 45.1% |
| Treatment | 2,515 | 49.6% |

- **Absolute uplift: +4.5pp** (≈ +10% relative).
- Two-proportion test: **z ≈ 3.2, p < 0.002**; 95% CI on the uplift ≈ **[1.7, 7.3] pp** —
  comfortably excludes zero.
- The gate consumes this as an evidence-strength signal ≈ **1.00** (ship-grade).

(In a live setting I'd also run **CUPED** with pre-signup engagement as the covariate to
shrink the variance; the platform supports it. Here the effect is already unambiguous.)

## 4. Guardrail metrics

| Guardrail | Control | Treatment | Δ | Verdict |
| --- | ---: | ---: | ---: | --- |
| Support-contact rate | 8.97% | 10.22% | **+1.25pp** | ⚠ warn (≥1pp) |
| Complaint rate | 0.36% | 0.64% | +0.27pp | ✅ within threshold |
| App-crash rate | 6.56% | 6.80% | +0.24pp | ✅ within threshold |

The only concern is **support burden**: the new prompt appears to generate slightly more
support contacts (people asking how to set up a pot). It's small, but it's a real
operational cost and a customer-effort signal, so it should not be ignored.

## 5. Fairness / Consumer Duty

This is where a fintech decision differs from an e-commerce one. A change that lifts the
average but **widens** the gap between well-served and under-served customers can be a
Consumer Duty problem. So I look at the **heterogeneous treatment effect**, not just the
average:

| Income band | Control | Treatment | Uplift |
| --- | ---: | ---: | ---: |
| high | 50.9% | 55.2% | +4.4pp |
| medium | 46.3% | 48.5% | +2.2pp |
| **low** | **38.1%** | **45.8%** | **+7.7pp** |

The treatment **helps low-income customers most**. The activation gap between high- and
low-income bands **narrows from 12.8pp to 9.5pp** — the change is *fairness-improving*.

The platform encodes this correctly: it feeds the gate the **treatment's effect on the
gap** (≈ 0 / narrowing), not the pre-existing baseline disparity. That distinction matters
— an earlier version wrongly blocked this beneficial change because it read the baseline
income gap as if the treatment had caused it. Vulnerable-flagged customers are additionally
routed to a review/monitor path rather than being targeted.

## 6. The gate — why `limited_rollout`

The engine separates **evidence** from **guardrails** and lets harm dominate:

- Evidence tier = **ship** (significant, ship-grade uplift; incrementality is clean in an
  RCT).
- Fairness = **pass** (narrows, doesn't widen).
- Complaints / stability = **pass**.
- Support burden = **warn** (+1.2pp).

A warn on a customer-outcome guardrail is enough to stop a full `ship` but not enough to
`block` a change that is both effective and fairness-improving. → **`limited_rollout`.**

## 7. What I'd actually do

1. **Roll out to a capped share** (e.g. 20–25%) rather than 100%.
2. **Monitor support-contact rate** in the rollout cohort; if the +1.2pp holds or grows,
   that's the blocker to resolve before scaling.
3. **Test an assisted-onboarding variant** (clearer copy / in-flow help) aimed at removing
   the support-contact cause — likely the pot-setup step confusing some users.
4. **Re-read** at a larger sample / longer window before deciding on full rollout.

## 8. Limitations

- **Synthetic data** — the point is the *method*; magnitudes are illustrative.
- **Single 7-day window** — no novelty/primacy correction or longer-horizon retention here;
  I'd want W4 retention before calling it a win.
- **Support burden is correlational** within the experiment arm — the assisted-onboarding
  test is what would confirm the cause.

## Reproduce

```powershell
uv run python -m data_generator.generate --users 5000 --months 6 --output-dir raw/ci
uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank
# variant readout + decision are on the dashboard's "Customer outcomes" tab,
# or via app.dashboard_data.onboarding_release_decision(...) and the release-gate engine.
```

Decision engine: [`src/release_decisions`](../src/release_decisions) ·
experimentation: [`src/experiments`](../src/experiments) · fairness signal:
`treatment_fairness_gap` in [`app/dashboard_data.py`](../app/dashboard_data.py).

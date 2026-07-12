# MMM benchmark note — how a transparent reference relates to the mature tools

> **As of 2026-07, ported from [marketing-effectiveness-lab](https://github.com/rosscyking1115/marketing-effectiveness-lab)**
> (now archived); docs only. Live dashboard (kept warm from this repo):
> <https://marketing-effectiveness-lab.streamlit.app/>.

The marketing-mix engine absorbed here is a **transparent reference implementation** —
deliberately kept legible so every transform, prior, and validation step sits next to the
code that implements it. It is **not** a competitor to the mature open-source MMM tools. This
note states honestly what those tools add over it, so the boundary is explicit rather than
implied.

## How it relates to the specialist tools

| Tool | What it adds over this reference |
| --- | --- |
| **[Google Meridian](https://github.com/google/meridian)** | Hierarchical Bayesian MMM, full posterior over adstock/saturation, geo-level modeling, reach/frequency, built-in ROI priors from experiments. |
| **[Meta Robyn](https://github.com/facebookexperimental/Robyn)** | Ridge regression with evolutionary (Nevergrad) hyperparameter search over adstock/saturation, Pareto-front model selection, automated calibration to experiments. |
| **[PyMC-Marketing](https://github.com/pymc-labs/pymc-marketing)** | Full PyMC Bayesian MMM — MCMC (NUTS) over all transform parameters, custom priors, posterior predictive checks, time-varying effects. |

## What the reference does that is visible at a glance

- Every transformation, prior, and validation step is **documented next to the code**.
- The estimator is checked against **known ground truth** — see
  [parameter-recovery-validation.md](parameter-recovery-validation.md).
- The **MMM ↔ experiment loop** is demonstrated end to end — see
  [mmm-experiment-reconciliation.md](../case-studies/mmm-experiment-reconciliation.md).

The tools above are what you would reach for **in production**; this material is where you go
to *understand how the pieces work*.

## Stated methodological gap

The clearest gap versus those tools — **sampling** the adstock/saturation parameters rather
than fixing them, and modeling at the **geo level** — was the top roadmap item in the source
project. It is recorded here so the limitation travels with the methodology, not just the
strengths.

# Decision Memo: Personalised Onboarding A/B Test

## Executive Summary

SHIP: launch the personalised prompt with rollout monitoring.

The treatment increased D7 activation by 2.29 pp with CUPED,
95% CI [1.42 pp, 3.15 pp],
p=0.0000. The embedded synthetic ground truth is 3.00 pp.

## Context

We tested a personalised onboarding prompt that nudges new users toward a Savings Pot
setup flow. The decision metric is D7 activation: first card transaction within 7
days of signup. The experiment uses deterministic 50/50 assignment at signup and a
pre-treatment activation propensity score from signup metadata as the CUPED covariate.

## Assignment Quality And Power

- Analysed users: 50,000.
- SRM p-value: 0.0736; passed at alpha 0.001.
- Current 80% power MDE: 1.25 pp absolute D7 activation lift.
- Approximate achieved power for the CUPED estimate: 99.92%.
- Balanced sample needed per arm for a 2.00 pp lift: 9,739.

## Result

- Control D7 activation: 45.71%.
- Treatment D7 activation: 47.92%.
- Naive lift: 2.21 pp, 95% CI [1.34 pp, 3.09 pp], p=0.0000.
- CUPED lift: 2.29 pp, 95% CI [1.42 pp, 3.15 pp], p=0.0000.
- CUPED theta: 0.9889; variance reduction: 1.40%.

## Guardrails

- Support contact rate: effect -0.49 pp, 95% CI [-1.00 pp, 0.03 pp], pass (upper CI <= 0.0050).
- Complaint rate: effect -0.05 pp, 95% CI [-0.18 pp, 0.08 pp], pass (upper CI <= 0.0020).
- App crash rate: effect 0.00 pp, 95% CI [-0.42 pp, 0.43 pp], pass (upper CI <= 0.0100).
- Vulnerable-customer D7 activation: effect 3.72 pp, 95% CI [-0.40 pp, 7.84 pp], pass (lower CI >= -0.0100).

## Heterogeneous Effects

Largest positive slices:

- region = Northern Ireland: effect 4.69 pp, 95% CI [-1.40 pp, 10.78 pp], n=1,024.
- signup_channel = organic_search: effect 3.71 pp, 95% CI [1.53 pp, 5.89 pp], n=8,030.
- region = North East: effect 3.44 pp, 95% CI [-1.53 pp, 8.41 pp], n=1,526.
- region = Wales: effect 3.38 pp, 95% CI [-1.01 pp, 7.76 pp], n=1,984.
- income_segment = student: effect 3.28 pp, 95% CI [0.81 pp, 5.75 pp], n=6,086.
- region = South East: effect 3.14 pp, 95% CI [0.71 pp, 5.57 pp], n=6,496.

## Caveats

The CUPED covariate is a synthetic pre-treatment propensity score. In a live fintech
setting, the same pattern should use frozen pre-experiment or eligibility-time
features from governed feature tables, with no leakage from treatment exposure.
The analysis reads user-level marts, so rollout monitoring should still validate
support load, complaints, app stability, and vulnerable-customer outcomes in daily
dashboards before ramping to full traffic.

## Recommendation

SHIP: launch the personalised prompt with rollout monitoring.

Roll out behind a feature flag, monitor the guardrails above daily for the first two
weeks, and keep the personalised prompt eligible only for users whose onboarding
state makes the prompt clearly relevant.

## Next Experiment

Test prompt timing and message framing: immediate post-signup versus after first app
session, with separate treatment arms for Savings Pot setup, Salary Sorter setup,
and a neutral "make your first card payment" activation prompt.

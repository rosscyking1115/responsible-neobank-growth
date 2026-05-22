# Model Card: Activation Decisioning

## Executive Summary

PILOT: use the model for a monitored onboarding-help treatment.

The calibrated signup-time model ranks D7 activation propensity with ROC AUC
0.573, Brier score 0.245, and expected
calibration error 4.65% on the forward test
window. The best threshold targets users with predicted activation probability at
or below 45.00%.

## Intended Use

Use this model to prioritise a helpful onboarding intervention, such as extra setup
guidance or a clearer first-card-payment prompt. The score should not be used for
pricing, eligibility, credit decisions, account limits, or any punitive customer
treatment.

## Data And Features

- Rows: 50,000.
- Temporal split: 30,000 train, 10,000 calibration, 10,000 test.
- Label: D7 activation, defined as first card transaction within 7 days of signup.
- Features: region, signup channel, device OS, age, income segment, push opt-in,
  vulnerable-customer flag, business-account flag, signup month, and signup day of week.
- Excluded from training: transaction outcomes, feature adoption, support contacts,
  CLV, experiment treatment, and synthetic hidden propensity fields.

## Performance

- Test rows: 10,000.
- Test activation rate: 43.97%.
- ROC AUC: 0.573.
- Average precision: 0.495.
- Brier score: 0.245.
- Log loss: 0.683.
- Expected calibration error: 4.65%.

## Threshold Economics

- Value per activation assumption: GBP 11.
- Contact cost assumption: GBP 0.45 per targeted user.
- Selected threshold: predicted activation <= 45.00%.
- Targeted users in test window: 2,560 (25.60%).
- Expected incremental activations: 111.1.
- Expected net value: GBP 96.

## Customer-Outcome Guardrails

- vulnerable_targeting_ratio: 2.155 <= 2.500 (pass).
- vulnerable_false_negative_gap: -0.146 <= 0.080 (pass).
- low_income_false_negative_gap: -0.158 <= 0.080 (pass).

These checks are deliberately conservative. A live rollout should also monitor
complaints, support contacts, opt-outs, accessibility needs, and vulnerable-customer
outcomes daily.

## Explainability

Largest model coefficients after preprocessing:

- categorical__income_segment_student: coefficient -0.290 (absolute 0.290).
- categorical__signup_channel_paid_social: coefficient -0.238 (absolute 0.238).
- categorical__income_segment_affluent: coefficient 0.235 (absolute 0.235).
- categorical__signup_channel_campus: coefficient -0.205 (absolute 0.205).
- categorical__signup_channel_word_of_mouth: coefficient 0.203 (absolute 0.203).
- binary__push_opt_in: coefficient 0.178 (absolute 0.178).
- binary__business_account_flag: coefficient 0.174 (absolute 0.174).
- binary__vulnerable_customer_flag: coefficient -0.165 (absolute 0.165).
- categorical__income_segment_low: coefficient -0.152 (absolute 0.152).
- categorical__region_North East: coefficient -0.137 (absolute 0.137).
- categorical__income_segment_high: coefficient 0.123 (absolute 0.123).
- categorical__region_East of England: coefficient 0.110 (absolute 0.110).
- categorical__region_East Midlands: coefficient -0.086 (absolute 0.086).
- categorical__signup_channel_business_referral: coefficient 0.078 (absolute 0.078).
- categorical__region_London: coefficient 0.077 (absolute 0.077).

Signup-channel score summary:

- word_of_mouth: mean score 52.04%, observed D7 activation 48.19%, rows 3,692.
- business_referral: mean score 50.58%, observed D7 activation 48.89%, rows 405.
- app_store: mean score 48.90%, observed D7 activation 42.05%, rows 1,793.
- organic_search: mean score 48.11%, observed D7 activation 44.88%, rows 1,660.
- partnership: mean score 46.04%, observed D7 activation 40.90%, rows 687.
- campus: mean score 42.15%, observed D7 activation 39.96%, rows 538.
- paid_social: mean score 40.95%, observed D7 activation 34.69%, rows 1,225.

## Operating Policy

The model should be deployed only behind an experiment or feature flag. Use it to
offer assistance, not to withhold service. Recalibrate monthly or whenever acquisition
mix changes materially, and retrain if expected calibration error exceeds 5% or if
any customer-outcome guardrail fails.

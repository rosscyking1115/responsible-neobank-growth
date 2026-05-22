# Decision Memo: Referral Incrementality Geo Experiment

## Executive Summary

ITERATE: referral lift is positive, but unit economics need a cheaper incentive.

The blended causal estimate is 289.0 incremental
referral signups across North West, Wales, Yorkshire and The Humber during the post period.
Observed reward cost was GBP 16,380, implying
GBP 57 per incremental signup.

## Context

We tested a regional referral incentive in selected regions where network effects
make a user-level A/B test hard to interpret. The outcome is referral-attributed
signups per region-day. Total signups are monitored as a spillover guardrail.

## Result

- DiD effect: 0.52 referral signups per treated region-day,
  95% CI [-0.04, 1.08], p=0.0681.
- DiD total lift: 201.1 referral signups.
- Synthetic-control total lift: 376.8 referral signups.
- Synthetic-control pre-period RMSE: 2.42.
- Blended lift: 289.0 referral signups.
- Embedded ground-truth incremental referral signups observed in treated post period:
  510. Configured synthetic incrementality fraction: 60.0%.
- Ground-truth recovery ratio: 56.7%.

## Donor Pool

Largest synthetic-control donor weights:

- London: 64.1%
- South East: 20.1%
- West Midlands: 12.7%
- East of England: 3.0%
- South West: 0.0%

## Diagnostics

- Pre-period treated-minus-control slope gap: 0.0000
  referral signups per day.
- Total-signup spillover DiD: -0.56
  signups per treated region-day, p=0.5254.
- Largest absolute placebo DiD effect: 0.66 referral signups per day.
- Largest absolute placebo synthetic-control total effect: 213.8 referral signups.

Placebo examples:

- London: DiD 0.66 referral signups per day, synthetic-control total 213.8.
- South East: DiD 0.09 referral signups per day, synthetic-control total 21.9.
- South West: DiD 0.07 referral signups per day, synthetic-control total 33.2.
- East Midlands: DiD -0.13 referral signups per day, synthetic-control total -0.6.
- East of England: DiD -0.21 referral signups per day, synthetic-control total 3.3.

## Caveats

The design assumes untreated regions form a credible counterfactual after controlling
for region and date effects. Remaining risks are cross-region referral spillovers,
region-specific marketing shocks, donor-pool mismatch, and seasonality not captured
by shared date effects. The synthetic-control estimate is useful as a triangulation
check, not as a proof by itself.

## Recommendation

ITERATE: referral lift is positive, but unit economics need a cheaper incentive.

Roll out to additional similar regions in a stepped-wedge design, keep at least a few
regions as holdouts, and monitor total signups, referral quality, support contacts,
and cost per activated referred customer.

## Next Experiment

Test lower-cost incentive variants and message framing. The next readout should use
activated referred customers, not only referred signups, as the primary value metric.

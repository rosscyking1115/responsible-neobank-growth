# Looker Evidence Checklist (Plan 3 capture; written in Plan 1, not yet executed)

> Evidence must survive trial expiry. Capture everything below before the trial
> ends; **no credential**, billing identifier, private project ID or signed URL
> may appear in any artifact.

## Capture list

- [ ] All LookML source committed at the validated Git commit
- [ ] **Validator output** summaries (LookML, SQL, Assert, Content) with timestamp and commit
- [ ] **Screenshot** of each of the three dashboards and one representative Explore
- [ ] Screenshot/evidence of the SQL generated for one governed query
- [ ] **Expected-versus-actual** table for every fixture answer below
- [ ] Two-to-three-minute **walkthrough** video (silent or narrated) with transcript
- [ ] Trial version/region and validation date
- [ ] Limitations, cleanup record and no-affiliation statement

## Fixture answers (expected values from the tiny truth fixtures)

The validation fixture is the `referral-known-truth` scenario
(`fixtures/truth/tiny/referral-known-truth.json`) loaded through the governed
interfaces. Each Explore must reproduce these exact values.

### growth_acquisition

| Question | Expected fixture answer |
|---|---|
| Funded activations traced to referrals (happy-path fixture) | 1 (`acc_000001`, first funding £100.00) |
| Applications in happy-path fixture | 1 |

### referral_economics

| Question | Expected fixture answer |
|---|---|
| Qualified referrals (known-truth) | 5 canonical (ref_100001–4, ref_100006) |
| Reward booked cost (known-truth) | 20000 minor units (£200.00) |
| Entitlement (known-truth) | 25000 minor units (£250.00) |

### reward_reconciliation

| Question | Expected fixture answer |
|---|---|
| Missing postings (known-truth) | exactly 1 (`ref_100006`) |
| Reversed amount (known-truth) | 5000 minor units (`rwd_100004`) |
| Outstanding payable (known-truth) | 0 |
| Daily entitlement 2026-01-05 / 2026-01-06 | 10000 / 15000 minor units |

### warehouse_health

| Question | Expected fixture answer |
|---|---|
| Freshness breach in the freshness-outage fixture | breached = true (96h gap > 72h threshold) |
| Cost fields before Plan 3 measurement | null (never displayed as zero) |

## Post-capture verification

- [ ] Every value above matched, or the mismatch is recorded and fixed test-first
- [ ] Evidence files reviewed for secrets before commit
- [ ] `artifacts/plan3/looker/validation-summary.md` written with links to all artifacts

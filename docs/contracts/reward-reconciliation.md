# Reward Reconciliation Contract

> **Status:** Accepted 2026-07-17 (Plan 1, Task 7). Freezes the bounded
> referral-reward subledger semantics for Plan 2. Detection behaviour is
> executable now: `tests/oracles/test_reward_reconciliation_truth.py` proves the
> tiny fixtures expose incorrect reversal treatment and missing postings exactly.

## Scope

Finance is limited to the referral-reward subledger (Route C scope,
`docs/architecture/route-c-product-scope.md`). No general ledger, payments
processor or bank-wide reconciliation platform is represented.

## Lifecycle

```text
invited -> qualified -> booked -> settled
                         |          |
                         +-> reversed <-+
```

Invalid transitions create data-quality exceptions. Reversals are new events —
the original booking is never mutated (append-only source contract).

## Bounded chart of accounts (fictional)

- `referral_reward_expense`
- `referral_reward_payable`
- `reward_cash_clearing`

Illustrative double-entry treatment:

| Event | Debit | Credit |
|---|---|---|
| Reward booked | referral_reward_expense | referral_reward_payable |
| Reward settled | referral_reward_payable | reward_cash_clearing |
| Booking reversed before settlement | referral_reward_payable | referral_reward_expense |

This is **not a claim about** Monzo's or any real bank's accounting policy. If an
accountant-reviewed representation changes these entries later, the synthetic
truth and tests change together before publication.

## Invariants (zero tolerance)

- debit equals credit for every journal;
- opening balance plus movements equals closing balance;
- `outstanding_payable = booked − settled − reversed` (integer minor units);
- every canonical qualified referral has exactly one expected entitlement of
  `reward_amount_minor`;
- every exception carries a reason code, age and source-event trace.

## Mandatory exception reasons

- `missing_posting` — qualified referral with no booked reward
  (exercised by the `reconciliation-break` and `referral-known-truth` fixtures);
- `duplicate_posting` — more than one booking for one referral;
- `amount_mismatch` — booked/settled/reversed amount differs from entitlement;
- `invalid_lifecycle_transition`;
- `unbalanced_journal`;
- `settlement_without_booking`;
- `reversal_beyond_booked_amount`;
- `pending_beyond_synthetic_sla`.

Plan 1 fixtures exercise `missing_posting` exactly; Plan 2 fault injection must
cover the remainder with the same exact-truth discipline. Reason codes are
append-only (interface deprecation policy).

## Daily outputs

For each reward and day, Plan 2 calculates: expected entitlement; booked,
settled and reversed amounts; outstanding payable; debit/credit balance;
lifecycle status; reconciliation status; exception reason and age; owning
interface and source event trace. The `referral-known-truth` fixture declares
exact daily entitlement and ledger totals that these outputs must reproduce.

# Route C Product Scope — Responsible Neobank Growth

> **Status:** Accepted 2026-07-17 (Plan 1, Task 2) · **Owner:** Ross (Cheng-Yuan King)
> **Authoritative plan:** Responsible Neobank Growth — Plan 1: Architecture, Contracts and Gate 0

This document locks the product identity, scope and exclusions for the Route C
migration: `responsible-neobank-growth` becomes an event-to-interface Analytics
Engineering platform. It is the reference other Route C documents and tests point at.

## Reviewer-facing identity

This remains an independent open portfolio and reusable reference project built on
**synthetic** data. It is **not a Monzo simulation** (**no affiliation** with Monzo
Bank Ltd), not a regulated product, **not a production banking system**, and
**not evidence of work with real bank customers**.

### Target sentence (to be earned, not yet achieved)

> I designed a governed neobank analytics platform where late, duplicated, reversed
> and schema-evolving source events have known truth; incremental BigQuery/dbt models
> reconcile them into trusted Growth and referral-reward interfaces that analysts
> investigate through Looker.

Plan 1 approves this only as the *target* sentence. Later plans must supply the
evidence before it may appear anywhere as an achieved claim.

### Primary stakeholder question

> Which acquisition and referral activity creates incremental activated customers
> without unacceptable customer-outcome signals, and did every qualified referral
> reward post exactly once and reconcile correctly?

Everything admitted to the MVP must support this question, platform trust, or one
preserved downstream consumer.

## Locked scope

### Primary domain: responsible Growth

Admitted source event families (closed list):

1. marketing campaign and spend;
2. application, KYC and account lifecycle;
3. activation and first funding;
4. referral invitation, qualification and reward lifecycle;
5. experiment assignment and outcome;
6. complaints/support/poor-outcome signals as a bounded guardrail.

### Bounded Finance proof

Finance is limited to the **referral-reward** subledger and the reconciliation needed
to answer: for every qualified referral reward, was the expected amount booked once,
settled or reversed correctly, and reconciled to the daily reward ledger?

No general ledger, payments processor, card authorisation system, prudential report,
AML system or bank-wide reconciliation platform is admitted.

### Four-layer warehouse

The target dbt model layers are **landing**, **normalised**, **logical** and
**presentation** (see ADR-route-c-four-layer-interfaces). Only normalised and logical
models may become cross-domain governed interfaces.

## Explicit non-goals (forbidden scope)

- **fraud** detection, **AML**, **credit scoring** or **lending**;
- a **general ledger** or bank-wide reconciliation platform;
- reproducing Monzo's private data model, implementation or scale;
- additional forecasting, LLM, causal-ML or modelling features;
- **Kafka**, **streaming** infrastructure or **real-time** claims;
- production PII, authentication or enterprise security theatre;
- replacing DuckDB as the fast local development target;
- deleting current models before compatibility is demonstrated;
- publishing synthetic data before the generator, truth manifest and limitations pass
  verification.

## Boundary rules retained from the current project

- Synthetic-data credibility boundaries in `docs/CREDIBILITY.md` remain in force and
  are extended by ADR-route-c-synthetic-truth.
- Existing validated Growth, experimentation, fairness and customer-outcome
  capabilities are preserved through the migration inventory
  (`docs/migration/route-c-model-inventory.csv`), not rewritten.
- Plan 1 authorises no new billable cloud execution, no Looker trial, no public
  dataset release and no public README repositioning.

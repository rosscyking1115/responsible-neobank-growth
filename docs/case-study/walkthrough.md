# Walkthrough Script (2–3 minutes)

> A spoken script for a short screen-recorded walkthrough. Every figure resolves
> to [`evidence/registry.yml`](../../evidence/registry.yml). Because Looker was
> access-limited, the BI segment is replaced by the BigQuery evidence and the
> gap is stated (Plan 4 §11.2). Keep it calm and specific; total ~2m40s.
> Accessibility: record with captions; this script doubles as the transcript.

## 0:00–0:20 — The decision problem and the synthetic boundary

"This is a synthetic, independent project — no affiliation with any bank. The
problem it tackles is real, though: backend events in a neobank arrive late,
duplicated, reversed, and with changing schemas, and a data team has to turn
that mess into interfaces people can trust. The trick here is that the data is
generated with *known truth* — every defect is injected against a manifest — so
correctness can be checked, not just claimed."

## 0:20–0:55 — One event, and its truth

"Here's a single referral. It qualifies, a reward is booked, and it settles.
Now watch the injected defects: this qualification is delivered twice with the
same idempotency key — the warehouse must count it once. This one arrives two
days late — an ordinary incremental run repairs it. This reward is reversed
instead of settling. And this qualification's reward posting is deliberately
missing. The truth manifest already says exactly how many of each there should
be, down to the daily ledger totals."

## 0:55–1:30 — The four layers and governed interfaces

"Events land append-only, with bad payloads quarantined as evidence rather than
dropped. Landing flattens and deduplicates; normalised builds canonical,
version-independent events and current state — this is where a v1 and a v2
referral schema become one meaning. Logical publishes four governed interfaces —
growth acquisition, referral economics, reward reconciliation, warehouse health
— each with one owner and one authoritative grain. The existing experimentation
code runs unchanged on these interfaces through a compatibility view, so nothing
that already worked was thrown away."

## 1:30–2:05 — Incremental parity and the measured BigQuery result

"The core question: does incremental processing produce the same answer as a
full rebuild? I build the same final state both ways and compare every
interface — row counts, content fingerprints, and integer money — with zero
tolerance. On the 569,000-event benchmark on BigQuery, they matched exactly at
every phase. The cost result is honest and mixed: incremental billed about two
percent *more* bytes, because the raw store is unpartitioned so every strategy
scans it — but it used about sixty percent less compute. The ablation shows
where byte savings actually come from: the same query on partitioned storage
scanned five hundred times fewer bytes. The whole run cost about twenty pence."

## 2:05–2:30 — What the scale run caught (replaces the BI segment)

"Running at full scale earned its keep: it exposed two staleness bugs the small
test couldn't — a settlement arriving before its late booking, and its ledger
lines going stale after the fix. Both are now caught by invariants and heal
automatically. I also built a full LookML semantic layer for this, but I'll be
straight about it: the Looker trial was access-limited, so it's authored and
reviewed, not validated in a live instance — and I don't claim otherwise."

## 2:30–2:40 — Limitations and reuse

"It's synthetic, engineered for coverage, not calibrated to any real bank, and
the benchmark is one size on one day. The event dataset, the truth manifests and
the whole pipeline are in the repo, reproducible from a clean clone with no
cloud account. Thanks for watching."

## Recording checklist

- [ ] Screen capture at 1080p; captions on (this file is the transcript).
- [ ] Show, in order: a truth manifest, the dbt DAG, a parity artifact, the
      benchmark summary, the LookML files with the "not validated" note.
- [ ] No credentials, billing identifiers, private project IDs or signed URLs
      on screen.
- [ ] Keep to ~2m40s; do not overrun into feature-tour territory.

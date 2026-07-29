# Futures considered and declined

**Status: this project is complete and frozen. Decided 2026-07-27.**

Four plausible next directions were assessed and each was declined on specific
evidence. This record exists so they are not re-proposed from scratch. Each entry
states what would have to change for the decision to be worth revisiting.

The bar for reopening any of these is **new evidence**, not renewed enthusiasm.

> Adoption and third-party figures below are as recorded by the 2026-07-27 scan
> and are not re-measured here. Re-check them before relying on them.

---

## 1. Turn the dataset into a public benchmark

**Declined.** The category has a graveyard, and this project has no distribution.

TPC-DI is the closest prior art: a data-integration benchmark with deliberately
embedded data-quality defects — the same core idea — backed by a funded industry
consortium, an audited results-submission programme and a VLDB paper. As of 2022
it had received **no official submissions**.

If a consortium-backed, audited, peer-reviewed benchmark could not attract a
single submission, a solo synthetic dataset will not. The distribution numbers
confirm there is no launch platform here: 23 dataset downloads in the last month,
and 1 star on the repository.

*Reopen if:* someone with existing distribution wants to co-own it, or a vendor
asks to submit results against it. Not before.

## 2. Build a test harness for data-quality tools

**Declined.** The gap is real; the silence about it is informative.

There is genuinely no neutral harness for evaluating data-observability tools,
and this repository's known-truth manifest would be a reasonable substrate for
one. But the observability category has existed for roughly eight years and has
produced no such benchmark. That is revealed preference, not an oversight:
buyers evaluate these tools on **their own data**, because the failure modes they
care about are their own. A neutral harness answers a question the buyer does not
have.

*Reopen if:* a buyer or vendor asks for a neutral comparison — i.e. the demand
appears from outside rather than being assumed.

## 3. Turn it into a teaching product

**Declined.** The distribution is already owned.

DataTalksClub occupies the free data-engineering curriculum space, and dbt Labs'
`jaffle-shop` is the default teaching dataset with the vendor's own distribution
behind it. Competing for that attention is a marketing problem, not an
engineering one, and this project has no marketing advantage.

*Reopen if:* an existing course wants to adopt the dataset — adoption first, then
packaging.

## 4. Repoint the machinery at real data

**Declined.** The existing argument is better, and it is already written down.

[CREDIBILITY.md](CREDIBILITY.md#why-not-just-use-real-data) makes the case: the
project's thesis is *method validation*, and validating a causal estimator
requires a known counterfactual, which real data never provides. Switching to
real data would not strengthen the centrepiece — it would remove it. The project
already runs the same estimators on two real public datasets (UCI Bank Marketing,
Criteo Uplift) as a cross-check, which is the part real data can actually
support.

This is the one option that would make the project *worse*, not merely
unprofitable.

*Reopen if:* never, on these grounds. A real dataset with a known embedded
counterfactual would be a different project, not a change to this one.

---

## What was kept instead

The scan's conclusion was that the repository is complete, and that its most
valuable property was under-sold rather than missing: **every detector in it is
tested for detection, using deliberate negative controls.** That is now stated
in the [README](../README.md#every-check-here-is-tested-for-detection) and leads
the demo script in [CLAIMS_AND_SCOPE.md](CLAIMS_AND_SCOPE.md).

Promoting an existing, shipped, green property cost far less than any of the four
options above and is the only one that improved how the work reads.

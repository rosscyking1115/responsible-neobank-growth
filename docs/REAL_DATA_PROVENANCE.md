# Real-Data Provenance

This project uses **synthetic** customer-level data — that data class (per-customer
transactions joined to vulnerability, complaints, and outcomes) is PII in a heavily
regulated domain and is not, and should not be, public. Instead the synthetic
generators are **anchored to real, published UK aggregate statistics**, and a real
public dataset is available for an optional decisioning/fairness adapter.

This file records the sources behind those anchors so every synthetic figure is
defensible. All figures are point-in-time; refresh against the latest release.

## Calibration anchors (wired into `src/calibration`)

| Synthetic proxy | Target | Real figure | Source (year) |
| --- | ---: | --- | --- |
| `new_to_uk_share` | 16.8% | 16.8% of England & Wales residents born outside the UK | [ONS Census 2021 — international migration](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/internationalmigration/bulletins/internationalmigrationenglandandwales/census2021) |
| `accessibility_need_share` | 24% | 24% of the UK population (16.1m) reported a disability | [DWP Family Resources Survey 2022/23](https://www.gov.uk/government/statistics/family-resources-survey-financial-year-2022-to-2023) |
| `low_digital_confidence_share` | 18% | ~20% lack foundation digital skills (80% have them); 27% "lowest digital capability" | [Lloyds Consumer Digital Index 2023](https://www.lloydsbank.com/consumer-digital-index.html) |

**Construct notes:** these are *related but not identical* to the synthetic proxies.
"Digital confidence" is narrower than "digital skills", so the digital anchor is set
slightly below the ~20% skills figure. Disability prevalence is definition-sensitive.

## Additional context (cited in modules, not strict calibration checks)

These ground the narrative of the outcomes, pricing, and protection modules but are
volumes/£ that don't map cleanly to a single per-customer share, so they are not
calibration anchors:

| Concept | Figure (year) | Source |
| --- | --- | --- |
| Customer vulnerability | 49% of UK adults show characteristics of vulnerability (26.4m); 24% low financial resilience | [FCA Financial Lives 2024](https://www.fca.org.uk/financial-lives/financial-lives-2024) |
| Complaints | FOS uphold rate 37%; banking/payment complaints 80,137 (2023/24, a 10-year high); ~4.2 complaints/1,000 accounts (2019 H2 — verify latest) | [FOS 2023/24](https://www.financial-ombudsman.org.uk/data-insight/annual-complaints-data/annual-complaints-data-insight-2023-24) · [FCA complaints data](https://www.fca.org.uk/data/complaints-data) |
| APP / scam fraud | £450.7m APP losses in 2024 (−2%); ~186k cases; investment fraud £144.4m (~32% of APP £); purchase scams £87.1m | [UK Finance Annual Fraud Report 2025](https://www.ukfinance.org.uk/policy-and-guidance/reports-and-publications/annual-fraud-report-2025) |

> The FCA "49%" vulnerability figure is a *broad* measure (any characteristic). Our
> `vulnerable_customer_proxy` models a narrower, more acute subset, so it is **not**
> calibrated to 49% — the FCA figure is cited for context only.

## Real dataset for an optional adapter

**UCI Bank Marketing** (Moro, Cortez & Rita, 2014) — real data from a Portuguese
bank's phone campaigns; 41,188 records; target = term-deposit subscription (yes/no),
with age / job / marital / education for demographic slicing. It ships in
`fairlearn.datasets.fetch_bank_marketing`, i.e. it is an established fairness-research
dataset — a strong fit to demonstrate the activation/decisioning and fairness path on
real inputs.

- Source: <https://archive.ics.uci.edu/dataset/222/bank+marketing> (CC BY 4.0; cite Moro et al. 2014).
- Lower-fit alternatives: Kaggle credit-card-fraud (ULB) — real but anonymised, no
  demographics; Lending Club (lending, not neobank growth); Telco churn (wrong sector).

## What this does and does not claim

- **Does:** anchor synthetic distributions to verified public aggregates; cite real
  fraud/complaint/vulnerability statistics; offer a real public dataset adapter.
- **Does not:** use any real customer-level data, or claim to. The synthetic core is a
  deliberate, responsible choice for a privacy-sensitive domain.

# Real-Data Adapter — UCI Bank Marketing

The platform runs on synthetic data by design, but it is **not limited to it**. This
adapter runs the same customer-outcome / fairness analysis on a **real** public
banking dataset, proving the pipeline works on real inputs.

## The dataset

**UCI Bank Marketing** (Moro, Cortez & Rita, 2014) — ~41k real phone-campaign records
from a Portuguese bank. Target: term-deposit subscription (`y` = yes/no), a genuine
conversion outcome. Demographic features (age, job, marital, education) enable fairness
slicing. It ships in `fairlearn.datasets`, i.e. it is an established fairness benchmark.

- Download: <https://archive.ics.uci.edu/dataset/222/bank+marketing> (CC BY 4.0; cite Moro et al. 2014).
- See [REAL_DATA_PROVENANCE.md](REAL_DATA_PROVENANCE.md) for why a *real* dataset is
  used here while the customer-level core stays synthetic.

## Where it lives

| Concern | Location |
| --- | --- |
| Adapter (load + outcome + fairness) | [`src/adapters/uci_bank_marketing.py`](../src/adapters/uci_bank_marketing.py) |
| Tests | [`tests/test_uci_adapter.py`](../tests/test_uci_adapter.py) |

The fairness analysis **reuses `src.wellbeing.metrics.outcome_gap`** — the same machinery
the synthetic dashboard uses — so the definition of a fairness gap is identical across
real and synthetic data.

## Run it

```powershell
# after downloading and unzipping bank-additional-full.csv
uv run python -m src.adapters.uci_bank_marketing --csv path/to/bank-additional-full.csv
```

Real output on the full 41,188-record dataset:

```text
- Records: 41,188
- Term-deposit conversion: 11.3% (4,640 subscribed)

| Segment   | Gap (pp) | Higher-rate level | Lower-rate level |
| age_band  |   38.6   | 65_plus           | 45_54            |
| job       |   24.5   | student           | blue-collar      |
| education |    6.7   | unknown           | basic.9y         |
| marital   |    4.8   | unknown           | married          |
```

The 11.3% conversion matches this dataset's documented base rate — a correctness check
that the adapter reads and analyses the real data correctly. The largest disparity
(age: retirees convert on term deposits far more than mid-career customers) is a known,
intuitive pattern, demonstrating the fairness analysis surfaces real structure.

## Boundary

This analyses *aggregate outcomes and group disparities* on a public, consented
research dataset. It makes no individual inferences and uses no customer PII.

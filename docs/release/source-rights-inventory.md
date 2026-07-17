# Source and Rights Inventory (Plan 4, Task 5)

> **Result: PASS** — every included artifact's rights are clear and mutually
> compatible, so the generated dataset may carry an explicit licence. Prepared
> 2026-07-17. Publication itself remains gated on the user's approval (Task 7).

## What the public release includes

Code and documentation (this repository) plus, if published, a **generated
synthetic event dataset** (deliveries, quarantine fixtures, truth manifests,
checksums, schemas). It does **not** include the UCI Bank Marketing or Criteo
Uplift datasets — only the adapter code that reads them.

## Rights inventory

| Artifact | Origin | Rights / terms | Compatible? |
|---|---|---|---|
| Repository source | Authored in this project | MIT © 2026 Cheng-Yuan King (`LICENSE`) | yes |
| Generated event data | Output of this project's own generator | Author owns the generator and its deterministic output; free to license | yes |
| Event/interface/scenario schemas + enums | Authored here (generic business event names) | No copied proprietary text or enumerations | yes |
| Truth manifests / checksums | Computed by this project | Author-owned | yes |
| Open Banking / FCA / ONS / DWP / Lloyds references | Public benchmarks, cited for calibration context only | Cited, not redistributed; figures are references not datasets | yes |
| UCI Bank Marketing (adapter) | Third-party dataset | **Not included**; adapter self-fetches from source at run time under the source's terms | n/a (excluded) |
| Criteo Uplift (adapter) | Third-party dataset | **Not included**; adapter reads a user-provided copy | n/a (excluded) |
| Streamlit screenshots (`docs/assets/`) | This project's own UI | Author-owned; no third-party assets | yes |
| Fonts / icons | None bundled | — | yes |

## Licence decision

- **Code:** remains **MIT** (`LICENSE`).
- **Generated dataset (proposed):** **CC-BY-4.0** — attribution-friendly for a
  reusable portfolio benchmark and compatible with every included artifact
  above. This is not a guess: the author owns the generator and its output
  outright, and nothing bundled restricts redistribution. The choice is
  confirmable at publication; if the user prefers CC0 or another compatible
  licence, only the data card's licence field changes.

If any compatibility question had remained open, the fallback (Plan 4 §8.5)
was to publish the code and generation recipes while withholding the data
files — not needed here.

# Access Control & Data Minimisation

Sensitive wellbeing data should be seen by as few people as possible, and only by those
whose role requires it. This module adds a **lightweight role-based access control
(RBAC) layer** over the individual-level wellbeing/vulnerability fields, demonstrating
the data-minimisation posture the responsible-growth thesis depends on.

It complements [`src/wellbeing/guardrails.py`](../src/wellbeing/guardrails.py) (which
governs permitted *uses*): this layer governs *who can see* the sensitive data.

## Where it lives

| Concern | Location |
| --- | --- |
| Roles, sensitive-field classification, redaction | [`src/access/rbac.py`](../src/access/rbac.py) |
| Dashboard role selector | "View as role" on the Customer outcomes tab |
| Tests | [`tests/test_rbac.py`](../tests/test_rbac.py) |

## Roles

| Role | May see individual-level sensitive wellbeing data? |
| --- | :---: |
| `analyst` | No — works from aggregate, non-sensitive segments |
| `operations` | No |
| `consumer_duty_reviewer` | Yes — the role exists to support vulnerable customers |
| `admin` | Yes |

## Sensitive fields

Individual-level fields that reveal a customer's vulnerability/wellbeing position
(e.g. `vulnerable_customer_proxy`, `accessibility_need_proxy`, `overdraft_risk_proxy`,
`digital_confidence_score`, `complaint_history_flag`) are classified as sensitive in
`SENSITIVE_WELLBEING_FIELDS`.

## How it's enforced

- `redact_sensitive(frame, role)` drops sensitive columns from a customer-level frame
  for roles that may not view them (the rest of the frame stays usable for aggregates).
- `accessible_segments(role, segments)` filters fairness-slice dimensions, so an
  `analyst` sees aggregate gaps by `income_band` / `digital_confidence_band` but **not**
  the `vulnerable_customer_proxy` segment.
- The dashboard's Customer outcomes tab has a **"View as role"** selector (defaulting to
  the least-privileged `analyst`); switching to `consumer_duty_reviewer` reveals the
  vulnerability segment.

```python
from src.access import accessible_segments, redact_sensitive

redact_sensitive(customer_frame, "analyst")          # sensitive columns removed
accessible_segments("analyst", segments)             # vulnerability segment filtered out
accessible_segments("consumer_duty_reviewer", segments)  # full access
```

## Boundary

This is a **scoped demonstration** of least-privilege / data minimisation, not a
production authorisation system. A regulated deployment would enforce it with real
identity (IAM / SSO), row- and column-level security in the warehouse, audit logging,
and approval workflows — see the "What would be hardened for production" section of the
README.

# Looker Trial Runbook (Plan 3 execution; written in Plan 1, not yet executed)

> **Status:** prepared 2026-07-17. Nothing here has run. The trial may begin only
> when the Plan 1 Section 10.3 readiness gate passes: stable BigQuery relations,
> committed LookML, this runbook, fixture answers recorded, and scheduled
> expiry/cleanup dates.

## Pre-activation gate (all must be true)

- [ ] BigQuery governed relations exist and contain stable fields (Plan 3 Tasks 1–8 complete)
- [ ] LookML files committed and reviewed (`looker/`)
- [ ] Field inventory maps every field to an interface column (`explore-field-inventory.csv`)
- [ ] Expected fixture answers recorded (`evidence-checklist.md`)
- [ ] Least-privilege BigQuery identity for Looker prepared (read-only on governed datasets; optional scratch dataset write)
- [ ] Trial verified **no-cost** under the actual signup terms at activation time; any billing requirement or auto-conversion documented — auto-renewal is not authorised
- [ ] **Trial expiry** date, evidence-capture dates and cleanup dates in the calendar
- [ ] No credential of any kind committed to the repository

## Execution order

1. **Activate trial** (official Looker trial only; Looker Studio is not a substitute).
2. **BigQuery connection**: create the connection with the least-privilege
   identity; verify with a trivial bounded query; confirm job attribution labels.
3. **Git connection**: connect the repository's `looker/` project; verify pull.
4. **LookML validation**: run the LookML Validator; fix defects test-first in the
   repo, never only in the instance.
5. **SQL validation**: run the SQL Validator against BigQuery.
6. **Assert validation**: run model tests (`tests/model_tests.lkml`) — primary
   keys, join relationships, expected fixture values.
7. **Content validation**: run the Content Validator over the three dashboards.
8. **Manual checks**: drill paths, filters, restricted-field access grants,
   cache/datagroup behaviour, generated SQL inspection for one governed query.
9. **Evidence capture**: follow `evidence-checklist.md` before expiry.
10. **Cleanup**: disable schedules/public links, export permitted LookML and
    evidence, delete or confirm expiry of the trial instance, revoke temporary
    credentials, record the cleanup in `artifacts/plan3/resource-cleanup.md`.

## Failure rule

If an official trial cannot be provisioned or lacks required validation
capability: retain the prepared LookML, record `partial go — BigQuery only`,
do not substitute another BI tool, and do not claim Looker experience.

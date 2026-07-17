# Privacy and Security Review (Plan 4, Task 5)

> **Result: PASS** — no flagged pattern in the release-candidate data, no
> secret in tracked files or git history, no real PII or account formats.
> These checks reduce accidental disclosure; they do **not** certify privacy in
> general. Prepared 2026-07-17.

## Automated scans (reproducible)

| Scan | Command | Result |
|---|---|---|
| Release-candidate data (fixtures + contracts) | `python -m tools.release.privacy_scan fixtures contracts` | 0 findings |
| Generated standard data (batch sample) | `python -m tools.release.privacy_scan data/generated/standard/batches` | 0 findings |
| Git history for credential shapes | `git log --all -p \| Select-String AKIA…/PRIVATE KEY/AIza…/service_account` | only code identifiers (no key material) |
| Tracked secret files | `git ls-files \| Select-String .env/credential/.pem/-key.json` | only `.env.example` |

The scanner (`tools/release/privacy_scan.py`, tested by
`tests/evidence/test_privacy_scan.py`) checks for real-looking
emails/phones, AWS/Google/bearer credentials, GCP service-account key JSON,
signed URLs, and card / IBAN / UK sort-code+account formats, while recognising
the project's fictional identifiers (`cus_`/`ref_`/`rwd_`…) and the owner's
allowlisted email in docs.

## Manual review

- **Generated data by design carries no PII:** the event envelope and payload
  schemas never generate names, emails, addresses, or card/account numbers;
  identifiers are salted hashes of `(namespace, seed, sequence)` that cannot be
  reversed to a person and do not resemble real credentials.
- **Protected attributes:** the wellbeing/inclusion proxies live in the batch
  downstream-consumer models, not in the released event dataset; they are not
  part of the synthetic event benchmark.
- **Cloud artifacts:** the Plan 3 run used the authenticated owner identity with
  **no service-account keys minted**; benchmark evidence stores job metadata
  only (no query text, no billing identifiers). The `warehouse_job_evidence`
  mart excludes query text by construction.
- **Screenshots/logs:** `docs/assets/` are the project's own Streamlit UI; no
  private project IDs, billing identifiers or signed URLs appear in committed
  artifacts.

## Residual risk statement

Synthetic generation and these scans reduce the chance of accidental
disclosure; they are not a guarantee of privacy. Anyone reusing the data should
treat it as a synthetic engineering benchmark, not as representative of, or safe
to map onto, any real population.

## Security reporting

Vulnerabilities or accidental-disclosure concerns: open a private issue or
contact the maintainer (see repository profile). No credentials are stored in
the repository.

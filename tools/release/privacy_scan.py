"""Privacy and secret scan for the release candidate (Plan 4, Task 5).

Scans a set of files for patterns that must never appear in a public
synthetic-data release: real-looking emails/phones, credential-shaped strings,
private GCP project ids, signed URLs, and real bank/card/account-number
formats. Fictional Route C identifiers (cus_/ref_/rwd_/... hex) are recognised
and not flagged.

These checks reduce accidental disclosure; they do not certify privacy in
general (Plan 4 §8.6).

Usage: python -m tools.release.privacy_scan <path> [<path> ...]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (name, compiled pattern). Ordered most-specific first.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("gcp_service_account_key", re.compile(r'"type"\s*:\s*"service_account"')),
    ("bearer_token", re.compile(r"(?i)bearer\s+[a-z0-9._\-]{20,}")),
    ("signed_url", re.compile(r"[?&](X-Goog-Signature|Signature|Expires)=")),
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("uk_phone", re.compile(r"\b(?:\+44\s?7\d{3}|\(?07\d{3}\)?)\s?\d{3}\s?\d{3}\b")),
    ("card_number", re.compile(r"\b(?:4\d{3}|5[1-5]\d{2})(?:[ \-]?\d{4}){3}\b")),
    ("iban", re.compile(r"\bGB\d{2}[A-Z]{4}\d{14}\b")),
    ("uk_sort_and_account", re.compile(r"\b\d{2}-\d{2}-\d{2}\s+\d{8}\b")),
]

# Emails/domains that are allowed to appear (project's own, in docs/config).
EMAIL_ALLOWLIST = {
    "rosscyking@gmail.com",
    "rosscyking1115@gmail.com",
    "rosscykinglabs@gmail.com",
    "leaffeng1115@gmail.com",
    "abc@domain.com",  # placeholder in the trial-form guidance
}

# Files/dirs where project-owned emails and config are expected (not data).
NON_DATA_SUFFIXES = {".md", ".toml", ".yml", ".yaml", ".cfg", ".lkml", ".txt"}


def scan_text(name: str, text: str, is_data: bool) -> list[str]:
    findings: list[str] = []
    for label, pattern in PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if label == "email":
                if value.lower() in EMAIL_ALLOWLIST:
                    continue
                # Project-owned emails only allowed outside data files.
                if not is_data and value.lower().endswith("@gmail.com"):
                    continue
            findings.append(f"{name}: {label}: {value[:60]}")
    return findings


def scan_paths(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
        for file in files:
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            is_data = file.suffix.lower() not in NON_DATA_SUFFIXES
            findings.extend(scan_text(str(file.relative_to(ROOT) if ROOT in file.parents else file),
                                      text, is_data))
    return findings


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    targets = [Path(a) for a in argv] or [ROOT / "fixtures", ROOT / "contracts"]
    findings = scan_paths(targets)
    for finding in findings:
        print(finding, file=sys.stderr)
    print(f"privacy scan: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

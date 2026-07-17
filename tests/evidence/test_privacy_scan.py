"""Privacy/secret scan tests.

The committed release-candidate data must be clean, and the scanner must detect
seeded real-looking contact strings, credentials and card/account formats
without scanning unrelated private paths.
"""

from pathlib import Path

from tools.release.privacy_scan import scan_paths, scan_text

ROOT = Path(__file__).resolve().parents[2]


def test_committed_fixtures_and_contracts_are_clean() -> None:
    findings = scan_paths([ROOT / "fixtures", ROOT / "contracts"])
    assert findings == [], "release-candidate data must contain no flagged patterns:\n" + "\n".join(
        findings
    )


def test_generated_standard_data_is_clean_if_present() -> None:
    standard = ROOT / "data" / "generated" / "standard"
    if not standard.exists():
        return
    # Scan a sample of batch files (data, not docs).
    batches = sorted((standard / "batches").glob("*.jsonl"))[:10]
    findings = scan_paths(batches)
    assert findings == [], "generated standard data must be clean:\n" + "\n".join(findings)


def test_seeded_email_is_detected() -> None:
    findings = scan_text("evil.jsonl", '{"email": "victim@realbank.co.uk"}', is_data=True)
    assert any("email" in f for f in findings)


def test_seeded_card_and_account_are_detected() -> None:
    card = scan_text("evil.jsonl", '{"card": "4111 1111 1111 1111"}', is_data=True)
    assert any("card_number" in f for f in card)
    account = scan_text("evil.jsonl", '{"detail": "12-34-56 12345678"}', is_data=True)
    assert any("uk_sort_and_account" in f for f in account)


def test_seeded_credentials_are_detected() -> None:
    key = scan_text("evil.env", "AKIAABCDEFGHIJKLMNOP", is_data=True)
    assert any("aws_access_key" in f for f in key)
    sa = scan_text("evil.json", '{"type": "service_account", "project_id": "x"}', is_data=True)
    assert any("gcp_service_account_key" in f for f in sa)


def test_fictional_identifiers_are_not_flagged() -> None:
    sample = '{"customer_id": "cus_a1b2c3d4e5", "referral_id": "ref_000001", "amount_minor": 5000}'
    assert scan_text("ok.jsonl", sample, is_data=True) == []


def test_project_owned_email_allowed_in_docs_not_data() -> None:
    # Owner email in a doc is fine; the same string in a data file is flagged.
    assert scan_text("readme.md", "contact rosscyking@gmail.com", is_data=False) == []
    findings = scan_text("leak.jsonl", "rosscyking@gmail.com", is_data=True)
    assert findings == [], "explicitly allowlisted owner email is not a leak even in data"
    findings2 = scan_text("leak.jsonl", "someone.else@gmail.com", is_data=True)
    assert any("email" in f for f in findings2), "non-owner email in data must flag"

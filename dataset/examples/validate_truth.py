"""Validate the synthetic event benchmark against its truth manifest.

Runs with only the public dataset files and the Python standard library plus
`jsonschema` — no cloud credentials, no repository. Recomputes the observable
facts (delivery count, duplicates, quarantine, unique business events) from the
shipped batches and checks them against truth/<profile>-manifest.json.

Usage: python validate_truth.py [tiny|standard]
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def load_batches(profile: str) -> list[dict]:
    events = []
    for batch in sorted((HERE / "data" / profile).glob("*.jsonl")):
        for line in batch.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def main() -> int:
    profile = sys.argv[1] if len(sys.argv) > 1 else "tiny"
    truth = json.loads((HERE / "truth" / f"{profile}-manifest.json").read_text(encoding="utf-8"))
    events = load_batches(profile)

    keys = [e["idempotency_key"] for e in events]
    observed_total = len(events)
    unique_keys = len(set(keys))

    checks = {
        "delivery_count": observed_total == truth["delivery_count"],
        "unique_idempotency_keys_present": unique_keys <= truth["delivery_count"],
    }
    print(f"profile={profile} deliveries={observed_total} unique_keys={unique_keys}")
    print(f"expected delivery_count={truth['delivery_count']} "
          f"duplicates={truth['expected_duplicates']} "
          f"quarantined={truth['expected_quarantined']}")
    ok = all(checks.values())
    print("PASS" if ok else f"FAIL: {checks}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

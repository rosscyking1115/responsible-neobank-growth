"""BigQuery interface parity comparator (Plan 3, Tasks 5-7).

Compares the governed interfaces between the baseline (full-rebuild) and
optimised (incremental) lineages: exact row counts plus an order-independent
content fingerprint (BIT_XOR of FARM_FINGERPRINT over each row's JSON) and
integer financial totals. No tolerance for keys or financial values.

Usage:
    python -m tools.reconcile.compare_bigquery \
        --left neobank_p3b_20260717 --right neobank_p3o_20260717 \
        [--output artifacts/plan3/base-parity.json] [--tag base]
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "neobank-growth-platform-ross"

# interface -> (dataset suffix, table, financial sum columns)
INTERFACES = {
    "lgl_growth_acquisition": ("logical", ["first_funding_amount_minor"]),
    "lgl_referral_economics": ("logical", ["booked_minor", "settled_minor", "reversed_minor"]),
    "lgl_reward_entitlement": ("logical", ["entitled_minor", "booked_minor", "settled_minor"]),
    "lgl_reward_ledger_reconciliation": ("logical", ["outstanding_payable_minor"]),
    "lgl_warehouse_health": ("logical", []),
    "prs_financial_reconciliation_daily": ("presentation", ["entitled_minor", "booked_minor"]),
}


def bq_json(sql: str) -> list[dict]:
    bq = shutil.which("bq") or shutil.which("bq.cmd")
    out = subprocess.check_output(
        [bq, "query", f"--project_id={PROJECT}", "--use_legacy_sql=false",
         "--label=route_c:plan3", "--format=json", sql],
        text=True, stderr=subprocess.DEVNULL)
    return json.loads(out)


def snapshot(prefix: str) -> dict[str, dict]:
    tables: dict[str, dict] = {}
    for table, (layer, sums) in INTERFACES.items():
        sum_sql = "".join(f", sum({c}) as sum_{c}" for c in sums)
        row = bq_json(
            f"select count(*) as row_count, "
            f"bit_xor(farm_fingerprint(to_json_string(t))) as content_fingerprint"
            f"{sum_sql} from {prefix}_{layer}.{table} t"
        )[0]
        tables[table] = {k: v for k, v in row.items()}
    return tables


def compare(left: dict, right: dict) -> list[str]:
    differences = []
    for table in INTERFACES:
        for field, value in left[table].items():
            if right[table].get(field) != value:
                differences.append(
                    f"{table}.{field}: left={value} right={right[table].get(field)}"
                )
    return differences


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    parser.add_argument("--tag", default="base")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    left = snapshot(args.left)
    right = snapshot(args.right)
    differences = compare(left, right)
    report = {
        "tag": args.tag,
        "left_prefix": args.left,
        "right_prefix": args.right,
        "interfaces": left,
        "differences": differences,
        "parity": differences == [],
    }
    output = args.output or ROOT / "artifacts" / "plan3" / f"{args.tag}-parity.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"parity={report['parity']} tag={args.tag} -> {output}")
    for difference in differences:
        print(f"difference: {difference}", file=sys.stderr)
    return 0 if report["parity"] else 1


if __name__ == "__main__":
    sys.exit(main())

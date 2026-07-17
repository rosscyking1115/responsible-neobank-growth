"""Local end-to-end verification of the Plan 2 pipeline (Plan 2, Task 12).

Reproduces every mandatory CI stage from the current checkout and fails when a
truth/reconciliation artifact is missing at the end. This is the single
command behind the Plan 2 acceptance evidence:

    uv run python -m tools.ci.verify_plan2
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STAGES: list[tuple[str, list[str]]] = [
    ("lint", ["ruff", "check", "."]),
    ("unit-tests", ["python", "-m", "pytest", "-q"]),
    (
        "generate-a",
        ["python", "-m", "src.event_simulator.cli", "generate", "--profile", "tiny",
         "--output", "data/generated/tiny-a"],
    ),
    (
        "generate-b",
        ["python", "-m", "src.event_simulator.cli", "generate", "--profile", "tiny",
         "--output", "data/generated/tiny-b"],
    ),
    (
        "determinism",
        ["python", "-m", "src.event_simulator.cli", "compare",
         "--left", "data/generated/tiny-a", "--right", "data/generated/tiny-b"],
    ),
    (
        "load",
        ["python", "-m", "src.ingestion.event_loader", "--source", "data/generated/tiny-a",
         "--warehouse", "data/warehouse"],
    ),
    (
        # The legacy graph still reads the batch generator's output (preserved
        # consumers); a clean checkout has neither, so generate both worlds.
        "generate-batch-raw",
        ["python", "-m", "data_generator.generate", "--users", "5000", "--months", "6",
         "--seed", "42", "--output-dir", "raw/ci"],
    ),
    (
        "dbt-build",
        ["dbt", "build", "--project-dir", "dbt_neobank", "--profiles-dir", "dbt_neobank",
         "--target", "dev"],
    ),
    (
        "standards",
        ["python", "-m", "tools.standards.check_dbt_interfaces",
         "--manifest", "dbt_neobank/target/manifest.json",
         "--json-output", "artifacts/plan2/standards-report.json"],
    ),
    (
        "blue-green",
        ["python", "-m", "tools.reconcile.compare_interfaces", "--scenario", "all"],
    ),
    (
        "pipeline-tests",
        ["python", "-m", "pytest", "tests/oracles", "tests/migration", "tests/standards", "-q"],
    ),
]

REQUIRED_ARTIFACTS = [
    "artifacts/plan2/blue-green-report.json",
    "artifacts/plan2/standards-report.json",
    "artifacts/plan2/backfill-log.jsonl",
    "dbt_neobank/target/run_results.json",
    "data/generated/tiny-a/manifest.json",
]


def _resolve(executable: str) -> str:
    found = shutil.which(executable)
    if not found:
        raise RuntimeError(f"{executable} not found on PATH (run via `uv run`)")
    return found


def main() -> int:
    results: dict[str, str] = {}
    for name, command in STAGES:
        command = list(command)
        if command[0] in {"ruff", "dbt"}:
            command[0] = _resolve(command[0])
        elif command[0] == "python":
            command[0] = sys.executable
        print(f"--- stage: {name}")
        completed = subprocess.run(command, cwd=ROOT)
        results[name] = "pass" if completed.returncode == 0 else "fail"
        if completed.returncode != 0:
            print(f"stage {name} failed", file=sys.stderr)
            break

    missing = [a for a in REQUIRED_ARTIFACTS if not (ROOT / a).exists()]
    with open(ROOT / "artifacts" / "plan2" / "blue-green-report.json", encoding="utf-8") as f:
        parity = json.load(f).get("parity") is True

    summary = {
        "stages": results,
        "missing_artifacts": missing,
        "blue_green_parity": parity,
        "ok": all(v == "pass" for v in results.values())
        and len(results) == len(STAGES)
        and not missing
        and parity,
    }
    out = ROOT / "artifacts" / "plan2" / "local-verification.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

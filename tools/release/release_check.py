"""Release-candidate check (Plan 4, Task 11).

Fails for a dirty working tree, failed gates, broken evidence/dataset links,
missing licence, or a mismatched dataset build manifest. This is the gate that
must pass before the candidate is presented for publication approval; it does
not tag or publish anything.

Usage: python -m tools.release.release_check
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr)


def check() -> list[str]:
    failures: list[str] = []

    # 1. Clean working tree.
    code, out = _run(["git", "status", "--porcelain"])
    if out.strip():
        failures.append("working tree is dirty; commit or stash before release")

    # 2. Required release files exist.
    required = [
        "LICENSE",
        "README.md",
        "docs/release/release-notes.md",
        "docs/release/source-rights-inventory.md",
        "docs/release/privacy-security-review.md",
        "evidence/registry.yml",
        "dataset/build-manifest.json",
        "dataset/README.md",
        "docs/case-study/analytics-engineering-case-study.md",
    ]
    for rel in required:
        if not (ROOT / rel).exists():
            failures.append(f"missing required release file: {rel}")

    # 3. Version is stated.
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'version = "1.0.0"' not in pyproject:
        failures.append("pyproject version is not the release version 1.0.0")

    # 4. Dataset build manifest is on the release branch.
    if (ROOT / "dataset" / "build-manifest.json").exists():
        manifest = json.loads((ROOT / "dataset" / "build-manifest.json").read_text())
        if manifest.get("release_branch") != "bigquery-only":
            failures.append("dataset build manifest is not on the bigquery-only branch")

    # 5. Gate scripts pass.
    for name, cmd in [
        ("claim audit", [sys.executable, "-m", "tools.release.claim_audit"]),
        ("privacy scan", [sys.executable, "-m", "tools.release.privacy_scan",
                          "fixtures", "contracts", "dataset"]),
    ]:
        code, _ = _run(cmd)
        if code != 0:
            failures.append(f"{name} reported findings")

    return failures


def main() -> int:
    failures = check()
    for failure in failures:
        print(f"release-check: {failure}", file=sys.stderr)
    print(f"release check: {'READY' if not failures else str(len(failures)) + ' blocker(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

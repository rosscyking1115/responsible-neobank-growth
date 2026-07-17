"""Standards-as-code checker for governed Route C interfaces (Plan 1, Task 8).

Prototype scope: inspects dbt-artifact-shaped JSON (``nodes`` keyed by unique
id, each with ``name``, ``resource_type`` and ``config.meta``) and reports one
violation per broken rule. It deliberately does not recreate dbt; Plan 2 points
it at the real ``manifest.json`` in CI.

Usage:
    python -m tools.standards.check_dbt_interfaces \
        --manifest path/to/manifest.json [--rules tools/standards/rules.yml] \
        [--json-output report.json]

Exit code 0 when no governed model violates a rule, 1 otherwise.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

DEFAULT_RULES = Path(__file__).resolve().parent / "rules.yml"


def load_rules(path: Path = DEFAULT_RULES) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _meta(node: dict) -> dict:
    config = node.get("config", {})
    meta = dict(node.get("meta", {}))
    meta.update(config.get("meta", {}))
    return meta


def _is_governed(node: dict, rules: dict) -> bool:
    if node.get("resource_type") != "model":
        return False
    if _meta(node).get("governed") is True:
        return True
    return node.get("name", "").startswith(tuple(rules["governed_prefixes"]))


def _requirement_value(node: dict, meta: dict, key: str):
    """Resolve a required declaration, accepting manifest-native equivalents:
    purpose falls back to the model description; unique_key falls back to the
    incremental config's unique_key."""
    value = meta.get(key)
    if value in (None, "", [], {}):
        if key == "purpose":
            value = node.get("description")
        elif key == "unique_key":
            value = node.get("config", {}).get("unique_key")
    return value


def check_manifest(manifest: dict, rules: dict) -> list[dict]:
    """Return one violation dict per broken rule: {model, rule, message}."""
    violations: list[dict] = []
    for node in manifest.get("nodes", {}).values():
        if not _is_governed(node, rules):
            continue
        name = node["name"]
        meta = _meta(node)

        for requirement in rules["required_meta"]:
            value = _requirement_value(node, meta, requirement["key"])
            if value in (None, "", [], {}):
                violations.append(
                    {
                        "model": name,
                        "rule": requirement["rule"],
                        "message": f"{name}: {requirement['message']}",
                    }
                )

        incremental_rule = rules["incremental"]
        materialized = node.get("config", {}).get("materialized")
        if materialized != "incremental" and not meta.get(incremental_rule["exemption_key"]):
            violations.append(
                {
                    "model": name,
                    "rule": incremental_rule["rule"],
                    "message": f"{name}: {incremental_rule['message']}",
                }
            )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--json-output", type=Path, default=None)
    args = parser.parse_args(argv)

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)
    violations = check_manifest(manifest, load_rules(args.rules))

    if args.json_output:
        args.json_output.write_text(
            json.dumps({"violations": violations}, indent=2) + "\n", encoding="utf-8"
        )

    if violations:
        print(f"{len(violations)} standards violation(s):")
        for violation in violations:
            print(f"  [{violation['rule']}] {violation['message']}")
        return 1
    print("all governed interfaces satisfy the standards rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())

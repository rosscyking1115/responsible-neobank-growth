"""Render a release decision as a stakeholder-readable markdown memo."""

from __future__ import annotations

from src.release_decisions.decision_engine import ReleaseDecision

_HEADLINE = {
    "ship": "SHIP",
    "limited_rollout": "LIMITED ROLLOUT",
    "experiment_only": "EXPERIMENT ONLY",
    "needs_human_review": "NEEDS HUMAN REVIEW",
    "block": "BLOCK",
}


def render_decision_markdown(decision: ReleaseDecision) -> str:
    lines = [
        f"# Release decision: {_HEADLINE[decision.decision]}",
        "",
        f"- Feature: `{decision.feature_name}`",
        f"- Decision: `{decision.decision}`",
        f"- Evidence tier: `{decision.evidence_tier}`",
        "",
        "## Why",
        "",
        *[f"- {reason}" for reason in decision.reasons],
        "",
        "## Guardrail checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in decision.checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.append("")
    return "\n".join(lines)

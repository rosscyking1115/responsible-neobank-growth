"""Lifecycle state machines and truth capture.

Transitions are locked by the reward-reconciliation contract
(docs/contracts/reward-reconciliation.md): invited -> qualified -> booked ->
settled, with reversed as an alternative terminal after booking. Anything else
raises before an event can be emitted.
"""

from dataclasses import dataclass, field

ALLOWED_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"invited"},
    "invited": {"qualified"},
    "qualified": {"booked"},
    "booked": {"settled", "reversed"},
    "settled": set(),
    "reversed": set(),
}


class LifecycleError(ValueError):
    """Raised on a transition the reward-reconciliation contract does not allow."""


class ReferralLifecycle:
    def __init__(self, referral_id: str):
        self.referral_id = referral_id
        self.state: str | None = None

    def advance(self, new_state: str) -> str:
        allowed = ALLOWED_TRANSITIONS[self.state]
        if new_state not in allowed:
            raise LifecycleError(
                f"{self.referral_id}: cannot move from {self.state!r} to {new_state!r}; "
                f"allowed next states: {sorted(allowed) or 'none (terminal state reached)'}"
            )
        self.state = new_state
        return new_state


@dataclass
class GenerationTruth:
    """Exact truth captured while generating (extended by manifests)."""

    event_counts: dict[str, int] = field(default_factory=dict)
    referral_end_states: dict[str, str] = field(default_factory=dict)
    entitled_minor: int = 0
    booked_minor: int = 0
    settled_minor: int = 0
    reversed_minor: int = 0

    def count(self, event_name: str) -> None:
        self.event_counts[event_name] = self.event_counts.get(event_name, 0) + 1


@dataclass
class GenerationResult:
    events: list[dict]
    truth: GenerationTruth

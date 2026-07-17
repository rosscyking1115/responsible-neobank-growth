"""Deterministic UTC virtual clock (Plan 2 section 5.4)."""

from datetime import UTC, datetime, timedelta


class VirtualClock:
    """A forward-only clock that starts where the config says and never reads
    the wall clock."""

    def __init__(self, start: datetime):
        if start.tzinfo is None or start.utcoffset() != timedelta(0):
            raise ValueError("virtual clock requires a timezone-aware UTC datetime")
        self._now = start.astimezone(UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> datetime:
        if delta < timedelta(0):
            raise ValueError("virtual clock cannot move backward")
        self._now += delta
        return self._now

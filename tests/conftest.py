"""Shared pytest configuration.

Redirect the backfill log to a temp path so running the suite (which exercises
the incremental/backfill harness) never churns the committed Plan 2 evidence
snapshot at ``artifacts/plan2/backfill-log.jsonl``.
"""

import os
import tempfile
from pathlib import Path

_TEST_BACKFILL_LOG = Path(tempfile.gettempdir()) / "route-c-test-backfill-log.jsonl"
os.environ.setdefault("NEOBANK_BACKFILL_LOG", str(_TEST_BACKFILL_LOG))

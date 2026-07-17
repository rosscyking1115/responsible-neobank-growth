"""Deterministic identity derivation.

Identifiers are derived from (namespace, seed, sequence) via SHA-256 — never
from random UUIDs or unseeded randomness — so the same configuration always
emits the same entities. Formats satisfy the envelope/payload schema patterns
and never resemble real account credentials.
"""

import hashlib


class DeterministicIds:
    def __init__(self, seed: int):
        self._seed = seed

    def _digest(self, namespace: str, sequence: int | str, length: int) -> str:
        material = f"{self._seed}:{namespace}:{sequence}".encode()
        return hashlib.sha256(material).hexdigest()[:length]

    def customer_id(self, sequence: int) -> str:
        return f"cus_{self._digest('customer', sequence, 10)}"

    def application_id(self, sequence: int) -> str:
        return f"app_{self._digest('application', sequence, 10)}"

    def account_id(self, sequence: int) -> str:
        return f"acc_{self._digest('account', sequence, 10)}"

    def referral_id(self, sequence: int) -> str:
        return f"ref_{self._digest('referral', sequence, 10)}"

    def reward_id(self, sequence: int) -> str:
        return f"rwd_{self._digest('reward', sequence, 10)}"

    def settlement_id(self, sequence: int) -> str:
        return f"stl_{self._digest('settlement', sequence, 10)}"

    def reversal_id(self, sequence: int) -> str:
        return f"rev_{self._digest('reversal', sequence, 10)}"

    def event_id(self, event_name: str, sequence: int) -> str:
        return f"evt_{self._digest(f'event:{event_name}', sequence, 16)}"

    def idempotency_key(self, business_key: str) -> str:
        return f"idk_{self._digest('idempotency', business_key, 16)}"

    def trace_id(self, workflow: str) -> str:
        return f"trc_{self._digest('trace', workflow, 12)}"

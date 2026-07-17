"""Deterministic synthetic event simulator for the synthetic event benchmark.

Everything in this package must be reproducible from (profile config, seed):
time comes from the virtual clock, identities from seeded derivation, and
randomness only from explicitly seeded generators. Wall-clock time, random
UUIDs and unordered iteration are prohibited in deterministic paths (enforced
by tests/event_simulator/test_config.py).
"""

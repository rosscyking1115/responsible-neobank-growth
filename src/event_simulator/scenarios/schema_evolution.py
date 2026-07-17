"""Schema-evolution scenario: v1 and v2 referral-qualified payloads coexist in
one deterministic stream (emitted by valid generation per the configured v2
share). This module summarises the coexistence for the truth manifest; the
normalised layer must adapt both versions to one canonical meaning."""


def summarise(deliveries) -> dict:
    v1 = sum(
        1
        for e in deliveries
        if e["event_name"] == "referral-qualified" and e["schema_version"] == 1
    )
    v2 = sum(
        1
        for e in deliveries
        if e["event_name"] == "referral-qualified" and e["schema_version"] == 2
    )
    return {"referral_qualified_v1": v1, "referral_qualified_v2": v2}

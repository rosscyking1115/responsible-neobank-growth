"""Configurable risk weights and thresholds for scam-intervention simulation."""

from __future__ import annotations

from dataclasses import dataclass

# Signal weights summed into a 0..1 risk score. Positive signals raise risk; an
# explicit customer confirmation or a heeded warning slightly lower it (the customer
# engaged with the protective step).
RISK_WEIGHTS: dict[str, float] = {
    "new_payee": 0.20,
    "first_large_transfer": 0.25,
    "large_amount": 0.20,
    "unusual_time": 0.10,
    "recent_device_change": 0.20,
    "ignored_warning": 0.25,
    "support_contact_about_scam": 0.30,
    "investment_context": 0.20,
    "vulnerable_customer": 0.15,
    "confirmed_transfer": -0.15,
    "viewed_warning_heeded": -0.05,
}


@dataclass(frozen=True)
class ProtectionThresholds:
    large_amount_gbp: float = 1000.0
    low_risk: float = 0.20
    medium_risk: float = 0.45
    high_risk: float = 0.70


DEFAULT_PROTECTION_THRESHOLDS = ProtectionThresholds()

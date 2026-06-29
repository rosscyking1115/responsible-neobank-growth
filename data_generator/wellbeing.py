"""Synthetic customer financial-wellbeing proxies.

These fields are a SIMULATION layer for evaluating product decisions responsibly.
They are not a real vulnerability classifier and must never be used for punitive,
credit-eligibility, pricing, or service-denial decisions. See
``src/wellbeing/guardrails.py`` and ``docs/FINANCIAL_WELLBEING_PROXIES.md``.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from data_generator.config import GeneratorConfig

# Offset the wellbeing RNG stream so it does not collide with the users generator
# while staying deterministic for a given config seed.
WELLBEING_SEED_OFFSET = 101

INCOME_BAND_BY_SEGMENT = {
    "student": "low",
    "low": "low",
    "middle": "medium",
    "high": "high",
    "affluent": "high",
}

# Baseline (income-volatility, salary-regularity, cash-buffer, bill-pressure) priors
# per income segment. Higher volatility / bill pressure and lower buffer / regularity
# indicate more financial strain.
SEGMENT_PRIORS = {
    "student": (0.62, 0.45, 0.22, 0.60),
    "low": (0.58, 0.50, 0.20, 0.66),
    "middle": (0.38, 0.70, 0.45, 0.42),
    "high": (0.26, 0.82, 0.66, 0.28),
    "affluent": (0.20, 0.88, 0.78, 0.20),
}


def _clip01(values: np.ndarray) -> np.ndarray:
    return np.clip(values, 0.0, 1.0)


def generate_wellbeing_proxies(users: pl.DataFrame, config: GeneratorConfig) -> pl.DataFrame:
    """Derive synthetic per-customer wellbeing proxies from the users frame.

    Proxies are correlated with income segment, age, and the existing vulnerable
    flag so that downstream fairness and inclusion analysis is meaningful, with
    independent noise so segments are not perfectly separable.
    """

    rng = np.random.default_rng(config.seed + WELLBEING_SEED_OFFSET)
    n = users.height

    user_id = users.get_column("user_id").to_numpy()
    income_segment = users.get_column("income_segment").to_numpy()
    age = users.get_column("age").to_numpy().astype(float)
    device_os = users.get_column("device_os").to_numpy()
    signup_channel = users.get_column("signup_channel").to_numpy()
    vulnerable_flag = users.get_column("vulnerable_customer_flag").to_numpy().astype(bool)

    income_band = np.array([INCOME_BAND_BY_SEGMENT[seg] for seg in income_segment])
    priors = np.array([SEGMENT_PRIORS[seg] for seg in income_segment])
    volatility_base, regularity_base, buffer_base, bill_base = priors.T

    noise = lambda scale: rng.normal(0.0, scale, size=n)  # noqa: E731

    income_volatility_score = _clip01(volatility_base + noise(0.08))
    salary_regularity_score = _clip01(regularity_base + noise(0.08))
    cash_buffer_proxy = _clip01(buffer_base + noise(0.08))
    bill_pressure_score = _clip01(bill_base + noise(0.08))

    # Overdraft risk rises with bill pressure and volatility, falls with cash buffer.
    overdraft_risk_proxy = _clip01(
        0.55 * bill_pressure_score
        + 0.30 * income_volatility_score
        - 0.35 * cash_buffer_proxy
        + 0.20
        + noise(0.05)
    )
    missed_payment_proxy = (rng.random(n) < (overdraft_risk_proxy * 0.35)).astype(bool)

    # Digital confidence falls with age and is a little higher on iOS; lower for the
    # most strained segments.
    digital_confidence_score = _clip01(
        0.92
        - (age - 25.0) / 90.0
        + np.where(device_os == "ios", 0.04, -0.02)
        - 0.10 * bill_pressure_score
        + noise(0.06)
    )

    support_contact_frequency = np.maximum(
        0,
        rng.poisson(
            0.4 + 1.2 * (1.0 - digital_confidence_score) + 0.8 * vulnerable_flag
        ),
    ).astype(int)
    complaint_history_flag = (
        rng.random(n) < (0.02 + 0.06 * vulnerable_flag + 0.04 * bill_pressure_score)
    ).astype(bool)

    accessibility_need_proxy = (
        rng.random(n) < (0.05 + np.where(age >= 65, 0.18, 0.0))
    ).astype(bool)
    new_to_uk_proxy = (
        rng.random(n) < (0.06 + np.where(signup_channel == "campus", 0.05, 0.0))
    ).astype(bool)
    student_proxy = (income_segment == "student") | (rng.random(n) < 0.02)

    # The proxy carries the existing flag forward and additionally flags customers
    # with a strong strain signal, so it is a superset of the source flag.
    strain_signal = (overdraft_risk_proxy > 0.7) & (cash_buffer_proxy < 0.2)
    vulnerable_customer_proxy = vulnerable_flag | strain_signal

    return pl.DataFrame(
        {
            "customer_id": user_id,
            "income_band": income_band,
            "income_volatility_score": np.round(income_volatility_score, 4),
            "salary_regularity_score": np.round(salary_regularity_score, 4),
            "cash_buffer_proxy": np.round(cash_buffer_proxy, 4),
            "bill_pressure_score": np.round(bill_pressure_score, 4),
            "overdraft_risk_proxy": np.round(overdraft_risk_proxy, 4),
            "missed_payment_proxy": missed_payment_proxy,
            "support_contact_frequency": support_contact_frequency,
            "complaint_history_flag": complaint_history_flag,
            "digital_confidence_score": np.round(digital_confidence_score, 4),
            "accessibility_need_proxy": accessibility_need_proxy,
            "new_to_uk_proxy": new_to_uk_proxy,
            "student_proxy": student_proxy,
            "vulnerable_customer_proxy": vulnerable_customer_proxy,
        }
    )

"""Deterministic baseline scoring for the first API contract."""

from __future__ import annotations

from math import exp

from api.schemas import (
    CustomerFeatures,
    GuardrailFlag,
    OfferRecommendationResponse,
    PricingScenarioRequest,
    PricingScenarioResponse,
    ScoreResponse,
    ScoreType,
)

MODEL_VERSION = "baseline-rules-2026-05-29"
CONTRACT_VERSION = "v1"
DATA_VERSION = "synthetic-local"


def _sigmoid(value: float) -> float:
    return 1 / (1 + exp(-value))


def _clip_probability(value: float) -> float:
    return round(min(max(value, 0.01), 0.99), 4)


def customer_guardrails(customer: CustomerFeatures) -> list[GuardrailFlag]:
    flags = [
        GuardrailFlag(
            name="minimum_age",
            severity="block",
            passed=customer.age >= 18,
            message="Customer is 18 or older.",
        ),
        GuardrailFlag(
            name="vulnerable_customer_review",
            severity="warn",
            passed=not customer.vulnerable_customer_flag,
            message="Manual review required before incentive targeting.",
        ),
    ]
    return flags


def _feature_score(customer: CustomerFeatures) -> float:
    channel_lift = {
        "organic_search": 0.35,
        "app_store": 0.25,
        "word_of_mouth": 0.20,
        "partnership": 0.10,
        "paid_social": -0.05,
        "campus": 0.15,
        "business_referral": 0.30,
    }.get(customer.signup_channel, 0.0)
    income_lift = {
        "affluent": 0.35,
        "high": 0.20,
        "middle": 0.05,
        "student": -0.05,
        "low": -0.15,
    }.get(customer.income_segment, 0.0)
    engagement_lift = min(customer.weekly_sessions, 10) * 0.06
    spend_lift = min(customer.monthly_card_spend_gbp, 2000) / 2000 * 0.45
    opt_in_lift = 0.12 if customer.push_opt_in else -0.10
    business_lift = 0.18 if customer.business_account_flag else 0.0
    feature_lift = 0.12 if customer.adopted_savings_pot else 0.0
    return (
        channel_lift
        + income_lift
        + engagement_lift
        + spend_lift
        + opt_in_lift
        + business_lift
        + feature_lift
    )


def score_customer(customer: CustomerFeatures, score_type: ScoreType) -> ScoreResponse:
    raw = _feature_score(customer)
    if score_type == "activation":
        probability = _clip_probability(_sigmoid(-0.35 + raw - customer.days_since_signup * 0.015))
        threshold = 0.52
        reason_codes = ["signup_quality", "engagement_intent", "channel_activation_prior"]
    elif score_type == "churn":
        inactivity = max(0, 4 - customer.weekly_sessions) * 0.24
        low_spend = 0.28 if customer.monthly_card_spend_gbp < 50 else -0.15
        probability = _clip_probability(_sigmoid(-0.25 + inactivity + low_spend - raw * 0.4))
        threshold = 0.45
        reason_codes = ["recent_engagement", "spend_depth", "feature_adoption"]
    else:
        probability = _clip_probability(
            _sigmoid(-0.60 + raw + customer.monthly_card_spend_gbp / 2500)
        )
        threshold = 0.50
        reason_codes = ["value_potential", "product_fit", "engagement_depth"]

    guardrails = customer_guardrails(customer)
    if any(flag.severity == "block" and not flag.passed for flag in guardrails):
        decision = "do_not_target"
    elif probability >= threshold and not customer.vulnerable_customer_flag:
        decision = "target"
    else:
        decision = "monitor"

    return ScoreResponse(
        customer_id=customer.customer_id,
        score_type=score_type,
        probability=probability,
        threshold=threshold,
        decision=decision,
        model_version=MODEL_VERSION,
        reason_codes=reason_codes,
        guardrails=guardrails,
    )


def recommend_offer(
    customer: CustomerFeatures,
    *,
    max_monthly_incentive_gbp: float,
) -> OfferRecommendationResponse:
    upsell = score_customer(customer, "upsell")
    if customer.business_account_flag:
        offer = "business_cashback_trial"
        margin = 8.5
        reasons = ["business_account_fit", "higher_expected_margin"]
    elif not customer.adopted_savings_pot:
        offer = "savings_pot_setup_prompt"
        margin = 4.2
        reasons = ["missing_savings_pot", "activation_depth"]
    elif not customer.adopted_salary_sorter:
        offer = "salary_sorter_prompt"
        margin = 3.8
        reasons = ["salary_sorter_gap", "primary_bank_signal"]
    else:
        offer = "referral_incentive_test"
        margin = 2.5
        reasons = ["feature_depth", "network_growth_potential"]

    guardrails = customer_guardrails(customer)
    if max_monthly_incentive_gbp > margin:
        guardrails.append(
            GuardrailFlag(
                name="unit_economics",
                severity="warn",
                passed=False,
                message="Configured incentive is above expected monthly margin.",
            )
        )

    return OfferRecommendationResponse(
        customer_id=customer.customer_id,
        recommended_offer=offer,
        expected_upsell_probability=upsell.probability,
        expected_monthly_margin_gbp=round(margin * upsell.probability, 2),
        max_monthly_incentive_gbp=max_monthly_incentive_gbp,
        reason_codes=reasons,
        guardrails=guardrails,
    )


def simulate_pricing_scenario(request: PricingScenarioRequest) -> PricingScenarioResponse:
    incentive_delta = request.proposed_incentive_gbp - request.current_incentive_gbp
    segment_sensitivity = {
        "student": 0.018,
        "low": 0.014,
        "middle": 0.010,
        "high": 0.006,
        "affluent": 0.004,
    }.get(request.segment, 0.008)
    vulnerable_penalty = request.vulnerable_customer_share * 0.02
    projected_lift = max(0.0, min(incentive_delta * segment_sensitivity - vulnerable_penalty, 0.08))
    projected_rate = min(request.baseline_activation_rate + projected_lift, 0.95)
    incremental_customers = round(request.eligible_customers * projected_lift)
    incremental_cost = incremental_customers * request.proposed_incentive_gbp
    expected_margin = (
        incremental_customers * request.expected_monthly_margin_per_activated_customer_gbp
        - incremental_cost
    )

    guardrails = [
        GuardrailFlag(
            name="positive_unit_economics",
            severity="warn",
            passed=expected_margin >= 0,
            message="Projected first-month margin is non-negative.",
        ),
        GuardrailFlag(
            name="vulnerable_customer_share",
            severity="warn",
            passed=request.vulnerable_customer_share <= 0.20,
            message="Vulnerable-customer share is within review threshold.",
        ),
    ]
    if expected_margin > 0 and all(flag.passed for flag in guardrails):
        recommendation = "ship"
    elif projected_lift > 0 and request.proposed_incentive_gbp <= 10:
        recommendation = "iterate"
    else:
        recommendation = "hold"

    return PricingScenarioResponse(
        segment=request.segment,
        projected_activation_rate=round(projected_rate, 4),
        projected_lift_pp=round(projected_lift * 100, 2),
        incremental_activated_customers=incremental_customers,
        incremental_incentive_cost_gbp=round(incremental_cost, 2),
        expected_monthly_margin_gbp=round(expected_margin, 2),
        recommendation=recommendation,
        reason_codes=["segment_price_response", "unit_economics", "customer_guardrails"],
        guardrails=guardrails,
    )

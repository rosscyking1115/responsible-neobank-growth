"""Typed API contracts for customer scoring and pricing scenarios."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ScoreType = Literal["activation", "churn", "upsell"]
Decision = Literal["target", "monitor", "do_not_target"]
GuardrailSeverity = Literal["info", "warn", "block"]


class CustomerFeatures(BaseModel):
    customer_id: str = Field(..., min_length=1, examples=["cust_000123"])
    region: str = Field(..., min_length=1, examples=["London"])
    signup_channel: str = Field(..., min_length=1, examples=["organic_search"])
    device_os: str = Field(..., min_length=1, examples=["ios"])
    income_segment: str = Field(..., min_length=1, examples=["middle"])
    age: int = Field(..., ge=16, le=100, examples=[31])
    push_opt_in: bool = Field(default=True)
    vulnerable_customer_flag: bool = Field(default=False)
    business_account_flag: bool = Field(default=False)
    days_since_signup: int = Field(default=0, ge=0)
    weekly_sessions: int = Field(default=0, ge=0)
    monthly_card_spend_gbp: float = Field(default=0.0, ge=0.0)
    adopted_savings_pot: bool = Field(default=False)
    adopted_salary_sorter: bool = Field(default=False)


class ScoreRequest(BaseModel):
    customer: CustomerFeatures


class GuardrailFlag(BaseModel):
    name: str
    severity: GuardrailSeverity
    passed: bool
    message: str


class ScoreResponse(BaseModel):
    customer_id: str
    score_type: ScoreType
    probability: float = Field(..., ge=0.0, le=1.0)
    threshold: float = Field(..., ge=0.0, le=1.0)
    decision: Decision
    model_version: str
    reason_codes: list[str]
    guardrails: list[GuardrailFlag]


class OfferRecommendationRequest(BaseModel):
    customer: CustomerFeatures
    max_monthly_incentive_gbp: float = Field(default=5.0, ge=0.0, le=100.0)


class OfferRecommendationResponse(BaseModel):
    customer_id: str
    recommended_offer: str
    expected_upsell_probability: float = Field(..., ge=0.0, le=1.0)
    expected_monthly_margin_gbp: float
    max_monthly_incentive_gbp: float
    reason_codes: list[str]
    guardrails: list[GuardrailFlag]


class PricingScenarioRequest(BaseModel):
    segment: str = Field(..., min_length=1, examples=["student"])
    eligible_customers: int = Field(..., ge=1, examples=[2500])
    baseline_activation_rate: float = Field(..., ge=0.0, le=1.0, examples=[0.44])
    current_incentive_gbp: float = Field(default=0.0, ge=0.0)
    proposed_incentive_gbp: float = Field(..., ge=0.0, le=100.0, examples=[3.0])
    expected_monthly_margin_per_activated_customer_gbp: float = Field(
        default=4.0,
        ge=0.0,
    )
    vulnerable_customer_share: float = Field(default=0.0, ge=0.0, le=1.0)


class PricingScenarioResponse(BaseModel):
    segment: str
    projected_activation_rate: float = Field(..., ge=0.0, le=1.0)
    projected_lift_pp: float
    incremental_activated_customers: int
    incremental_incentive_cost_gbp: float
    expected_monthly_margin_gbp: float
    recommendation: Literal["ship", "iterate", "hold"]
    reason_codes: list[str]
    guardrails: list[GuardrailFlag]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    contract_version: str
    model_version: str
    data_version: str

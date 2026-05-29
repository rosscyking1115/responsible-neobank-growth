"""FastAPI entrypoint for the customer growth and pricing service."""

from __future__ import annotations

from fastapi import FastAPI

from api.schemas import (
    HealthResponse,
    OfferRecommendationRequest,
    OfferRecommendationResponse,
    PricingScenarioRequest,
    PricingScenarioResponse,
    ScoreRequest,
    ScoreResponse,
)
from api.scoring import (
    CONTRACT_VERSION,
    DATA_VERSION,
    MODEL_VERSION,
    recommend_offer,
    score_customer,
    simulate_pricing_scenario,
)

app = FastAPI(
    title="Customer Growth & Pricing Intelligence API",
    version=CONTRACT_VERSION,
    summary="Prediction and scenario contracts for the synthetic neobank data product.",
)


@app.get("/health", response_model=HealthResponse, tags=["service"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="customer-growth-pricing-api",
        contract_version=CONTRACT_VERSION,
        model_version=MODEL_VERSION,
        data_version=DATA_VERSION,
    )


@app.post("/score/activation", response_model=ScoreResponse, tags=["scoring"])
def score_activation(request: ScoreRequest) -> ScoreResponse:
    return score_customer(request.customer, "activation")


@app.post("/score/churn", response_model=ScoreResponse, tags=["scoring"])
def score_churn(request: ScoreRequest) -> ScoreResponse:
    return score_customer(request.customer, "churn")


@app.post("/score/upsell", response_model=ScoreResponse, tags=["scoring"])
def score_upsell(request: ScoreRequest) -> ScoreResponse:
    return score_customer(request.customer, "upsell")


@app.post("/recommend/offer", response_model=OfferRecommendationResponse, tags=["recommendation"])
def recommend_customer_offer(request: OfferRecommendationRequest) -> OfferRecommendationResponse:
    return recommend_offer(
        request.customer,
        max_monthly_incentive_gbp=request.max_monthly_incentive_gbp,
    )


@app.post("/simulate/pricing", response_model=PricingScenarioResponse, tags=["pricing"])
def simulate_pricing(request: PricingScenarioRequest) -> PricingScenarioResponse:
    return simulate_pricing_scenario(request)

# API Contract

The Customer Growth & Pricing Intelligence API is the first product-service
boundary for the project. It is intentionally contract-first: the current scorer
is a deterministic baseline, and the next milestone will connect the existing
activation model artifact to the same endpoint shape.

## Run Locally

```powershell
uv run uvicorn api.main:app --reload --port 8000
```

Open the generated OpenAPI docs at:

```text
http://127.0.0.1:8000/docs
```

## Container Smoke Run

```powershell
docker build -f Dockerfile.api -t neobank-api .
docker run --rm -p 8080:8080 neobank-api
```

## Endpoints

- `GET /health`: service, contract, model, and data version metadata.
- `POST /score/activation`: D7 activation propensity.
- `POST /score/churn`: churn-risk propensity.
- `POST /score/upsell`: upsell or next-best-action propensity.
- `POST /recommend/offer`: guarded offer recommendation.
- `POST /simulate/pricing`: pricing or incentive scenario simulator.

## Example Scoring Request

```json
{
  "customer": {
    "customer_id": "cust_000123",
    "region": "London",
    "signup_channel": "organic_search",
    "device_os": "ios",
    "income_segment": "middle",
    "age": 31,
    "push_opt_in": true,
    "vulnerable_customer_flag": false,
    "business_account_flag": false,
    "days_since_signup": 3,
    "weekly_sessions": 4,
    "monthly_card_spend_gbp": 240.0,
    "adopted_savings_pot": false,
    "adopted_salary_sorter": false
  }
}
```

## Example Pricing Scenario

```json
{
  "segment": "student",
  "eligible_customers": 2500,
  "baseline_activation_rate": 0.44,
  "current_incentive_gbp": 0.0,
  "proposed_incentive_gbp": 3.0,
  "expected_monthly_margin_per_activated_customer_gbp": 4.0,
  "vulnerable_customer_share": 0.05
}
```

## Guardrails

Responses include guardrail flags so downstream consumers can separate a high
score from a safe decision. The baseline service currently checks minimum age,
vulnerable-customer review, unit economics, and vulnerable-customer share. Future
model-backed versions should preserve these response fields so the dashboard and
batch scoring jobs do not break when the scoring engine changes.

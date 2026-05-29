# API Contract

The Customer Growth & Pricing Intelligence API is the product-service boundary
for the project. It is intentionally contract-first: endpoints keep stable
request and response shapes while the backing logic can move from deterministic
baselines to model artifacts and warehouse marts.

## Run Locally

```powershell
uv run uvicorn api.main:app --reload --port 8000
```

Open the generated OpenAPI docs at:

```text
http://127.0.0.1:8000/docs
```

By default, activation scoring uses the deterministic baseline scorer. To serve a
trained activation model artifact, first run:

```powershell
uv run python -m src.modelling.run_activation_model
```

Then set the registry path before starting the API:

```powershell
$env:NEOBANK_ACTIVATION_MODEL_REGISTRY="artifacts/models/activation/registry.json"
uv run uvicorn api.main:app --reload --port 8000
```

Pricing scenario simulation also has a deterministic fallback. When
`NEOBANK_DUCKDB_PATH` points to a DuckDB database containing
`main_marts.mart_pricing_recommendations`, `/simulate/pricing` calibrates the
scenario from the pricing mart and includes `pricing_mart_response` in the
response reason codes.

For portfolio-level scenario runs and sensitivity outputs, use:

```powershell
uv run python -m src.pricing.scenario_runs --run-date 2025-06-30
```

That command writes JSON, Markdown, and CSV artifacts under
`artifacts/pricing/scenario_runs/`. See `docs/PRICING_SCENARIOS.md`.

## Container Smoke Run

```powershell
docker build -f Dockerfile.api -t neobank-api .
docker run --rm -p 8080:8080 neobank-api
```

The container is Cloud Run compatible and reads the service port from `PORT`.
See `docs/CLOUD_RUN_DEPLOYMENT.md` for deployment, runtime configuration, and
rollback notes.

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
score from a safe decision. The service currently checks minimum age,
vulnerable-customer review, unit economics, vulnerable-customer share, and pricing
mart guardrails when mart evidence is available. Future model-backed versions
should preserve these response fields so the dashboard and batch scoring jobs do
not break when the scoring engine changes.

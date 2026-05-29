from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def sample_customer() -> dict[str, object]:
    return {
        "customer_id": "cust_000123",
        "region": "London",
        "signup_channel": "organic_search",
        "device_os": "ios",
        "income_segment": "middle",
        "age": 31,
        "push_opt_in": True,
        "vulnerable_customer_flag": False,
        "business_account_flag": False,
        "days_since_signup": 3,
        "weekly_sessions": 4,
        "monthly_card_spend_gbp": 240.0,
        "adopted_savings_pot": False,
        "adopted_salary_sorter": False,
    }


def test_health_endpoint_exposes_contract_metadata() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["contract_version"] == "v1"
    assert payload["model_version"].startswith("baseline-rules")


def test_activation_scoring_contract() -> None:
    response = client.post("/score/activation", json={"customer": sample_customer()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "cust_000123"
    assert payload["score_type"] == "activation"
    assert 0 <= payload["probability"] <= 1
    assert payload["decision"] in {"target", "monitor", "do_not_target"}
    assert payload["reason_codes"]
    assert {flag["name"] for flag in payload["guardrails"]} >= {
        "minimum_age",
        "vulnerable_customer_review",
    }


def test_vulnerable_customer_is_not_directly_targeted() -> None:
    customer = sample_customer()
    customer["vulnerable_customer_flag"] = True

    response = client.post("/score/upsell", json={"customer": customer})

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "monitor"
    assert any(
        flag["name"] == "vulnerable_customer_review" and not flag["passed"]
        for flag in payload["guardrails"]
    )


def test_offer_recommendation_contract() -> None:
    response = client.post(
        "/recommend/offer",
        json={"customer": sample_customer(), "max_monthly_incentive_gbp": 3.0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_offer"] == "savings_pot_setup_prompt"
    assert 0 <= payload["expected_upsell_probability"] <= 1
    assert payload["reason_codes"]


def test_pricing_scenario_contract() -> None:
    response = client.post(
        "/simulate/pricing",
        json={
            "segment": "student",
            "eligible_customers": 2500,
            "baseline_activation_rate": 0.44,
            "current_incentive_gbp": 0.0,
            "proposed_incentive_gbp": 3.0,
            "expected_monthly_margin_per_activated_customer_gbp": 4.0,
            "vulnerable_customer_share": 0.05,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["segment"] == "student"
    assert payload["projected_lift_pp"] > 0
    assert payload["incremental_activated_customers"] > 0
    assert payload["recommendation"] in {"ship", "iterate", "hold"}

.PHONY: install lint test dbt app api docker-api pricing-scenarios monitor all

install:
	uv sync --group dev

lint:
	uv run ruff check .

test:
	uv run pytest

dbt:
	uv run dbt build --project-dir dbt_neobank --profiles-dir dbt_neobank

app:
	uv run streamlit run app/streamlit_app.py

api:
	uv run uvicorn api.main:app --reload --port 8000

docker-api:
	docker build -f Dockerfile.api -t neobank-api .

pricing-scenarios:
	uv run python -m src.pricing.scenario_runs --run-date 2025-06-30

monitor:
	uv run python -m src.monitoring.snapshot --snapshot-date 2025-06-30
	uv run python -m src.monitoring.model_report --report-date 2025-06-30
	uv run python -m src.monitoring.calibration_report --db neobank.duckdb --report-date 2025-07-07

all: lint test dbt

.PHONY: install lint test dbt app api docker-api all

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

all: lint test dbt

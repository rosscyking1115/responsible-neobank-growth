# Streamlit Community Cloud Deployment

Use Streamlit Community Cloud for the public portfolio dashboard.

## App Settings

- Repository: `rosscyking1115/neobank-product-analytics`
- Branch: `main`
- Main file path: `app/streamlit_app.py`
- Python dependencies: `requirements.txt`
- Secrets: none required

## Runtime Behavior

The app expects the dbt marts in `neobank.duckdb`. In a fresh Streamlit Cloud
container, that file will not exist, so the dashboard creates a lightweight demo
database on first load:

1. Generate 5,000 synthetic users into `raw/streamlit_demo`.
2. Run `dbt build` with `NEOBANK_DUCKDB_PATH=neobank.duckdb`.
3. Read the built marts in read-only mode for the dashboard.

Both `raw/` and DuckDB files are gitignored, so the deployed app remains
reproducible without committing generated data.

## Operational Notes

- First cold start can take a few minutes while synthetic data and dbt models are
  built.
- If the app sleeps or the container is recycled, it rebuilds the demo database
  only when `neobank.duckdb` is missing.
- If deployment fails, check Streamlit Cloud logs for dependency install errors
  or the bootstrap command output.

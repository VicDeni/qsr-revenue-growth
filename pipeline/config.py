"""Runtime configuration, read from environment variables.

Local development uses DuckDB (no cloud account needed); production uses BigQuery.
Every setting has a safe local default so `python -m pipeline run` works out of the box.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    warehouse: str            # "duckdb" (dev) or "bigquery" (prod)
    landing_uri: str          # local folder or gs://bucket/prefix
    raw_schema: str           # dataset/schema that holds append-only raw tables
    duckdb_path: Path
    gcp_project: str | None
    bq_location: str
    export_dir: Path
    sheets_spreadsheet_id: str | None  # optional: push Tableau extracts to Google Sheets

    @property
    def dbt_target(self) -> str:
        return "prod" if self.warehouse == "bigquery" else "dev"


def _env(name: str, default: str | None = None) -> str | None:
    """Treat empty strings (common with unset CI variables) as unset."""
    value = os.getenv(name)
    return value if value else default


def load_settings() -> Settings:
    warehouse = (_env("WAREHOUSE", "duckdb") or "duckdb").lower()
    if warehouse not in {"duckdb", "bigquery"}:
        raise ValueError(f"WAREHOUSE must be 'duckdb' or 'bigquery', got {warehouse!r}")
    project = _env("GCP_PROJECT")
    if warehouse == "bigquery" and not project:
        raise ValueError("GCP_PROJECT must be set when WAREHOUSE=bigquery")
    return Settings(
        warehouse=warehouse,
        landing_uri=_env("LANDING_URI", str(REPO_ROOT / "data" / "landing")),
        raw_schema=_env("RAW_SCHEMA", "qsr_raw"),
        duckdb_path=Path(_env("DUCKDB_PATH", str(REPO_ROOT / "warehouse" / "qsr.duckdb"))),
        gcp_project=project,
        bq_location=_env("BQ_LOCATION", "US"),
        export_dir=Path(_env("EXPORT_DIR", str(REPO_ROOT / "exports"))),
        sheets_spreadsheet_id=_env("SHEETS_SPREADSHEET_ID"),
    )

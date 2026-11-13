"""Transform + test: run `dbt build` (models and data tests in DAG order)."""
from __future__ import annotations

import logging
import os
import subprocess

from .config import REPO_ROOT, Settings

log = logging.getLogger(__name__)
DBT_DIR = REPO_ROOT / "dbt"


def run_dbt(settings: Settings, command: str = "build", extra: list[str] | None = None) -> None:
    env = {
        **os.environ,
        "RAW_SCHEMA": settings.raw_schema,
        "DUCKDB_PATH": str(settings.duckdb_path),
        "BQ_LOCATION": settings.bq_location,
    }
    if settings.gcp_project:
        env["GCP_PROJECT"] = settings.gcp_project
    cmd = [
        "dbt", command,
        "--project-dir", str(DBT_DIR),
        "--profiles-dir", str(DBT_DIR),
        "--target", settings.dbt_target,
        *(extra or []),
    ]
    log.info("running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)

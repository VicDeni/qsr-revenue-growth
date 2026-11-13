"""Command line entry point.

    python -m pipeline run         # ingest -> dbt build -> export (what the schedule runs)
    python -m pipeline ingest      # load new landing files only
    python -m pipeline transform   # dbt build only
    python -m pipeline export      # refresh BI extracts only
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from .config import load_settings
from .export import export_extracts
from .ingest import ingest
from .landing import open_landing
from .transform import run_dbt
from .warehouse import open_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("step", choices=["run", "ingest", "transform", "export"])
    parser.add_argument("--full-refresh", action="store_true", help="rebuild incremental dbt models")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
    log = logging.getLogger("pipeline")
    settings = load_settings()
    log.info("warehouse=%s landing=%s dbt_target=%s", settings.warehouse, settings.landing_uri, settings.dbt_target)
    started = time.time()

    if args.step in ("run", "ingest"):
        ingest(open_warehouse(settings), open_landing(settings.landing_uri), settings.raw_schema)
    if args.step in ("run", "transform"):
        run_dbt(settings, "build", ["--full-refresh"] if args.full_refresh else None)
    if args.step in ("run", "export"):
        export_extracts(open_warehouse(settings), settings.export_dir, settings.sheets_spreadsheet_id)

    log.info("step=%s finished in %.1fs", args.step, time.time() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Publish BI extracts: CSV files for Tableau, plus an optional Google Sheet.

Tableau Public cannot connect to BigQuery directly, but it re-syncs Google Sheets data
sources once a day. Pushing the reporting tables to a Sheet after each scheduled run
keeps the public dashboard current with no manual republishing.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .warehouse import Warehouse

log = logging.getLogger(__name__)

# extract name -> (schema, table)
EXTRACTS = {
    "orders": ("qsr_reporting", "rpt_orders_tableau"),
    "strategy_timeline": ("qsr_marts", "mart_strategy_timeline"),
    "keyword_trends": ("qsr_marts", "mart_keyword_trends"),
    "competitor_language": ("qsr_marts", "mart_competitor_language"),
}

# Business-friendly field names for Tableau; anything not listed becomes Title Case.
FIELD_NAMES = {
    "order_id": "Order ID", "customer_id": "Customer ID", "store_id": "Store ID",
    "order_ts": "Order Timestamp", "order_hour": "Order Hour", "day_of_week_num": "Weekday Number",
    "day_of_week_name": "Weekday", "is_app_order": "Is App Order", "items": "Items",
    "revenue": "Revenue", "fulfillment_min": "Fulfillment Minutes",
    "fulfillment_bucket_min": "Fulfillment Bucket (min)", "satisfaction_score": "Satisfaction Score",
    "us_stores_per_million": "US Stores per Million Residents", "per_10k_words": "Mentions per 10k Words",
    "ceo": "CEO", "pct_licensed": "Pct Licensed", "pct_international": "Pct International",
}


def _title(col: str) -> str:
    words = col.replace("_per_10k", " per 10k words").split("_")
    fixed = {"us": "US", "id": "ID", "ceo": "CEO", "pct": "Pct", "10k": "10k", "per": "per", "words": "Words"}
    return " ".join(fixed.get(w, w.capitalize()) for w in " ".join(words).split(" "))


def friendly(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: FIELD_NAMES.get(c, _title(c)) for c in df.columns})


def export_extracts(wh: Warehouse, export_dir: Path, sheets_spreadsheet_id: str | None = None) -> dict[str, int]:
    export_dir.mkdir(parents=True, exist_ok=True)
    frames: dict[str, pd.DataFrame] = {}
    for name, (schema, table) in EXTRACTS.items():
        df = friendly(wh.query(f"select * from {wh.fq(schema, table)}"))
        df.to_csv(export_dir / f"{name}.csv", index=False)
        frames[name] = df
        log.info("extract=%s rows=%d -> %s", name, len(df), export_dir / f"{name}.csv")
    if sheets_spreadsheet_id:
        push_to_google_sheets(sheets_spreadsheet_id, frames)
    return {k: len(v) for k, v in frames.items()}


def _sheet_values(df: pd.DataFrame) -> list[list]:
    out = df.copy()
    for col in out.columns:
        if not pd.api.types.is_numeric_dtype(out[col]) or pd.api.types.is_bool_dtype(out[col]):
            out[col] = out[col].astype(str).where(out[col].notna(), "")
    out = out.astype(object).where(out.notna(), "")
    return [list(out.columns)] + out.values.tolist()


def push_to_google_sheets(spreadsheet_id: str, frames: dict[str, pd.DataFrame], chunk_rows: int = 10_000) -> None:
    """Overwrite one worksheet per extract. The Sheet must be shared with the service account."""
    import google.auth
    import gspread

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
    sheet = gspread.authorize(creds).open_by_key(spreadsheet_id)
    for name, df in frames.items():
        values = _sheet_values(df)
        try:
            ws = sheet.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title=name, rows=len(values), cols=len(df.columns))
        ws.clear()
        ws.resize(rows=len(values), cols=len(df.columns))
        for start in range(0, len(values), chunk_rows):
            ws.update(range_name=f"A{start + 1}", values=values[start:start + chunk_rows],
                      value_input_option="USER_ENTERED")
        log.info("sheet=%s rows=%d pushed to Google Sheets", name, len(df))

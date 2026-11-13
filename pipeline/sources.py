"""Data contracts for every file the pipeline ingests.

A landing file is loaded only if it has every required column. Raw tables keep all
source columns as STRING (schema-on-read); typing happens in dbt staging models, so a
malformed value becomes NULL there and is caught by tests instead of failing the load.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str                 # raw table name
    pattern: str              # glob, relative to the landing root
    required_columns: tuple[str, ...]
    key: str | None = None    # column that must never be blank


ORDER_COLUMNS = (
    "customer_id", "order_id", "order_date", "order_time", "day_of_week", "order_channel",
    "store_id", "store_location_type", "region", "customer_age_group", "customer_gender",
    "is_rewards_member", "cart_size", "num_customizations", "total_spend",
    "fulfillment_time_min", "drink_category", "has_food_item", "order_ahead",
    "customer_satisfaction",
)

SOURCES: tuple[Source, ...] = (
    # Point-of-sale order extracts; one file per month lands in orders/.
    Source("orders", "orders/*.csv", ORDER_COLUMNS, key="order_id"),
    # Outputs of the 10-K text-mining pipeline (Starbucks annual reports, FY1996-FY2025).
    Source(
        "store_counts", "reference/store_counts_timeseries.csv",
        ("fiscal_year", "co_us", "co_international", "lic_us", "lic_international",
         "total_worldwide", "source_note", "ceo"),
        key="fiscal_year",
    ),
    Source("keyword_trends", "reference/item1_keyword_timeseries.csv",
           ("fiscal_year", "total_words"), key="fiscal_year"),
    Source("state_population", "reference/state_population_1996_2025.csv",
           ("state", "year", "population"), key="state"),
    Source("competitor_keywords", "reference/competitor_keyword_comparison.csv",
           ("document", "total_words"), key="document"),
)

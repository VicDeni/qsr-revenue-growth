"""Thin warehouse adapters: the same pipeline code runs on DuckDB (dev/CI) and BigQuery (prod)."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

AUDIT_TABLE = "_load_audit"
AUDIT_COLUMNS = ("source", "file_name", "file_md5", "row_count", "loaded_at")


class Warehouse(Protocol):
    kind: str
    def ensure_schema(self, schema: str) -> None: ...
    def table_exists(self, schema: str, table: str) -> bool: ...
    def append(self, schema: str, table: str, df: pd.DataFrame) -> None: ...
    def query(self, sql: str) -> pd.DataFrame: ...
    def fq(self, schema: str, table: str) -> str: ...


class DuckDBWarehouse:
    kind = "duckdb"

    def __init__(self, path: Path):
        import duckdb

        self._duckdb = duckdb
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        # Short-lived connections: DuckDB allows one writer, and dbt opens the file next.
        return self._duckdb.connect(str(self.path))

    def fq(self, schema: str, table: str) -> str:
        return f'"{schema}"."{table}"'

    def ensure_schema(self, schema: str) -> None:
        with self._connect() as con:
            con.execute(f'create schema if not exists "{schema}"')

    @staticmethod
    def _exists(con, schema: str, table: str) -> bool:
        n = con.execute(
            "select count(*) from information_schema.tables where table_schema = ? and table_name = ?",
            [schema, table],
        ).fetchone()[0]
        return n > 0

    def table_exists(self, schema: str, table: str) -> bool:
        with self._connect() as con:
            return self._exists(con, schema, table)

    def append(self, schema: str, table: str, df: pd.DataFrame) -> None:
        with self._connect() as con:
            con.register("incoming", df)
            if self._exists(con, schema, table):
                cols = ", ".join(f'"{c}"' for c in df.columns)
                con.execute(f"insert into {self.fq(schema, table)} ({cols}) select {cols} from incoming")
            else:
                con.execute(f"create table {self.fq(schema, table)} as select * from incoming")
            con.unregister("incoming")

    def query(self, sql: str) -> pd.DataFrame:
        with self._connect() as con:
            return con.execute(sql).df()


class BigQueryWarehouse:
    kind = "bigquery"

    def __init__(self, project: str, location: str = "US"):
        from google.cloud import bigquery

        self.bq = bigquery
        self.project = project
        self.location = location
        self.client = bigquery.Client(project=project, location=location)

    def fq(self, schema: str, table: str) -> str:
        return f"`{self.project}.{schema}.{table}`"

    def ensure_schema(self, schema: str) -> None:
        ds = self.bq.Dataset(f"{self.project}.{schema}")
        ds.location = self.location
        self.client.create_dataset(ds, exists_ok=True)

    def table_exists(self, schema: str, table: str) -> bool:
        from google.api_core.exceptions import NotFound

        try:
            self.client.get_table(f"{self.project}.{schema}.{table}")
            return True
        except NotFound:
            return False

    def append(self, schema: str, table: str, df: pd.DataFrame) -> None:
        type_map = {"_loaded_at": "TIMESTAMP", "loaded_at": "TIMESTAMP", "row_count": "INT64", "_row_number": "INT64"}
        schema_fields = [self.bq.SchemaField(c, type_map.get(c, "STRING")) for c in df.columns]
        job_config = self.bq.LoadJobConfig(
            schema=schema_fields,
            write_disposition="WRITE_APPEND",
            create_disposition="CREATE_IF_NEEDED",
            schema_update_options=["ALLOW_FIELD_ADDITION"],
        )
        job = self.client.load_table_from_dataframe(df, f"{self.project}.{schema}.{table}", job_config=job_config)
        job.result()  # raises on failure

    def query(self, sql: str) -> pd.DataFrame:
        return self.client.query(sql).to_dataframe()


def open_warehouse(settings) -> Warehouse:
    if settings.warehouse == "bigquery":
        return BigQueryWarehouse(settings.gcp_project, settings.bq_location)
    return DuckDBWarehouse(settings.duckdb_path)

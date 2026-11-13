"""Extract + Load: copy new landing files into append-only raw tables.

Idempotent by design. Every loaded file is recorded in `_load_audit` with its MD5, so a
scheduled run only loads files it has not seen. A corrected file re-delivered under the
same name has a new MD5 and is loaded again; staging keeps the latest copy of each order.
"""
from __future__ import annotations

import hashlib
import io
import logging
import re
from datetime import UTC, datetime

import pandas as pd

from .landing import Landing, LandingFile
from .sources import SOURCES, Source
from .warehouse import AUDIT_TABLE, Warehouse

log = logging.getLogger(__name__)


class ContractError(ValueError):
    """A landing file does not match its data contract; it is not loaded."""


def _clean_column(name: str) -> str:
    return re.sub(r"[^0-9a-z_]+", "_", name.strip().lower()).strip("_")


def parse_file(source: Source, file: LandingFile) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file.content), dtype=str, keep_default_na=False)
    df.columns = [_clean_column(c) for c in df.columns]
    missing = [c for c in source.required_columns if c not in df.columns]
    if missing:
        raise ContractError(f"{file.name}: missing required columns {missing}")
    if df.empty:
        raise ContractError(f"{file.name}: file has no rows")
    if source.key and (df[source.key].str.strip() == "").any():
        raise ContractError(f"{file.name}: blank values in key column {source.key!r}")
    df = df.replace({"": None})
    df["_source_file"] = file.name
    df["_row_number"] = range(1, len(df) + 1)
    return df


def _already_loaded(wh: Warehouse, raw_schema: str) -> set[tuple[str, str, str]]:
    if not wh.table_exists(raw_schema, AUDIT_TABLE):
        return set()
    seen = wh.query(f"select source, file_name, file_md5 from {wh.fq(raw_schema, AUDIT_TABLE)}")
    return set(seen.itertuples(index=False, name=None))


def ingest(wh: Warehouse, landing: Landing, raw_schema: str) -> dict[str, int]:
    """Load every new landing file. Returns rows loaded per source."""
    wh.ensure_schema(raw_schema)
    seen = _already_loaded(wh, raw_schema)
    loaded: dict[str, int] = {}

    for source in SOURCES:
        names = landing.list(source.pattern)
        if not names:
            log.warning("source=%s no files match %s", source.name, source.pattern)
        for name in names:
            file = landing.read(name)
            md5 = hashlib.md5(file.content).hexdigest()
            if (source.name, file.name, md5) in seen:
                log.info("source=%s file=%s skipped (already loaded)", source.name, file.name)
                continue
            df = parse_file(source, file)
            loaded_at = datetime.now(UTC)
            df["_loaded_at"] = pd.Timestamp(loaded_at)
            wh.append(raw_schema, source.name, df)
            audit = pd.DataFrame([{
                "source": source.name, "file_name": file.name, "file_md5": md5,
                "row_count": len(df), "loaded_at": pd.Timestamp(loaded_at),
            }])
            wh.append(raw_schema, AUDIT_TABLE, audit)
            loaded[source.name] = loaded.get(source.name, 0) + len(df)
            log.info("source=%s file=%s rows=%d loaded", source.name, file.name, len(df))

    log.info("ingest complete: %s", loaded or "no new files")
    return loaded

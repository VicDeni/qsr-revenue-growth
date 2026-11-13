import pandas as pd
import pytest

from pipeline.ingest import ContractError, ingest, parse_file
from pipeline.landing import LandingFile, LocalLanding
from pipeline.sources import SOURCES
from pipeline.warehouse import DuckDBWarehouse

ORDERS = next(s for s in SOURCES if s.name == "orders")


def test_first_run_loads_every_file(tmp_path, landing):
    wh = DuckDBWarehouse(tmp_path / "wh.duckdb")
    loaded = ingest(wh, LocalLanding(landing), "qsr_raw")
    assert loaded["orders"] == 10
    assert loaded["store_counts"] == 30
    audit = wh.query('select * from "qsr_raw"."_load_audit"')
    assert len(audit) == 6  # 2 order files + 4 reference files


def test_second_run_is_a_no_op(tmp_path, landing):
    wh = DuckDBWarehouse(tmp_path / "wh.duckdb")
    ingest(wh, LocalLanding(landing), "qsr_raw")
    assert ingest(wh, LocalLanding(landing), "qsr_raw") == {}
    assert wh.query('select count(*) as n from "qsr_raw"."orders"').n[0] == 10


def test_corrected_file_is_reloaded(tmp_path, landing):
    wh = DuckDBWarehouse(tmp_path / "wh.duckdb")
    ingest(wh, LocalLanding(landing), "qsr_raw")
    f = landing / "orders" / "orders_2024-01.csv"
    df = pd.read_csv(f, dtype=str)
    df.loc[0, "total_spend"] = "1.00"
    df.to_csv(f, index=False)
    assert ingest(wh, LocalLanding(landing), "qsr_raw") == {"orders": 5}


def test_new_month_is_picked_up(tmp_path, landing):
    wh = DuckDBWarehouse(tmp_path / "wh.duckdb")
    ingest(wh, LocalLanding(landing), "qsr_raw")
    src = (landing / "orders" / "orders_2024-02.csv").read_text().replace("ORD_", "NEW_")
    (landing / "orders" / "orders_2024-03.csv").write_text(src)
    assert ingest(wh, LocalLanding(landing), "qsr_raw") == {"orders": 5}


def test_missing_column_breaks_the_contract():
    bad = LandingFile("orders/bad.csv", b"order_id,total_spend\nORD_1,9.99\n")
    with pytest.raises(ContractError, match="missing required columns"):
        parse_file(ORDERS, bad)


def test_blank_key_breaks_the_contract(landing):
    text = (landing / "orders" / "orders_2024-01.csv").read_text().splitlines()
    header, first = text[0], text[1].split(",")
    first[1] = ""  # order_id is the 2nd column
    bad = LandingFile("orders/bad.csv", (header + "\n" + ",".join(first) + "\n").encode())
    with pytest.raises(ContractError, match="blank values"):
        parse_file(ORDERS, bad)

import numpy as np
import pandas as pd

from pipeline.export import _sheet_values, friendly


def test_friendly_field_names():
    df = pd.DataFrame(columns=["order_id", "order_channel", "satisfaction_score"])
    assert list(friendly(df).columns) == ["Order ID", "Order Channel", "Satisfaction Score"]
    other = pd.DataFrame(columns=["us_stores", "company_operated_us", "mobile_per_10k", "store_growth_pct"])
    expected = ["US Stores", "Company Operated US", "Mobile per 10k Words", "Store Growth Pct"]
    assert list(friendly(other).columns) == expected


def test_sheet_values_are_json_safe():
    df = pd.DataFrame({
        "d": pd.to_datetime(["2025-01-01", None]),
        "flag": [True, False],
        "x": [1.5, np.nan],
        "s": ["a", None],
    })
    rows = _sheet_values(df)
    assert rows[0] == ["d", "flag", "x", "s"]
    assert rows[1] == ["2025-01-01", "True", 1.5, "a"]
    assert rows[2][2] == "" and rows[2][3] == ""

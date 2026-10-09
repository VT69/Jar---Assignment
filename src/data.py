"""Loading, repairing and merging the three raw datasets.

Raw files in ``data/`` are never modified; every repair happens in memory and
is guarded by assertions so that a change in the inputs fails loudly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from src import config


# --------------------------------------------------------------------------- #
# Loading & repair
# --------------------------------------------------------------------------- #
def _repair_order_date(value: object) -> pd.Timestamp:
    """Return the true order date for one raw ``Order Date`` cell.

    The column mixes two encodings:
    * text cells in ``dd-mm-yyyy`` (parsed as-is), and
    * cells Excel auto-converted to dates by reading ``dd-mm-yyyy`` as
      ``mm-dd-yyyy`` (only possible when day <= 12) - day and month are swapped
      back.
    """
    if isinstance(value, str):
        return pd.to_datetime(value.strip(), format=config.ORDER_DATE_TEXT_FORMAT)
    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(year=value.year, month=value.day, day=value.month)
    raise TypeError(f"Unexpected Order Date cell type: {type(value).__name__}")


def load_orders(path: Path = config.ORDERS_FILE) -> pd.DataFrame:
    """Load *List of Orders* (one row per order) and repair ``Order Date``.

    Returns:
        DataFrame with columns Order ID, Order Date (datetime64), CustomerName,
        State, City, and the raw date kept as ``Order Date Raw`` for audit.
    """
    raw = pd.read_excel(path, dtype={"Order ID": str})
    df = raw.copy()
    df["Order Date Raw"] = df["Order Date"].astype(str)
    df["Order Date"] = df["Order Date"].map(_repair_order_date).astype("datetime64[ns]")
    for col in ("Order ID", "CustomerName", "State", "City"):
        df[col] = df[col].str.strip()

    # Sanity: IDs unique; repaired dates must be non-decreasing in Order ID order
    # (the IDs are sequential) and fall inside FY 2018-19.
    assert df["Order ID"].is_unique, "Order ID must be unique in List of Orders"
    by_id = df.assign(_n=df["Order ID"].str[2:].astype(int)).sort_values("_n")
    assert by_id["Order Date"].is_monotonic_increasing, "Repaired dates not monotonic in Order ID"
    lo, hi = (pd.Timestamp(d) for d in config.EXPECTED_ORDER_PERIOD)
    assert df["Order Date"].between(lo, hi).all(), "Order Date outside expected FY 2018-19"
    assert df.notna().all().all(), "Unexpected nulls in List of Orders"
    return df


def load_details(path: Path = config.DETAILS_FILE) -> pd.DataFrame:
    """Load *Order Details* (one row per order line) with basic integrity checks."""
    df = pd.read_excel(path, dtype={"Order ID": str})
    for col in ("Order ID", "Category", "Sub-Category"):
        df[col] = df[col].str.strip()
    assert df.notna().all().all(), "Unexpected nulls in Order Details"
    assert (df["Amount"] > 0).all(), "Amount must be strictly positive"
    assert (df["Quantity"] > 0).all(), "Quantity must be strictly positive"
    assert (df["Profit"] <= df["Amount"]).all(), "Profit cannot exceed revenue"
    return df


def load_targets(path: Path = config.TARGETS_FILE) -> pd.DataFrame:
    """Load *Sales target* and rebuild the corrupted month column.

    The month labels (``Apr-18`` ... ``Mar-19``) were auto-converted by Excel to
    *day 18/19 of the current year*. The true month is ``month`` and the true
    year is ``2000 + day``.

    Returns:
        DataFrame with Month (month-start datetime), Category, Target.
    """
    raw = pd.read_excel(path)
    col = "Month of Order Date"
    stamps = pd.to_datetime(raw[col])
    month = pd.to_datetime(
        {"year": stamps.dt.day + config.TARGET_YEAR_CENTURY, "month": stamps.dt.month, "day": 1}
    )
    df = pd.DataFrame(
        {"Month": month, "Category": raw["Category"].str.strip(), "Target": raw["Target"].astype(float)}
    )
    per_cat = df.groupby("Category")["Month"].agg(["nunique", "min", "max"])
    assert (per_cat["nunique"] == 12).all(), "Each category should have 12 distinct months"
    assert (per_cat["min"] == pd.Timestamp(config.EXPECTED_ORDER_PERIOD[0])).all()
    assert (per_cat["max"] == pd.Timestamp("2019-03-01")).all()
    assert (df["Target"] > 0).all()
    return df.sort_values(["Category", "Month"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Merge
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class JoinReport:
    """Audit trail for the Orders x Details join."""

    orders_rows: int
    details_rows: int
    merged_rows: int
    orders_unique_ids: int
    details_unique_ids: int
    duplicate_ids_in_orders: int
    ids_only_in_orders: int
    ids_only_in_details: int
    join_type: str

    def as_frame(self) -> pd.DataFrame:
        """Return the report as a two-column table for export."""
        return pd.DataFrame({"check": list(self.__dict__), "value": list(self.__dict__.values())})


def merge_orders(orders: pd.DataFrame, details: pd.DataFrame) -> tuple[pd.DataFrame, JoinReport]:
    """Left-join line items to their order header (many-to-one) and validate.

    Order Details is the left table because it carries the analysis grain
    (one row per line item). ``validate='many_to_one'`` guarantees Order ID is
    unique on the header side, and the indicator column proves no line is
    orphaned. Any unmatched ID on either side raises instead of being dropped.
    """
    only_orders = set(orders["Order ID"]) - set(details["Order ID"])
    only_details = set(details["Order ID"]) - set(orders["Order ID"])
    merged = details.merge(
        orders.drop(columns=["Order Date Raw"]),
        on="Order ID",
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    report = JoinReport(
        orders_rows=len(orders),
        details_rows=len(details),
        merged_rows=len(merged),
        orders_unique_ids=orders["Order ID"].nunique(),
        details_unique_ids=details["Order ID"].nunique(),
        duplicate_ids_in_orders=int(orders["Order ID"].duplicated().sum()),
        ids_only_in_orders=len(only_orders),
        ids_only_in_details=len(only_details),
        join_type="left (Order Details -> List of Orders), validate=many_to_one",
    )
    assert report.merged_rows == report.details_rows, "Join changed the line-item row count"
    assert (merged["_merge"] == "both").all(), "Orphan line items found"
    assert not only_orders and not only_details, "Unmatched Order IDs between the two files"
    merged = merged.drop(columns="_merge")
    assert merged.notna().all().all(), "NaNs introduced by the merge"
    merged["Month"] = merged["Order Date"].dt.to_period("M").dt.to_timestamp()
    return merged, report

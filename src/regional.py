"""Question 1, Part 3 - state and city performance.

Order count is always the number of *distinct* Order IDs (taken from List of
Orders), never the number of line items. Average profit is per order (primary)
with per-line shown as a secondary column, consistent with Part 1.
"""
from __future__ import annotations

import pandas as pd

from src import config


def _geo_block(orders: pd.DataFrame, merged: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    order_counts = orders.groupby(keys)["Order ID"].nunique().rename("orders")
    money = merged.groupby(keys).agg(
        sales=("Amount", "sum"),
        profit=("Profit", "sum"),
        lines=("Order ID", "size"),
        loss_lines=("Profit", lambda s: int((s < 0).sum())),
    )
    out = money.join(order_counts, how="outer", validate="one_to_one")
    assert out.notna().all().all(), "Geography present in one table but not the other"
    out["profit_per_order"] = out["profit"] / out["orders"]
    out["profit_per_line"] = out["profit"] / out["lines"]
    out["sales_per_order"] = out["sales"] / out["orders"]
    out["margin_pct"] = 100 * out["profit"] / out["sales"]
    out["loss_line_share_pct"] = 100 * out["loss_lines"] / out["lines"]
    lo, hi = config.MARGIN_PLAUSIBLE_RANGE
    assert out["margin_pct"].between(lo, hi).all()
    return out


def state_summary(orders: pd.DataFrame, merged: pd.DataFrame) -> pd.DataFrame:
    """All states: distinct orders, sales, profit, per-order metrics and shares.

    ``share_gap_pp`` = profit share - sales share (percentage points). Negative
    means the state captures less of company profit than of company sales.
    """
    out = _geo_block(orders, merged, ["State"])
    out["sales_share_pct"] = 100 * out["sales"] / out["sales"].sum()
    out["profit_share_pct"] = 100 * out["profit"] / out["profit"].sum()
    out["share_gap_pp"] = out["profit_share_pct"] - out["sales_share_pct"]
    assert out["orders"].sum() == orders["Order ID"].nunique()
    assert out["sales"].sum() == merged["Amount"].sum()
    # Rank by distinct order count; ties broken by sales so the order is deterministic.
    out = out.sort_values(["orders", "sales"], ascending=[False, False])
    out["order_rank"] = range(1, len(out) + 1)
    return out


def top_states(states: pd.DataFrame, n: int = config.TOP_N_STATES) -> pd.DataFrame:
    """Top ``n`` states by distinct order count; warns via column if the cut-off is tied."""
    top = states.head(n).copy()
    cutoff = top["orders"].iloc[-1]
    top["tied_at_cutoff"] = (states["orders"] == cutoff).sum() > (top["orders"] == cutoff).sum()
    return top


def city_summary(orders: pd.DataFrame, merged: pd.DataFrame) -> pd.DataFrame:
    """State x City metrics with each city's share of its state's sales and profit."""
    out = _geo_block(orders, merged, ["State", "City"]).reset_index()
    st_sales = out.groupby("State")["sales"].transform("sum")
    st_profit = out.groupby("State")["profit"].transform("sum")
    st_orders = out.groupby("State")["orders"].transform("sum")
    out["share_of_state_sales_pct"] = 100 * out["sales"] / st_sales
    out["share_of_state_profit_pct"] = 100 * out["profit"] / st_profit
    out["share_of_state_orders_pct"] = 100 * out["orders"] / st_orders
    out["sales_share_pct"] = 100 * out["sales"] / out["sales"].sum()
    out["profit_share_pct"] = 100 * out["profit"] / out["profit"].sum()
    return out.sort_values(["State", "sales"], ascending=[True, False]).reset_index(drop=True)


def state_category_profit(merged: pd.DataFrame, states: list[str]) -> pd.DataFrame:
    """Profit and margin by Category for the given states (drivers of state results)."""
    sub = merged[merged["State"].isin(states)]
    out = sub.groupby(["State", "Category"]).agg(sales=("Amount", "sum"), profit=("Profit", "sum")).reset_index()
    out["margin_pct"] = 100 * out["profit"] / out["sales"]
    return out

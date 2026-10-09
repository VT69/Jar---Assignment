"""Question 1, Part 1 - sales and profitability by category and sub-category.

Definitions used throughout:
* **Profit per order** (primary): sum of a group's line profits / number of
  distinct Order IDs that contain at least one line of that group.
* **Profit per line** (secondary): mean of Profit across the group's lines.
* **Margin**: sum(Profit) / sum(Amount) x 100.
"""
from __future__ import annotations

import pandas as pd

from src import config


def _assert_margins(df: pd.DataFrame, col: str = "margin_pct") -> None:
    lo, hi = config.MARGIN_PLAUSIBLE_RANGE
    assert df[col].between(lo, hi).all(), f"{col} outside plausible range {lo}..{hi}"


def _profit_block(merged: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Shared aggregation for any grouping of line items."""
    g = merged.groupby(keys, observed=True)
    out = g.agg(
        amount=("Amount", "sum"),
        profit=("Profit", "sum"),
        quantity=("Quantity", "sum"),
        lines=("Order ID", "size"),
        orders=("Order ID", "nunique"),
        loss_lines=("Profit", lambda s: int((s < 0).sum())),
    )
    out["profit_per_order"] = out["profit"] / out["orders"]
    out["profit_per_line"] = out["profit"] / out["lines"]
    out["margin_pct"] = 100 * out["profit"] / out["amount"]
    out["amount_per_order"] = out["amount"] / out["orders"]
    out["avg_qty_per_line"] = out["quantity"] / out["lines"]
    out["unit_price"] = out["amount"] / out["quantity"]
    out["profit_per_unit"] = out["profit"] / out["quantity"]
    out["loss_line_share_pct"] = 100 * out["loss_lines"] / out["lines"]
    assert out.notna().all().all(), "NaN in profit block"
    _assert_margins(out)
    return out


def category_summary(merged: pd.DataFrame) -> pd.DataFrame:
    """Total sales, profit, per-order / per-line profit and margin per Category.

    Also adds each category's share of total sales and profit and its rank on the
    three headline metrics (1 = best).
    """
    out = _profit_block(merged, ["Category"])
    out["sales_share_pct"] = 100 * out["amount"] / out["amount"].sum()
    out["profit_share_pct"] = 100 * out["profit"] / out["profit"].sum()
    for metric in ("amount", "profit", "profit_per_order", "margin_pct"):
        out[f"rank_{metric}"] = out[metric].rank(ascending=False, method="min").astype(int)
    assert out["amount"].sum() == merged["Amount"].sum(), "Category sales do not reconcile"
    assert out["profit"].sum() == merged["Profit"].sum(), "Category profit does not reconcile"
    return out.sort_values("amount", ascending=False)


def subcategory_summary(merged: pd.DataFrame) -> pd.DataFrame:
    """Same metrics at Category x Sub-Category grain plus within-category shares."""
    out = _profit_block(merged, ["Category", "Sub-Category"]).reset_index()
    cat_amount = out.groupby("Category")["amount"].transform("sum")
    cat_profit = out.groupby("Category")["profit"].transform("sum")
    out["share_of_cat_sales_pct"] = 100 * out["amount"] / cat_amount
    out["share_of_cat_profit_pct"] = 100 * out["profit"] / cat_profit
    assert out["amount"].sum() == merged["Amount"].sum()
    return out.sort_values(["Category", "profit"], ascending=[True, False]).reset_index(drop=True)


def loss_profile(merged: pd.DataFrame, top_n: int = config.TOP_N_LOSS_LINES) -> pd.DataFrame:
    """How concentrated are each category's losses?

    Columns:
        gross_gain: sum of profit on profitable lines.
        gross_loss: absolute sum of profit on loss-making lines.
        loss_to_gain_pct: gross_loss / gross_gain - share of gains wiped out by losses.
        top_n_loss_share_pct: share of gross_loss coming from the ``top_n`` worst lines.
        loss_exceeds_revenue_lines: lines whose loss is larger than their revenue.
    """
    rows = []
    for cat, grp in merged.groupby("Category"):
        losses = grp.loc[grp["Profit"] < 0, "Profit"].abs().sort_values(ascending=False)
        gains = grp.loc[grp["Profit"] > 0, "Profit"]
        rows.append(
            {
                "Category": cat,
                "lines": len(grp),
                "loss_lines": len(losses),
                "loss_line_share_pct": 100 * len(losses) / len(grp),
                "zero_profit_lines": int((grp["Profit"] == 0).sum()),
                "gross_gain": float(gains.sum()),
                "gross_loss": float(losses.sum()),
                "net_profit": float(grp["Profit"].sum()),
                "loss_to_gain_pct": 100 * losses.sum() / gains.sum(),
                "top_n_loss_share_pct": 100 * losses.head(top_n).sum() / losses.sum(),
                "loss_exceeds_revenue_lines": int((grp["Profit"] < -grp["Amount"]).sum()),
                "loss_line_margin_pct": 100
                * grp.loc[grp["Profit"] < 0, "Profit"].sum()
                / grp.loc[grp["Profit"] < 0, "Amount"].sum(),
                "profit_line_margin_pct": 100
                * grp.loc[grp["Profit"] > 0, "Profit"].sum()
                / grp.loc[grp["Profit"] > 0, "Amount"].sum(),
            }
        )
    out = pd.DataFrame(rows).set_index("Category")
    assert (out["gross_gain"] - out["gross_loss"] == out["net_profit"]).all()
    return out


def price_realisation(merged: pd.DataFrame) -> pd.DataFrame:
    """Price-realisation check: unit price on loss lines vs profitable lines, per sub-category.

    The dataset has no discount column. If loss-making lines are driven by low
    realised prices, their unit price (Amount / Quantity) should sit below that
    of profitable lines of the *same* sub-category. A lower price is consistent
    with discounting (hypothesis) or with a cheaper product mix; this check
    cannot separate the two.

    Returns:
        One row per sub-category with median unit price on loss and profit lines,
        their ratio, and the median quantity on each.
    """
    df = merged.assign(unit_price=merged["Amount"] / merged["Quantity"])
    df["is_loss"] = df["Profit"] < 0
    agg = (
        df[df["Profit"] != 0]
        .groupby(["Category", "Sub-Category", "is_loss"])
        .agg(median_unit_price=("unit_price", "median"), median_qty=("Quantity", "median"), n=("unit_price", "size"))
        .unstack("is_loss")
    )
    out = pd.DataFrame(
        {
            "loss_lines": agg[("n", True)],
            "profit_lines": agg[("n", False)],
            "median_unit_price_loss": agg[("median_unit_price", True)],
            "median_unit_price_profit": agg[("median_unit_price", False)],
            "median_qty_loss": agg[("median_qty", True)],
            "median_qty_profit": agg[("median_qty", False)],
        }
    ).dropna()
    out["price_ratio_loss_vs_profit"] = out["median_unit_price_loss"] / out["median_unit_price_profit"]
    return out.reset_index()


def category_monthly(merged: pd.DataFrame) -> pd.DataFrame:
    """Monthly sales and profit by category (long format)."""
    out = (
        merged.groupby(["Month", "Category"])
        .agg(amount=("Amount", "sum"), profit=("Profit", "sum"), orders=("Order ID", "nunique"))
        .reset_index()
    )
    out["margin_pct"] = 100 * out["profit"] / out["amount"]
    assert out["amount"].sum() == merged["Amount"].sum()
    return out

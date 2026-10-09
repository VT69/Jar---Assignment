"""Question 1, Part 2 - target trend and target-vs-actual analysis."""
from __future__ import annotations

import pandas as pd

from src import config


def target_mom(
    targets: pd.DataFrame,
    category: str = config.TARGET_CATEGORY,
    z_threshold: float = config.FLUCTUATION_Z,
    material_pct: float = config.MATERIAL_MOM_PCT,
) -> pd.DataFrame:
    """Month-over-month % change in a category's target, with fluctuation flags.

    Flag rule (two lenses, both reported):
        * ``flag_relative``: the month's MoM % lies more than ``z_threshold``
          standard deviations from the mean MoM % of the series (z-score rule).
        * ``flag_material``: |MoM %| >= ``material_pct`` (business materiality).

    Returns:
        Month, Target, mom_abs, mom_pct, mom_z, flag_relative, flag_material.
    """
    df = targets[targets["Category"] == category].sort_values("Month").reset_index(drop=True)
    assert len(df) == 12 and df["Month"].is_monotonic_increasing
    df = df[["Month", "Target"]].copy()
    df["mom_abs"] = df["Target"].diff()
    df["mom_pct"] = 100 * df["Target"].pct_change()
    mean, sd = df["mom_pct"].mean(), df["mom_pct"].std(ddof=1)
    df["mom_z"] = (df["mom_pct"] - mean) / sd
    df["flag_relative"] = df["mom_z"].abs() > z_threshold
    df["flag_material"] = df["mom_pct"].abs() >= material_pct
    assert df["mom_pct"].iloc[1:].notna().all(), "MoM % should exist for months 2..12"
    return df


def target_vs_actual(
    targets: pd.DataFrame,
    monthly: pd.DataFrame,
    category: str = config.TARGET_CATEGORY,
    z_threshold: float = config.FLUCTUATION_Z,
) -> pd.DataFrame:
    """Join a category's monthly target to its actual monthly sales.

    Returns:
        Month, Target, Actual, Profit, gap (Actual - Target), attainment_pct,
        actual_mom_pct and a z-score flag on actual MoM % using the same rule as
        the target series.
    """
    t = targets[targets["Category"] == category][["Month", "Target"]]
    a = monthly[monthly["Category"] == category][["Month", "amount", "profit", "orders"]]
    df = t.merge(a, on="Month", how="left", validate="one_to_one").rename(
        columns={"amount": "Actual", "profit": "Profit", "orders": "Orders"}
    )
    assert df["Actual"].notna().all(), "A target month has no actual sales"
    df = df.sort_values("Month").reset_index(drop=True)
    df["gap"] = df["Actual"] - df["Target"]
    df["attainment_pct"] = 100 * df["Actual"] / df["Target"]
    df["actual_mom_pct"] = 100 * df["Actual"].pct_change()
    z = (df["actual_mom_pct"] - df["actual_mom_pct"].mean()) / df["actual_mom_pct"].std(ddof=1)
    df["actual_flag_relative"] = z.abs() > z_threshold
    df["margin_pct"] = 100 * df["Profit"] / df["Actual"]
    return df


def attainment_by_category(targets: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    """Annual and monthly attainment statistics for every category (context table)."""
    rows = []
    for cat in sorted(targets["Category"].unique()):
        tva = target_vs_actual(targets, monthly, cat)
        rows.append(
            {
                "Category": cat,
                "annual_target": tva["Target"].sum(),
                "annual_actual": tva["Actual"].sum(),
                "annual_attainment_pct": 100 * tva["Actual"].sum() / tva["Target"].sum(),
                "months_met": int((tva["Actual"] >= tva["Target"]).sum()),
                "min_attainment_pct": tva["attainment_pct"].min(),
                "max_attainment_pct": tva["attainment_pct"].max(),
                "target_cv_pct": 100 * tva["Target"].std(ddof=1) / tva["Target"].mean(),
                "actual_cv_pct": 100 * tva["Actual"].std(ddof=1) / tva["Actual"].mean(),
            }
        )
    return pd.DataFrame(rows).set_index("Category")


def rephased_targets(tva: pd.DataFrame, business_monthly: pd.Series) -> pd.DataFrame:
    """Re-phase the existing annual target using whole-business seasonality.

    The annual target is kept unchanged; it is redistributed across months in
    proportion to each month's share of ``business_monthly`` sales. Using
    company-wide rather than Furniture's own sales limits (but, because company
    sales include Furniture, does not eliminate) fitting the target to the
    series it is judged against; pass non-Furniture sales for a leakage-free
    sensitivity.

    Args:
        tva: Output of :func:`target_vs_actual` for the category.
        business_monthly: Total company sales indexed by Month.

    Returns:
        ``tva`` plus ``season_share_pct``, ``Rephased`` and ``rephased_attainment_pct``.
    """
    share = business_monthly / business_monthly.sum()
    df = tva.copy()
    df["season_share_pct"] = 100 * df["Month"].map(share)
    assert abs(df["season_share_pct"].sum() - 100) < 1e-9
    df["Rephased"] = df["Target"].sum() * df["season_share_pct"] / 100
    df["rephased_gap"] = df["Actual"] - df["Rephased"]
    df["rephased_attainment_pct"] = 100 * df["Actual"] / df["Rephased"]
    assert abs(df["Rephased"].sum() - df["Target"].sum()) < 1e-6, "Re-phasing must preserve the annual target"
    return df


def mape(actual: pd.Series, plan: pd.Series) -> float:
    """Mean absolute percentage error of a plan against actuals (in %)."""
    return float(100 * ((actual - plan).abs() / actual).mean())

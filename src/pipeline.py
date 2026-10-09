"""Orchestrates loading, computation, table export and figure generation."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src import config as C
from src import data, insights, opportunities, plotting, regional, sales, targets
from src.formatting import inr


def compute() -> dict[str, Any]:
    """Run every computation and return the resulting tables in one dict."""
    orders = data.load_orders()
    details = data.load_details()
    tgt = data.load_targets()
    merged, join = data.merge_orders(orders, details)

    monthly = sales.category_monthly(merged)
    tva = targets.target_vs_actual(tgt, monthly)
    business_monthly = merged.groupby("Month")["Amount"].sum()
    other_monthly = merged[merged["Category"] != C.TARGET_CATEGORY].groupby("Month")["Amount"].sum()
    states = regional.state_summary(orders, merged)
    top = regional.top_states(states)
    loss_states = states[states["profit"] < 0].index.tolist()
    return {
        "orders": orders,
        "details": details,
        "targets": tgt,
        "merged": merged,
        "join": join,
        "cat": sales.category_summary(merged),
        "sub": sales.subcategory_summary(merged),
        "loss": sales.loss_profile(merged),
        "price": sales.price_realisation(merged),
        "monthly": monthly,
        "mom": targets.target_mom(tgt),
        "tva": tva,
        "rephased": targets.rephased_targets(tva, business_monthly),
        "rephased_exfurn": targets.rephased_targets(tva, other_monthly),
        "attain": targets.attainment_by_category(tgt, monthly),
        "states": states,
        "top": top,
        "cities": regional.city_summary(orders, merged),
        "state_cat": regional.state_category_profit(merged, sorted(set(top.index) | set(loss_states))),
        "opps": opportunities.opportunity_table(),
    }


def export_tables(t: dict[str, Any]) -> list[str]:
    """Write intermediate tables to ``outputs/tables`` as CSV (deterministic order)."""
    C.TABLE_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "00_join_validation.csv": t["join"].as_frame(),
        "01_merged_line_items.csv": t["merged"],
        "02_category_summary.csv": t["cat"].reset_index(),
        "03_subcategory_summary.csv": t["sub"],
        "04_loss_profile.csv": t["loss"].reset_index(),
        "05_price_realisation.csv": t["price"],
        "06_category_monthly.csv": t["monthly"],
        "07_furniture_target_mom.csv": t["mom"],
        "08_furniture_target_vs_actual.csv": t["rephased"],
        "09_attainment_by_category.csv": t["attain"].reset_index(),
        "10_state_summary.csv": t["states"].reset_index(),
        "11_top5_states.csv": t["top"].reset_index(),
        "12_city_summary.csv": t["cities"],
        "13_state_category_profit.csv": t["state_cat"],
        "14_q3_opportunity_scores.csv": t["opps"],
    }
    for name, df in files.items():
        df.to_csv(C.TABLE_DIR / name, index=False, float_format="%.4f", date_format="%Y-%m-%d")
    return list(files)


def make_figures(t: dict[str, Any], n: dict[str, Any]) -> dict[str, str]:
    """Render all figures; titles are built from the computed numbers."""
    plotting.apply_style()
    F = C.FIGURE_DIR
    tab, games = n["sub.Furniture.Tables.profit"], n["sub.Electronics.Electronic Games.profit"]
    top_cities = ["Mumbai (MH)", "Indore (MP)", "Pune (MH)", "Chennai (TN)", "Chandigarh (PB)", "Ahmedabad (GJ)",
                  "Jaipur (RJ)", "Allahabad (UP)", "Bhopal (MP)"]
    figs = {
        "fig1": plotting.category_overview(
            t["cat"], F / "fig1_category_overview.png",
            "Electronics leads on sales and profit per order; Furniture trails on every metric"),
        "fig2": plotting.subcategory_profit(
            t["sub"], F / "fig2_subcategory_profit.png",
            f"Two sub-categories lose money: Tables ({inr(tab)}) and Electronic Games ({inr(games)})"),
        "fig3": plotting.loss_concentration(
            t["loss"], F / "fig3_loss_concentration.png",
            f"Furniture's loss-making lines erase {n['loss.Furniture.loss_to_gain_pct']:.0f}% of what its profitable lines earn"),
        "fig4": plotting.price_realisation(
            t["price"], F / "fig4_price_realisation.png",
            f"In {n['p1.price_n_lower']} of {n['p1.price_n_subcats']} sub-categories, loss lines sell at a lower unit price "
            f"(median {n['p1.price_median_ratio']:.2f}×)"),
        "fig5": plotting.target_mom(
            t["mom"], C.FLUCTUATION_Z, F / "fig5_furniture_target_mom.png",
            f"The Furniture target ramps smoothly: every MoM change is between {n['p2.mom_min']:.2f}% and {n['p2.mom_max']:.2f}%"),
        "fig6": plotting.target_vs_actual(
            t["rephased"], F / "fig6_furniture_target_vs_actual.png",
            f"Flat targets miss a back-loaded year: {n['p2.lead_miss_months']} straight misses, then "
            f"{n['p2.tail_met']} of the last {n['p2.tail_months']} months above target"),
        "fig7": plotting.top_states(
            t["top"], F / "fig7_top5_states.png",
            f"Two states hold {n['p3.top2_order_share']:.1f}% of orders; {t['top'].index[-1]} makes the top 5 yet loses money"),
        "fig8": plotting.state_share_gap(
            t["states"], F / "fig8_state_share_gap.png",
            f"{n['p3.n_loss_states']} states lose money; {n['p3.n_overearners']} smaller states earn well above their sales share"),
        "fig9": plotting.city_map(
            t["cities"], top_cities, F / "fig9_city_margin.png",
            "Mumbai and Indore carry the volume at thin margins; Chennai is the deepest loss"),
        "fig10": opportunities.matrix_figure(t["opps"], F / "fig10_q3_priority_matrix.png"),
    }
    return {k: v.relative_to(C.PROJECT_ROOT).as_posix() for k, v in figs.items()}


def run() -> dict[str, Any]:
    """Full analysis: compute, export tables, build numbers, render figures."""
    t = compute()
    tables = export_tables(t)
    n = insights.build_numbers(t)
    figs = make_figures(t, n)
    C.NUMBERS_JSON.write_text(json.dumps(n, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    pd.Series(figs).to_csv(C.TABLE_DIR / "figure_index.csv", header=["path"])
    return {"tables": t, "numbers": n, "figures": figs, "table_files": tables}

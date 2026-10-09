"""Derive every number quoted in the report from the computed tables.

The output is a flat ``{dotted.key: value}`` dict serialised to
``outputs/report_numbers.json``. The report template references these keys
only, so a number in the text can never drift from the computed output.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src import config
from src.opportunities import sizing
from src.targets import mape


def _flatten(prefix: str, frame: pd.DataFrame) -> dict[str, Any]:
    """Flatten a DataFrame indexed by entity into ``prefix.entity.column`` keys."""
    out: dict[str, Any] = {}
    for idx, row in frame.iterrows():
        name = ".".join(map(str, idx)) if isinstance(idx, tuple) else str(idx)
        for col, val in row.items():
            if isinstance(val, (int, float, bool)) or hasattr(val, "item"):
                val = val.item() if hasattr(val, "item") else val
            out[f"{prefix}.{name}.{col}"] = val
    return out


def _month(ts: pd.Timestamp) -> str:
    return ts.strftime("%b %Y")


def _join_names(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def build_numbers(t: dict[str, Any]) -> dict[str, Any]:
    """Compute the full set of report numbers.

    Args:
        t: Dict of computed tables produced by :func:`src.pipeline.compute`.

    Returns:
        Flat dict of scalar values (numbers or short strings).
    """
    n: dict[str, Any] = {}
    orders, merged, cat, sub, loss, pr = t["orders"], t["merged"], t["cat"], t["sub"], t["loss"], t["price"]

    # ---- data audit -------------------------------------------------------
    n.update({f"join.{k}": v for k, v in t["join"].__dict__.items()})
    raw = orders["Order Date Raw"]
    n["data.text_dates"] = int(raw.str.match(r"^\d{2}-\d{2}-\d{4}$").sum())
    n["data.swapped_dates"] = int(len(raw) - n["data.text_dates"])
    nbsp = "\u00a0"  # non-breaking space: keeps dates on one line in the PDF
    n["data.date_min"] = orders["Order Date"].min().strftime(f"%d{nbsp}%b{nbsp}%Y")
    n["data.date_max"] = orders["Order Date"].max().strftime(f"%d{nbsp}%b{nbsp}%Y")
    n["data.max_lines_per_order"] = int(merged.groupby("Order ID").size().max())
    n["data.single_line_orders"] = int((merged.groupby("Order ID").size() == 1).sum())
    n["data.multi_category_orders"] = int((merged.groupby("Order ID")["Category"].nunique() > 1).sum())
    n["data.repeat_subcat_lines"] = int(merged.duplicated(["Order ID", "Category", "Sub-Category"]).sum())
    n["data.delhi_in_mp"] = int(((orders["State"] == "Madhya Pradesh") & (orders["City"] == "Delhi")).sum())
    n["data.chandigarh_pb"] = int(((orders["City"] == "Chandigarh") & (orders["State"] == "Punjab")).sum())
    n["data.chandigarh_hr"] = int(((orders["City"] == "Chandigarh") & (orders["State"] == "Haryana")).sum())
    n["data.states"] = int(orders["State"].nunique())
    n["data.cities"] = int(orders["City"].nunique())
    n["data.subcats"] = int(merged["Sub-Category"].nunique())

    # ---- company totals ---------------------------------------------------
    n["total.sales"] = int(merged["Amount"].sum())
    n["total.profit"] = int(merged["Profit"].sum())
    n["total.margin"] = 100 * n["total.profit"] / n["total.sales"]
    n["total.orders"] = int(orders["Order ID"].nunique())
    n["total.lines"] = int(len(merged))
    n["total.loss_lines"] = int((merged["Profit"] < 0).sum())
    n["total.loss_line_share"] = 100 * n["total.loss_lines"] / n["total.lines"]

    # ---- Part 1 -----------------------------------------------------------
    n.update(_flatten("cat", cat))
    n.update(_flatten("sub", sub.set_index(["Category", "Sub-Category"])))
    n.update(_flatten("loss", loss))
    for c in cat.index:
        n[f"cat.{c}.order_line_ratio"] = cat.loc[c, "profit_per_order"] / cat.loc[c, "profit_per_line"]
    ratios = cat["profit_per_order"] / cat["profit_per_line"]
    n["p1.order_line_ratio_min"] = float(ratios.min())
    n["p1.order_line_ratio_max"] = float(ratios.max())
    n["p1.ranks_agree"] = bool((cat["profit_per_order"].rank() == cat["profit_per_line"].rank()).all())
    furn = sub[sub["Category"] == "Furniture"]
    ex_tab = furn[furn["Sub-Category"] != "Tables"]
    n["p1.furn_ex_tables_profit"] = int(ex_tab["profit"].sum())
    n["p1.furn_ex_tables_margin"] = 100 * ex_tab["profit"].sum() / ex_tab["amount"].sum()
    cloth = sub[sub["Category"] == "Clothing"]
    ex_saree = cloth[cloth["Sub-Category"] != "Saree"]
    n["p1.cloth_ex_saree_margin"] = 100 * ex_saree["profit"].sum() / ex_saree["amount"].sum()
    elec = sub[sub["Category"] == "Electronics"]
    ex_games = elec[elec["Sub-Category"] != "Electronic Games"]
    n["p1.elec_ex_games_margin"] = 100 * ex_games["profit"].sum() / ex_games["amount"].sum()
    neg = sub[sub["profit"] < 0]
    n["p1.loss_subcats"] = _join_names(neg["Sub-Category"].tolist())
    n["p1.n_loss_subcats"] = len(neg)
    # price-realisation check
    lower = pr[pr["price_ratio_loss_vs_profit"] < 1]
    n["p1.price_n_subcats"] = len(pr)
    n["p1.price_n_lower"] = len(lower)
    n["p1.price_median_ratio"] = float(pr["price_ratio_loss_vs_profit"].median())
    n["p1.price_min_ratio"] = float(pr["price_ratio_loss_vs_profit"].min())
    n["p1.price_max_ratio_lower"] = float(lower["price_ratio_loss_vs_profit"].max())
    n["p1.price_exception"] = _join_names(pr.loc[pr["price_ratio_loss_vs_profit"] >= 1, "Sub-Category"].tolist())
    n["p1.price_exception_ratio"] = float(pr.loc[pr["price_ratio_loss_vs_profit"] >= 1, "price_ratio_loss_vs_profit"].max())
    n["p1.qty_median_loss"] = float(merged.loc[merged["Profit"] < 0, "Quantity"].median())
    n["p1.qty_median_profit"] = float(merged.loc[merged["Profit"] > 0, "Quantity"].median())
    for c, r in pr.set_index("Sub-Category").iterrows():
        n[f"price.{c}.ratio"] = float(r["price_ratio_loss_vs_profit"])

    # ---- Part 2 -----------------------------------------------------------
    mom, tva, rp, att = t["mom"], t["tva"], t["rephased"], t["attain"]
    n["p2.target_first"] = float(mom["Target"].iloc[0])
    n["p2.target_last"] = float(mom["Target"].iloc[-1])
    n["p2.target_growth_pct"] = 100 * (mom["Target"].iloc[-1] / mom["Target"].iloc[0] - 1)
    n["p2.target_annual"] = float(mom["Target"].sum())
    n["p2.mom_min"] = float(mom["mom_pct"].min())
    n["p2.mom_max"] = float(mom["mom_pct"].max())
    n["p2.mom_mean"] = float(mom["mom_pct"].mean())
    n["p2.mom_sd"] = float(mom["mom_pct"].std(ddof=1))
    n["p2.z"] = config.FLUCTUATION_Z
    n["p2.material_pct"] = config.MATERIAL_MOM_PCT
    n["p2.z_upper"] = n["p2.mom_mean"] + config.FLUCTUATION_Z * n["p2.mom_sd"]
    n["p2.z_lower"] = n["p2.mom_mean"] - config.FLUCTUATION_Z * n["p2.mom_sd"]
    flagged = mom[mom["flag_relative"]]
    n["p2.flagged_months"] = _join_names([_month(m) for m in flagged["Month"]])
    n["p2.n_flagged"] = len(flagged)
    n["p2.n_material"] = int(mom["flag_material"].sum())
    n["p2.step_small"] = float(mom["mom_abs"].min())
    n["p2.step_large"] = float(mom["mom_abs"].max())
    regular = mom[mom["mom_abs"] == mom["mom_abs"].min()]
    n["p2.regular_mom_max"] = float(regular["mom_pct"].max())
    n["p2.regular_z_max"] = float(regular["mom_z"].max())
    n["p2.step200_months"] = _join_names([_month(m) for m in mom.loc[mom["mom_abs"] == mom["mom_abs"].max(), "Month"]])
    for _, r in mom.iterrows():
        k = r["Month"].strftime("%Y-%m")
        n[f"mom.{k}.target"] = float(r["Target"])
        n[f"mom.{k}.mom_pct"] = None if pd.isna(r["mom_pct"]) else float(r["mom_pct"])
        n[f"mom.{k}.z"] = None if pd.isna(r["mom_z"]) else float(r["mom_z"])
    near = mom[(~mom["flag_relative"]) & (mom["mom_abs"] == mom["mom_abs"].max())]
    n["p2.near_miss_month"] = _join_names([_month(m) for m in near["Month"]])
    n["p2.near_miss_z"] = float(near["mom_z"].max()) if len(near) else float("nan")
    # actual vs target
    n["p2.actual_annual"] = float(tva["Actual"].sum())
    n["p2.attain_annual"] = 100 * tva["Actual"].sum() / tva["Target"].sum()
    n["p2.gap_annual"] = float(tva["Actual"].sum() - tva["Target"].sum())
    n["p2.months_met"] = int((tva["Actual"] >= tva["Target"]).sum())
    n["p2.actual_mom_min"] = float(tva["actual_mom_pct"].min())
    n["p2.actual_mom_max"] = float(tva["actual_mom_pct"].max())
    n["p2.actual_mom_max_month"] = _month(tva.loc[tva["actual_mom_pct"].idxmax(), "Month"])
    n["p2.actual_mom_min_month"] = _month(tva.loc[tva["actual_mom_pct"].idxmin(), "Month"])
    n["p2.target_cv"] = float(att.loc[config.TARGET_CATEGORY, "target_cv_pct"])
    n["p2.actual_cv"] = float(att.loc[config.TARGET_CATEGORY, "actual_cv_pct"])
    n["p2.attain_min"] = float(tva["attainment_pct"].min())
    n["p2.attain_min_month"] = _month(tva.loc[tva["attainment_pct"].idxmin(), "Month"])
    n["p2.attain_max"] = float(tva["attainment_pct"].max())
    n["p2.attain_max_month"] = _month(tva.loc[tva["attainment_pct"].idxmax(), "Month"])
    # leading run of misses
    met = (tva["Actual"] >= tva["Target"]).tolist()
    run = met.index(True) if True in met else len(met)
    n["p2.lead_miss_months"] = run
    n["p2.lead_miss_end"] = _month(tva["Month"].iloc[run - 1])
    lead = tva.iloc[:run]
    n["p2.lead_miss_gap"] = float(lead["gap"].sum())
    n["p2.lead_miss_attain"] = 100 * lead["Actual"].sum() / lead["Target"].sum()
    tail = tva.iloc[run:]
    n["p2.tail_months"] = len(tail)
    n["p2.tail_met"] = int((tail["Actual"] >= tail["Target"]).sum())
    n["p2.tail_gap"] = float(tail["gap"].sum())
    n["p2.tail_attain"] = 100 * tail["Actual"].sum() / tail["Target"].sum()
    n["p2.tail_start"] = _month(tail["Month"].iloc[0])
    h1, h2 = tva.iloc[:6], tva.iloc[6:]
    n["p2.h1_attain"] = 100 * h1["Actual"].sum() / h1["Target"].sum()
    n["p2.h2_attain"] = 100 * h2["Actual"].sum() / h2["Target"].sum()
    n["p2.h1_share_target"] = 100 * h1["Target"].sum() / tva["Target"].sum()
    n["p2.h1_share_actual"] = 100 * h1["Actual"].sum() / tva["Actual"].sum()
    n["p2.loss_months"] = int((tva["Profit"] < 0).sum())
    n["p2.loss_months_list"] = _join_names([_month(m) for m in tva.loc[tva["Profit"] < 0, "Month"]])
    n["p2.loss_months_sales"] = float(tva.loc[tva["Profit"] < 0, "Actual"].sum())
    n["p2.loss_months_loss"] = float(tva.loc[tva["Profit"] < 0, "Profit"].sum())
    n["p2.worst_margin"] = float(tva["margin_pct"].min())
    n["p2.worst_margin_month"] = _month(tva.loc[tva["margin_pct"].idxmin(), "Month"])
    for _, r in tva.iterrows():
        k = r["Month"].strftime("%Y-%m")
        for col in ("Actual", "gap", "attainment_pct", "Profit", "margin_pct", "Orders"):
            n[f"tva.{k}.{col}"] = float(r[col])
    n["p2.mape_current"] = mape(rp["Actual"], rp["Target"])
    n["p2.mape_rephased"] = mape(rp["Actual"], rp["Rephased"])
    rpx = t["rephased_exfurn"]
    n["p2.mape_rephased_exfurn"] = mape(rpx["Actual"], rpx["Rephased"])
    n["p2.min_month_orders"] = int(tva["Orders"].min())
    n["p2.max_month_orders"] = int(tva["Orders"].max())
    n["p2.rephased_min"] = float(rp["Rephased"].min())
    n["p2.rephased_min_month"] = _month(rp.loc[rp["Rephased"].idxmin(), "Month"])
    n["p2.rephased_max"] = float(rp["Rephased"].max())
    n["p2.rephased_max_month"] = _month(rp.loc[rp["Rephased"].idxmax(), "Month"])
    band = config.TARGET_BAND_PCT
    n["p2.band"] = band
    n["p2.rephased_months_within_band"] = int(((rp["rephased_attainment_pct"] - 100).abs() <= band).sum())
    n["p2.current_months_within_band"] = int(((rp["attainment_pct"] - 100).abs() <= band).sum())
    n["p2.cv_ratio"] = n["p2.actual_cv"] / n["p2.target_cv"]
    n.update(_flatten("att", att))

    # ---- Part 3 -----------------------------------------------------------
    states, top, cities = t["states"], t["top"], t["cities"]
    n.update(_flatten("state", states))
    for i, s in enumerate(top.index, start=1):
        n[f"top.{i}"] = s
    n["p3.top_list"] = _join_names(top.index.tolist())
    n["p3.top_tied"] = bool(top["tied_at_cutoff"].iloc[0])
    n["p3.next_orders"] = int(states["orders"].iloc[config.TOP_N_STATES])
    n["p3.next_states"] = _join_names(states.index[states["orders"] == n["p3.next_orders"]].tolist())
    top2 = states.head(2)
    n["p3.top2_order_share"] = 100 * top2["orders"].sum() / states["orders"].sum()
    n["p3.top2_sales_share"] = float(top2["sales_share_pct"].sum())
    n["p3.top5_order_share"] = 100 * top["orders"].sum() / states["orders"].sum()
    n["p3.top5_sales_share"] = float(top["sales_share_pct"].sum())
    n["p3.top5_profit_share"] = float(top["profit_share_pct"].sum())
    lossy = states[states["profit"] < 0].sort_values("profit")
    n["p3.loss_states"] = _join_names(lossy.index.tolist())
    n["p3.n_loss_states"] = len(lossy)
    n["p3.loss_states_total"] = int(lossy["profit"].sum())
    n["p3.loss_states_sales"] = int(lossy["sales"].sum())
    hi = states[(states["share_gap_pp"] > config.OVEREARNER_GAP_PP)].sort_values("share_gap_pp", ascending=False)
    n["p3.overearners"] = _join_names(hi.index.tolist())
    n["p3.n_overearners"] = len(hi)
    n["p3.overearners_sales_share"] = float(hi["sales_share_pct"].sum())
    n["p3.overearners_profit_share"] = float(hi["profit_share_pct"].sum())
    n["p3.overearners_margin"] = 100 * hi["profit"].sum() / hi["sales"].sum()
    n["p3.overearners_orders"] = int(hi["orders"].sum())
    cities = cities.assign(key=cities["City"] + "@" + cities["State"])
    n.update(_flatten("city", cities.set_index("key").drop(columns=["City", "State"])))
    mumbai = cities[cities["City"] == "Mumbai"].iloc[0]
    pune = cities[cities["City"] == "Pune"].iloc[0]
    n["p3.mumbai_uplift_company"] = float(mumbai["sales"] * n["total.margin"] / 100 - mumbai["profit"])
    n["p3.mumbai_uplift_pune"] = float(mumbai["sales"] * pune["margin_pct"] / 100 - mumbai["profit"])
    indore = cities[cities["City"] == "Indore"].iloc[0]
    n["p3.indore_uplift_company"] = float(indore["sales"] * n["total.margin"] / 100 - indore["profit"])
    top_states_set = set(top.index)
    top_loss_cities = cities[cities["State"].isin(top_states_set) & (cities["profit"] < 0)]
    n["p3.loss_cities_top5"] = int(top_loss_cities["profit"].sum())
    n["p3.loss_cities_top5_names"] = _join_names(top_loss_cities["City"].tolist())
    n["p3.loss_cities_top5_states"] = _join_names(sorted(top_loss_cities["State"].unique().tolist()))
    loss_cities = cities[cities["profit"] < 0].sort_values("profit")
    n["p3.n_loss_cities"] = len(loss_cities)
    n["p3.loss_cities_total"] = int(loss_cities["profit"].sum())
    top_city = cities.sort_values("sales", ascending=False).head(2)
    n["p3.top2_city_sales_share"] = float(top_city["sales_share_pct"].sum())
    n["p3.top2_city_profit_share"] = float(top_city["profit_share_pct"].sum())
    n.update(_flatten("stcat", t["state_cat"].set_index(["State", "Category"])))
    n.update(_flatten("opp", t["opps"].set_index("code")))
    n.update({f"q3.{k}": v for k, v in sizing().items()})
    n["data.min_state_orders"] = int(states["orders"].min())
    n["data.min_state_orders_name"] = states["orders"].idxmin()
    return n

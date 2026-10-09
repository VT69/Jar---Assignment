"""All report figures. Each function takes computed tables and writes one PNG.

Style rules: one y-scale per axes (no dual axes), hairline solid grid, category
colours fixed by entity (never by rank), status red reserved for losses/flags,
rupee axes labelled with units and Indian-style compact ticks.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless, deterministic rendering
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullLocator  # noqa: E402

from src import config as C  # noqa: E402
from src.formatting import inr, inr_compact  # noqa: E402

CATEGORY_ORDER: list[str] = ["Electronics", "Clothing", "Furniture"]
RUPEE_FMT = FuncFormatter(lambda v, _: inr_compact(v))
PCT_FMT = FuncFormatter(lambda v, _: f"{v:g}%")


def apply_style() -> None:
    """Set a consistent, recessive matplotlib style for every figure."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",  # ships with matplotlib and has the ₹ glyph
            "font.size": 9.5,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.labelsize": 9.5,
            "axes.labelcolor": C.INK_SECONDARY,
            "axes.edgecolor": C.BASELINE,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": C.GRID,
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "xtick.color": C.INK_MUTED,
            "ytick.color": C.INK_MUTED,
            "xtick.labelcolor": C.INK_SECONDARY,
            "ytick.labelcolor": C.INK_SECONDARY,
            "text.color": C.INK_PRIMARY,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "savefig.dpi": C.FIG_DPI,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
            "svg.hashsalt": "jar",  # determinism
        }
    )


def _save(fig: plt.Figure, path: Path, suptitle: str, subtitle: str | None = None) -> Path:
    # Title block sits above the axes area (in inches, so it never collides with panel titles);
    # bbox_inches="tight" grows the canvas to include it.
    h = fig.get_figheight()
    has_panel_titles = any(ax.get_title() for ax in fig.axes)
    fig.subplots_adjust(top=1 - (0.42 if has_panel_titles else 0.10) / h)
    fig.text(0.01, 1 + 0.62 / h, suptitle, ha="left", va="bottom", fontsize=12.5, fontweight="bold",
             color=C.INK_PRIMARY)
    if subtitle:
        fig.text(0.01, 1 + 0.30 / h, subtitle, ha="left", va="bottom", fontsize=9, color=C.INK_SECONDARY)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
    return path


def _hbar_labels(ax: plt.Axes, bars, labels: list[str], pad_frac: float = 0.015) -> None:
    """Direct-label horizontal bars just past their end (both signs)."""
    xmin, xmax = ax.get_xlim()
    pad = (xmax - xmin) * pad_frac
    for bar, text in zip(bars, labels):
        w = bar.get_width()
        x = w + pad if w >= 0 else w - pad
        ax.text(x, bar.get_y() + bar.get_height() / 2, text, va="center",
                ha="left" if w >= 0 else "right", fontsize=8.5, color=C.INK_SECONDARY)


# --------------------------------------------------------------------------- #
# Part 1
# --------------------------------------------------------------------------- #
def category_overview(cat: pd.DataFrame, path: Path, title: str) -> Path:
    """Three panels: total sales, profit per order vs per line, and margin."""
    df = cat.reindex(CATEGORY_ORDER)
    colors = [C.CATEGORY_COLORS[c] for c in df.index]
    y = np.arange(len(df))[::-1]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), gridspec_kw={"wspace": 0.55})

    ax = axes[0]
    bars = ax.barh(y, df["amount"], color=colors, height=0.55)
    ax.set_xlim(0, df["amount"].max() * 1.32)
    _hbar_labels(ax, bars, [inr(v) for v in df["amount"]])
    ax.set_title("Total sales")
    ax.set_xlabel("Sales (₹)")
    ax.xaxis.set_major_formatter(RUPEE_FMT)

    ax = axes[1]
    h = 0.36
    b1 = ax.barh(y + h / 2, df["profit_per_order"], height=h, color=colors, label="Per order (primary)")
    b2 = ax.barh(y - h / 2, df["profit_per_line"], height=h, color=colors, alpha=0.38, label="Per line item")
    ax.set_xlim(0, df["profit_per_order"].max() * 1.35)
    _hbar_labels(ax, b1, [inr(v, 2) for v in df["profit_per_order"]])
    _hbar_labels(ax, b2, [inr(v, 2) for v in df["profit_per_line"]])
    ax.set_title("Average profit")
    ax.set_xlabel("Profit (₹)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncols=2, handlelength=1.0)
    for handle in ax.get_legend().legend_handles:
        handle.set_color(C.INK_MUTED)
    ax.get_legend().legend_handles[1].set_alpha(0.38)

    ax = axes[2]
    bars = ax.barh(y, df["margin_pct"], color=colors, height=0.55)
    ax.set_xlim(0, df["margin_pct"].max() * 1.35)
    _hbar_labels(ax, bars, [f"{v:.2f}%" for v in df["margin_pct"]])
    ax.set_title("Profit margin")
    ax.set_xlabel("Profit ÷ sales (%)")
    ax.xaxis.set_major_formatter(PCT_FMT)

    for ax in axes:
        ax.set_yticks(y, df.index)
        ax.grid(axis="y", visible=False)
    return _save(fig, path, title,
                 "Category totals across all 500 orders, Apr 2018 - Mar 2019")


def subcategory_profit(sub: pd.DataFrame, path: Path, title: str) -> Path:
    """Profit by sub-category, grouped by category, with margin labels."""
    df = sub.copy()
    df["Category"] = pd.Categorical(df["Category"], CATEGORY_ORDER, ordered=True)
    df = df.sort_values(["Category", "profit"], ascending=[True, True])
    # build y positions with a gap between categories
    ys, labels, y, prev = [], [], 0.0, None
    for _, r in df.iloc[::-1].iterrows():
        if prev is not None and r["Category"] != prev:
            y += 0.7
        ys.append(y)
        labels.append(r["Sub-Category"])
        prev = r["Category"]
        y += 1
    df = df.iloc[::-1].assign(y=ys)
    fig, ax = plt.subplots(figsize=(9.5, 6.4))
    colors = [C.CATEGORY_COLORS[c] for c in df["Category"]]
    bars = ax.barh(df["y"], df["profit"], color=colors, height=0.68)
    lim = df["profit"].abs().max() * 1.55
    ax.set_xlim(-lim * 0.92, lim)
    _hbar_labels(ax, bars, [f"{inr(p)}  ({m:.1f}%)" for p, m in zip(df["profit"], df["margin_pct"])])
    ax.axvline(0, color=C.BASELINE, lw=0.9)
    ax.set_yticks(df["y"], labels)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Total profit (₹)  -  label shows profit and (margin %)")
    ax.xaxis.set_major_formatter(RUPEE_FMT)
    handles = [plt.Rectangle((0, 0), 1, 1, color=C.CATEGORY_COLORS[c]) for c in CATEGORY_ORDER]
    ax.legend(handles, CATEGORY_ORDER, loc="lower right", ncols=3)
    return _save(fig, path, title,
                 "Total profit by sub-category; bars sorted within each category")


def loss_concentration(loss: pd.DataFrame, path: Path, title: str) -> Path:
    """Gross gains vs gross losses per category, with net profit and loss ratio."""
    df = loss.reindex(CATEGORY_ORDER)
    y = np.arange(len(df))[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.3), gridspec_kw={"wspace": 0.45, "width_ratios": [1.5, 1]})
    ax = axes[0]
    h = 0.36
    colors = [C.CATEGORY_COLORS[c] for c in df.index]
    g = ax.barh(y + h / 2, df["gross_gain"], height=h, color=colors, label="Profit on profitable lines")
    l_ = ax.barh(y - h / 2, -df["gross_loss"], height=h, color=C.CRITICAL, label="Loss on loss-making lines")
    lim = max(df["gross_gain"].max(), df["gross_loss"].max()) * 1.45
    ax.set_xlim(-lim, lim)
    _hbar_labels(ax, g, [inr(v) for v in df["gross_gain"]])
    _hbar_labels(ax, l_, [f"-{inr(v)}" for v in df["gross_loss"]])
    ax.axvline(0, color=C.BASELINE, lw=0.9)
    ax.set_yticks(y, [f"{c}\nnet {inr(n)}" for c, n in zip(df.index, df["net_profit"])])
    ax.set_title("Gains vs losses")
    ax.set_xlabel("Profit (₹)")
    ax.xaxis.set_major_formatter(RUPEE_FMT)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncols=2, fontsize=8)
    ax.get_legend().legend_handles[0].set_color(C.INK_MUTED)

    ax = axes[1]
    b = ax.barh(y, df["loss_to_gain_pct"], color=colors, height=0.55)
    ax.set_xlim(0, 115)
    _hbar_labels(ax, b, [f"{v:.1f}%" for v in df["loss_to_gain_pct"]])
    ax.set_yticks(y, df.index)
    ax.set_title("Share of gains wiped out by losses")
    ax.set_xlabel("Gross loss ÷ gross gain (%)")
    ax.xaxis.set_major_formatter(PCT_FMT)
    for a in axes:
        a.grid(axis="y", visible=False)
    return _save(fig, path, title,
                 "Line-level gains and losses by category")


def price_realisation(pr: pd.DataFrame, path: Path, title: str) -> Path:
    """Dot plot: median unit price on loss lines relative to profitable lines."""
    df = pr.copy()
    df["Category"] = pd.Categorical(df["Category"], CATEGORY_ORDER, ordered=True)
    df = df.sort_values(["Category", "price_ratio_loss_vs_profit"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    y = np.arange(len(df))[::-1]
    for cat in CATEGORY_ORDER:
        m = df["Category"] == cat
        ax.scatter(df.loc[m, "price_ratio_loss_vs_profit"], y[m.values], s=46, color=C.CATEGORY_COLORS[cat],
                   label=cat, zorder=3, edgecolor="white", linewidth=1.2)
    ax.axvline(1.0, color=C.INK_SECONDARY, lw=1)
    ax.text(1.02, y.max() + 0.6, "Same price", fontsize=8, color=C.INK_SECONDARY, va="bottom")
    ax.set_xscale("log")
    ax.xaxis.set_minor_locator(NullLocator())
    ticks = [0.25, 0.5, 1, 2, 3]
    ax.set_xticks(ticks, [f"{t:g}×" for t in ticks])
    ax.set_xlim(0.25, 3.5)
    ax.set_yticks(y, df["Sub-Category"])
    ax.set_ylim(-0.8, y.max() + 1.5)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Median unit price on loss lines ÷ median unit price on profitable lines (log scale)")
    ax.legend(loc="lower right")
    for i, r in df.iterrows():
        ax.text(r["price_ratio_loss_vs_profit"] * 1.06, y[i], f"{r['price_ratio_loss_vs_profit']:.2f}×",
                va="center", fontsize=7.5, color=C.INK_MUTED)
    return _save(fig, path, title,
                 "Price-realisation check: no discount field exists, so realised unit price (Amount ÷ Quantity) is compared")


# --------------------------------------------------------------------------- #
# Part 2
# --------------------------------------------------------------------------- #
def _month_ticks(ax: plt.Axes, months: pd.Series) -> None:
    ax.set_xticks(range(len(months)), [m.strftime("%b\n%y") for m in months])


def target_mom(mom: pd.DataFrame, z: float, path: Path, title: str) -> Path:
    """Furniture target level (top) and MoM % change with flagged months (bottom)."""
    x = np.arange(len(mom))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 5.6), sharex=True, gridspec_kw={"height_ratios": [1, 1], "hspace": 0.3})
    a1.plot(x, mom["Target"], color=C.CATEGORY_COLORS["Furniture"], lw=2, marker="o", ms=5)
    for i in (0, len(mom) - 1):
        a1.annotate(inr(mom["Target"].iloc[i]), (x[i], mom["Target"].iloc[i]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8.5, color=C.INK_SECONDARY)
    a1.set_ylim(mom["Target"].min() * 0.96, mom["Target"].max() * 1.03)
    a1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: inr(v)))
    a1.set_ylabel("Monthly target (₹)")
    a1.set_title("Furniture monthly sales target")

    vals = mom["mom_pct"].fillna(0)
    colors = [C.CRITICAL if f else C.CATEGORY_COLORS["Furniture"] for f in mom["flag_relative"]]
    bars = a2.bar(x[1:], vals[1:], color=colors[1:], width=0.6)
    mean, sd = mom["mom_pct"].mean(), mom["mom_pct"].std(ddof=1)
    upper = mean + z * sd
    a2.axhline(upper, color=C.INK_SECONDARY, lw=0.9)
    a2.text(-0.35, upper + 0.05, f"mean + {z:g} SD\n= {upper:.2f}%", ha="left", va="bottom", fontsize=8,
            color=C.INK_SECONDARY)
    for b, v, f in zip(bars, vals[1:], mom["flag_relative"][1:]):
        a2.text(b.get_x() + b.get_width() / 2, v + 0.04, f"{v:+.2f}%" + ("\nflagged" if f else ""),
                ha="center", va="bottom", fontsize=7.5, color=C.CRITICAL if f else C.INK_SECONDARY,
                bbox={"fc": "white", "ec": "none", "pad": 0.4}, zorder=4)
    a2.set_ylim(0, vals.max() * 1.55)
    a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}%"))
    a2.set_ylabel("MoM change (%)")
    a2.set_title("Month-over-month % change in target")
    _month_ticks(a2, mom["Month"])
    a2.grid(axis="x", visible=False)
    a1.grid(axis="x", visible=False)
    return _save(fig, path, title,
                 f"Red = flagged by the z-score rule (|MoM % - mean| > {z:g} SD)")


def target_vs_actual(rp: pd.DataFrame, path: Path, title: str) -> Path:
    """Actual Furniture sales vs current and re-phased target, plus attainment."""
    x = np.arange(len(rp))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.4, 1], "hspace": 0.3})
    a1.bar(x, rp["Actual"], color=C.CATEGORY_COLORS["Furniture"], width=0.6, label="Actual sales")
    a1.plot(x, rp["Target"], color=C.INK_PRIMARY, lw=2, marker="o", ms=4, label="Current target")
    a1.plot(x, rp["Rephased"], color=C.INK_SECONDARY, lw=1.5, ls=(0, (4, 2)), marker="s", ms=3.5,
            label="Illustrative re-phased target (same annual total)")
    a1.yaxis.set_major_formatter(RUPEE_FMT)
    a1.set_ylabel("Sales (₹)")
    a1.set_ylim(0, rp[["Actual", "Target", "Rephased"]].max().max() * 1.18)
    a1.legend(loc="upper left", ncols=1)
    a1.set_title("Furniture: actual monthly sales vs target")
    a1.grid(axis="x", visible=False)

    att = rp["attainment_pct"]
    colors = [C.GOOD if v >= 100 else C.CRITICAL for v in att]
    bars = a2.bar(x, att - 100, bottom=100, color=colors, width=0.6)
    a2.axhline(100, color=C.INK_SECONDARY, lw=1)
    for b, v in zip(bars, att):
        a2.text(b.get_x() + b.get_width() / 2, v + (4 if v >= 100 else -4), f"{v:.0f}%",
                ha="center", va="bottom" if v >= 100 else "top", fontsize=7.5, color=C.INK_SECONDARY)
    a2.set_ylim(0, att.max() * 1.18)
    a2.yaxis.set_major_formatter(PCT_FMT)
    a2.set_ylabel("Attainment (%)")
    a2.set_title("Attainment vs current target (green = met, red = missed)")
    _month_ticks(a2, rp["Month"])
    a2.grid(axis="x", visible=False)
    return _save(fig, path, title,
                 "Actual = sum of Furniture line Amounts per repaired order month")


# --------------------------------------------------------------------------- #
# Part 3
# --------------------------------------------------------------------------- #
def top_states(top: pd.DataFrame, path: Path, title: str) -> Path:
    """Top-5 states: orders, total sales and average profit per order."""
    df = top.iloc[::-1]
    y = np.arange(len(df))
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.2), gridspec_kw={"wspace": 0.75})
    specs = [
        ("orders", "Distinct orders", "Orders", lambda v: f"{v:,.0f}", None),
        ("sales", "Total sales", "Sales (₹)", inr, RUPEE_FMT),
        ("profit_per_order", "Avg profit per order", "Profit per order (₹)", lambda v: inr(v, 2), None),
    ]
    for ax, (col, panel_title, xlabel, fmt, tick_fmt) in zip(axes, specs):
        colors = [C.CRITICAL if v < 0 else C.ACCENT for v in df[col]]
        bars = ax.barh(y, df[col], color=colors, height=0.55)
        span = df[col].max() - min(0, df[col].min())
        lo = df[col].min() - 0.45 * span if df[col].min() < 0 else 0
        ax.set_xlim(lo, df[col].max() * 1.45)
        _hbar_labels(ax, bars, [fmt(v) for v in df[col]])
        ax.axvline(0, color=C.BASELINE, lw=0.9)
        ax.set_yticks(y, df.index)
        ax.set_title(panel_title)
        ax.set_xlabel(xlabel)
        if tick_fmt:
            ax.xaxis.set_major_formatter(tick_fmt)
        ax.grid(axis="y", visible=False)
    return _save(fig, path, title,
                 "Top 5 states by distinct Order ID count. Red = negative")


def state_share_gap(states: pd.DataFrame, path: Path, title: str) -> Path:
    """Diverging bars: profit share minus sales share, every state."""
    df = states.sort_values("share_gap_pp")
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    colors = [C.CRITICAL if round(v, 1) < 0 else C.ACCENT if round(v, 1) > 0 else C.NEUTRAL for v in df["share_gap_pp"]]
    bars = ax.barh(y, df["share_gap_pp"], color=colors, height=0.65)
    ax.set_xlim(df["share_gap_pp"].min() * 2.5, df["share_gap_pp"].max() * 1.9)
    labels = [f"{round(g, 1) + 0.0:+.1f} pp   ({m:.1f}% margin{', LOSS' if p < 0 else ''})"
              for g, m, p in zip(df["share_gap_pp"], df["margin_pct"], df["profit"])]
    _hbar_labels(ax, bars, labels)
    ax.axvline(0, color=C.INK_SECONDARY, lw=0.9)
    ax.set_yticks(y, df.index)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Share of company profit − share of company sales (percentage points)")
    return _save(fig, path, title,
                 "Blue = state captures more profit than its sales share; red = less")


def city_map(cities: pd.DataFrame, highlight: list[str], path: Path, title: str) -> Path:
    """City scatter: sales vs margin, bubble = orders, priority cities labelled."""
    df = cities.copy()
    df["label"] = df["City"] + " (" + df["State"].map(_abbr) + ")"
    fig, ax = plt.subplots(figsize=(10, 5.8))
    company_margin = 100 * df["profit"].sum() / df["sales"].sum()
    sizes = 18 + df["orders"] * 4.5
    loss = df["profit"] < 0
    ax.scatter(df.loc[~loss, "sales"], df.loc[~loss, "margin_pct"], s=sizes[~loss], color=C.ACCENT, alpha=0.7,
               edgecolor="white", linewidth=1.5, zorder=3, label="Profitable city")
    ax.scatter(df.loc[loss, "sales"], df.loc[loss, "margin_pct"], s=sizes[loss], color=C.CRITICAL, alpha=0.8,
               edgecolor="white", linewidth=1.5, zorder=3, label="Loss-making city")
    ax.axhline(company_margin, color=C.INK_SECONDARY, lw=0.9)
    ax.text(df["sales"].max() * 0.42, company_margin + 0.6, f"Company margin {company_margin:.2f}%", fontsize=8,
            color=C.INK_SECONDARY, va="bottom", ha="left")
    ax.axhline(0, color=C.BASELINE, lw=0.9)
    # Label placement as (Δ sales in ₹, Δ margin in pp) from the point; leader lines keep the cluster legible.
    nudges = {"Mumbai (MH)": (-14000, -9), "Indore (MP)": (-16000, 6), "Pune (MH)": (1500, 3),
              "Chennai (TN)": (3000, 1.5), "Chandigarh (PB)": (7000, -3), "Ahmedabad (GJ)": (5000, 0.5),
              "Jaipur (RJ)": (-9000, -7), "Allahabad (UP)": (2500, 3), "Bhopal (MP)": (2500, -3.5)}
    for _, r in df[df["label"].isin(highlight)].iterrows():
        dx, dy = nudges.get(r["label"], (2000, 2))
        ax.annotate(f"{r['label']}  {r['margin_pct']:.1f}%", (r["sales"], r["margin_pct"]),
                    xytext=(r["sales"] + dx, r["margin_pct"] + dy), ha="left", va="center", fontsize=8,
                    color=C.INK_PRIMARY,
                    arrowprops={"arrowstyle": "-", "color": C.INK_MUTED, "lw": 0.6, "shrinkA": 2, "shrinkB": 5})
    ax.xaxis.set_major_formatter(RUPEE_FMT)
    ax.yaxis.set_major_formatter(PCT_FMT)
    ax.set_xlabel("City sales (₹)")
    ax.set_ylabel("City profit margin (%)")
    ax.set_xlim(0, df["sales"].max() * 1.08)
    handles = [plt.Line2D([], [], ls="", marker="o", ms=8, color=c, alpha=a, label=lbl)
               for c, a, lbl in ((C.ACCENT, 0.7, "Profitable city"), (C.CRITICAL, 0.8, "Loss-making city"))]
    ax.legend(handles=handles, loc="lower right")
    return _save(fig, path, title,
                 "Each bubble is a city (size = distinct orders). Labels show priority cities and their margin")


_ABBR = {
    "Andhra Pradesh": "AP", "Bihar": "BR", "Delhi": "DL", "Goa": "GA", "Gujarat": "GJ", "Haryana": "HR",
    "Himachal Pradesh": "HP", "Jammu and Kashmir": "JK", "Karnataka": "KA", "Kerala": "KL",
    "Madhya Pradesh": "MP", "Maharashtra": "MH", "Nagaland": "NL", "Punjab": "PB", "Rajasthan": "RJ",
    "Sikkim": "SK", "Tamil Nadu": "TN", "Uttar Pradesh": "UP", "West Bengal": "WB",
}


def _abbr(state: str) -> str:
    return _ABBR.get(state, state[:2].upper())

"""Question 3 - opportunity scoring and the effort-vs-impact matrix.

Scores are analyst judgement on a 1-5 scale (stated as such in the report), kept
in code so the chart, the ranking and the text are generated from one source.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src import config as C  # noqa: E402


@dataclass(frozen=True)
class Opportunity:
    """One proposed business line with its prioritisation scores."""

    code: str
    name: str
    impact: float  # 1 (low) - 5 (high): revenue + engagement + strategic defensibility
    effort: float  # 1 (low) - 5 (high): build + licensing/partner + operational load
    horizon: str


OPPORTUNITIES: tuple[Opportunity, ...] = (
    # A: impact 4.0, not 5.0 - its quantified value (trail + retention, see sizing()) is ~3% of operating
    # revenue; the remainder of the case is defensibility of the gold habit, which is real but unsized.
    Opportunity("A", "SEBI-regulated gold ETF / FoF", impact=4.0, effort=2.5, horizon="Now (0-6 months)"),
    # B: effort 1.0 - Jar's goals feature and Nek both exist (goals confirmed in the Q2 session); the build is the link.
    Opportunity("B", "Connect savings goals to Nek redemption", impact=3.5, effort=1.0, horizon="Now (0-3 months)"),
    Opportunity("C", "Insured micro-deposits via bank partners", impact=4.0, effort=3.5, horizon="Next (6-12 months)"),
    Opportunity("D", "Sachet insurance on the AutoPay rail", impact=3.5, effort=3.5, horizon="Next (9-15 months)"),
    Opportunity("E", "Gold-backed micro-credit (partner-led)", impact=4.5, effort=4.5, horizon="Later (gated, 12+ months)"),
)
MIDPOINT: float = 3.0
LABEL_OFFSETS: dict[str, tuple[int, int]] = {"A": (-10, 16), "B": (-10, 16)}  # points; default: right of marker

# Back-of-envelope sizing assumptions (stated verbatim in the report).
REGISTERED_USERS: int = 35_000_000      # Jar-reported registered users (TechCrunch, Sep 2025)
ACTIVE_SHARE_PCT: float = 20.0          # ASSUMPTION: share of registered users actively saving (not published)
CORE_APP_REVENUE: float = 2.08e9        # FY25 operating revenue, ₹208 crore (Entrackr, 19 Sep 2025)
SIZING_A: dict[str, float] = {
    "adoption_pct": 10.0,       # % of active savers who add a regulated gold SIP
    "monthly_sip": 500.0,       # ₹ per month
    "trail_pct": 0.3,           # indicative annual distribution trail on AUM
    "churn_cut_pp": 2.0,        # cut in annual churn of the active base from offering a regulated option
}
SIZING_B: dict[str, float] = {
    "goal_pct": 5.0,            # % of active savers saving toward a jewellery goal
    "avg_goal": 12_000.0,       # ₹
    "redeem_pct": 30.0,         # % of those goals completed and redeemed at Nek
    "gross_margin_pct": 10.0,   # ASSUMPTION: jewellery gross margin (making charges carry most of it)
}


def sizing() -> dict[str, float]:
    """Back-of-envelope sizing for opportunities A and B from the stated assumptions.

    Both are sized on an assumed *active* base (registered users x ACTIVE_SHARE_PCT), not on registrations.
    A: new revenue = adopters x monthly SIP x 12 (year-one inflow) x trail; retention = active base x churn cut
       x operating revenue per active saver.
    B: goal-setters x average goal x redemption rate = Nek GMV from completed goals.
    """
    active = REGISTERED_USERS * ACTIVE_SHARE_PCT / 100
    rev_per_active = CORE_APP_REVENUE / active
    a_users = active * SIZING_A["adoption_pct"] / 100
    a_inflow = a_users * SIZING_A["monthly_sip"] * 12
    a_trail = a_inflow * SIZING_A["trail_pct"] / 100
    a_retained = active * SIZING_A["churn_cut_pp"] / 100
    a_retained_rev = a_retained * rev_per_active
    b_users = active * SIZING_B["goal_pct"] / 100
    b_orders = b_users * SIZING_B["redeem_pct"] / 100
    b_gmv = b_orders * SIZING_B["avg_goal"]
    out = {
        "registered_users": REGISTERED_USERS, "active_share_pct": ACTIVE_SHARE_PCT, "active_users": active,
        "core_revenue": CORE_APP_REVENUE, "rev_per_active": rev_per_active,
        "A.adoption_pct": SIZING_A["adoption_pct"], "A.monthly_sip": SIZING_A["monthly_sip"],
        "A.trail_pct": SIZING_A["trail_pct"], "A.users": a_users, "A.inflow": a_inflow,
        "A.trail_revenue": a_trail, "A.churn_cut_pp": SIZING_A["churn_cut_pp"], "A.retained_users": a_retained,
        "A.retained_revenue": a_retained_rev, "A.total_revenue": a_trail + a_retained_rev,
        "A.share_of_core_pct": 100 * (a_trail + a_retained_rev) / CORE_APP_REVENUE,
        "B.goal_pct": SIZING_B["goal_pct"], "B.avg_goal": SIZING_B["avg_goal"], "B.redeem_pct": SIZING_B["redeem_pct"],
        "B.users": b_users, "B.orders": b_orders, "B.gmv": b_gmv,
        "B.gross_margin_pct": SIZING_B["gross_margin_pct"], "B.margin": b_gmv * SIZING_B["gross_margin_pct"] / 100,
    }
    assert out["A.inflow"] > 0 and out["B.gmv"] > 0
    return out


def opportunity_table() -> pd.DataFrame:
    """Opportunities with a quadrant label and a simple priority score (impact / effort)."""
    df = pd.DataFrame([o.__dict__ for o in OPPORTUNITIES])

    def quadrant(r: pd.Series) -> str:
        hi_impact, lo_effort = r["impact"] >= MIDPOINT, r["effort"] <= MIDPOINT
        if hi_impact and lo_effort:
            return "Quick win / do now"
        if hi_impact:
            return "Big bet / sequence"
        if lo_effort:
            return "Fill-in"
        return "Deprioritise"

    df["quadrant"] = df.apply(quadrant, axis=1)
    df["priority_score"] = df["impact"] / df["effort"]
    # rank by impact/effort; ties go to the lower-effort option
    df = df.sort_values(["priority_score", "effort"], ascending=[False, True]).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    assert df["impact"].between(1, 5).all() and df["effort"].between(1, 5).all()
    return df


def matrix_figure(df: pd.DataFrame, path: Path) -> Path:
    """Effort-vs-impact scatter with quadrant shading and direct labels."""
    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    ax.axvline(MIDPOINT, color=C.BASELINE, lw=0.9)
    ax.axhline(MIDPOINT, color=C.BASELINE, lw=0.9)
    for (x, y, text) in ((0.68, 4.95, "QUICK WINS"), (4.92, 4.95, "BIG BETS"), (0.68, 1.12, "FILL-INS"),
                         (4.92, 1.12, "DEPRIORITISE")):
        ax.text(x, y, text, ha="left" if x < MIDPOINT else "right", va="top" if y > MIDPOINT else "bottom",
                fontsize=8, color=C.INK_MUTED, fontweight="bold")
    ax.scatter(df["effort"], df["impact"], s=220, color=C.ACCENT, edgecolor="white", linewidth=2, zorder=3)
    for _, r in df.iterrows():
        ax.text(r["effort"], r["impact"], r["code"], ha="center", va="center", color="white", fontsize=9,
                fontweight="bold", zorder=4)
        ax.annotate(r["name"], (r["effort"], r["impact"]), xytext=LABEL_OFFSETS.get(r["code"], (14, -3)),
                    textcoords="offset points", fontsize=8.5, color=C.INK_PRIMARY, ha="left", va="center")
    ax.set_xlim(0.6, 5.9)
    ax.set_ylim(1, 5.3)
    ax.set_xlabel("Effort (1 = low build, licensing and ops load; 5 = high)")
    ax.set_ylabel("Impact (1 = low; 5 = high revenue,\nengagement and defensibility)")
    ax.grid(False)
    h = fig.get_figheight()
    fig.subplots_adjust(top=1 - 0.10 / h)
    fig.text(0.01, 1 + 0.62 / h, "Start with Nek goal redemption and SEBI-regulated gold; gate credit behind compliance",
             fontsize=12.5, fontweight="bold", ha="left", va="bottom")
    fig.text(0.01, 1 + 0.30 / h, "Analyst-judgement scores (1-5). Priority = impact ÷ effort", fontsize=9,
             color=C.INK_SECONDARY, ha="left", va="bottom")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
    return path

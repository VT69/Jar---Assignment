"""Final verification: does the report say exactly what the data says?

Three independent checks:
1. **Recompute** headline numbers straight from the raw Excel files with a
   separate, minimal code path (no ``src.sales``/``src.regional`` functions) and
   compare them with ``report_numbers.json``.
2. **PDF text audit**: every value substituted into the template must appear in
   the extracted PDF text (proves nothing was lost or mangled in rendering).
3. **Literal scan**: list numbers typed directly in the Q1 sections (not from a
   placeholder) so they can be reviewed by hand.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src import config as C

TOL = 1e-6


def _raw_merge() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lo = pd.read_excel(C.ORDERS_FILE, dtype={"Order ID": str})
    od = pd.read_excel(C.DETAILS_FILE, dtype={"Order ID": str})
    st = pd.read_excel(C.TARGETS_FILE)
    # independent date repair: text -> dayfirst; datetime cells -> swap day/month
    def fix(v: Any) -> pd.Timestamp:
        if isinstance(v, str):
            d, m, y = map(int, v.split("-"))
            return pd.Timestamp(y, m, d)
        return pd.Timestamp(v.year, v.day, v.month)
    lo["date"] = lo["Order Date"].map(fix)
    m = od.merge(lo, on="Order ID", how="inner")
    st["month"] = [pd.Timestamp(2000 + d.day, d.month, 1) for d in pd.to_datetime(st["Month of Order Date"])]
    return lo, m, st


def recompute(numbers: dict[str, Any]) -> pd.DataFrame:
    """Recompute key figures independently and compare with the exported numbers."""
    lo, m, st = _raw_merge()
    checks: list[tuple[str, float]] = []
    for cat, g in m.groupby("Category"):
        checks += [
            (f"cat.{cat}.amount", g["Amount"].sum()),
            (f"cat.{cat}.profit", g["Profit"].sum()),
            (f"cat.{cat}.margin_pct", 100 * g["Profit"].sum() / g["Amount"].sum()),
            (f"cat.{cat}.profit_per_order", g["Profit"].sum() / g["Order ID"].nunique()),
            (f"cat.{cat}.profit_per_line", g["Profit"].mean()),
        ]
    for (cat, sub), g in m.groupby(["Category", "Sub-Category"]):
        checks.append((f"sub.{cat}.{sub}.profit", g["Profit"].sum()))
    checks += [("total.sales", m["Amount"].sum()), ("total.profit", m["Profit"].sum()),
               ("join.merged_rows", len(m))]
    orders = lo.groupby("State")["Order ID"].nunique()
    for s in orders.sort_values(ascending=False).index[:C.TOP_N_STATES]:
        g = m[m["State"] == s]
        checks += [(f"state.{s}.orders", orders[s]), (f"state.{s}.sales", g["Amount"].sum()),
                   (f"state.{s}.profit_per_order", g["Profit"].sum() / orders[s])]
    for (city, state), g in m.groupby(["City", "State"]):
        checks.append((f"city.{city}@{state}.margin_pct", 100 * g["Profit"].sum() / g["Amount"].sum()))
    f = st[st["Category"] == C.TARGET_CATEGORY].sort_values("month")
    mom = 100 * f["Target"].pct_change()
    for mo, v in zip(f["month"].iloc[1:], mom.iloc[1:]):
        checks.append((f"mom.{mo:%Y-%m}.mom_pct", v))
    fa = m[m["Category"] == C.TARGET_CATEGORY].groupby(m["date"].dt.to_period("M"))["Amount"].sum()
    checks += [("p2.target_annual", f["Target"].sum()), ("p2.actual_annual", fa.sum()),
               ("p2.attain_annual", 100 * fa.sum() / f["Target"].sum())]
    rows = []
    for key, expected in checks:
        got = numbers.get(key)
        ok = got is not None and abs(float(got) - float(expected)) <= TOL * max(1, abs(float(expected)))
        rows.append({"key": key, "independent": float(expected), "reported": got, "match": ok})
    return pd.DataFrame(rows)


def pdf_text_audit(pdf_path: Path, substitutions: list[tuple[str, str, str]]) -> pd.DataFrame:
    """Check each substituted (number-bearing) value appears in the PDF text."""
    from pypdf import PdfReader

    footer = re.compile(r"Jar Growth Intern Assignment\s*·.*?page \d+ of \d+")  # stamped page footers
    text = " ".join(footer.sub("", p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages)
    norm = re.sub(r"\s+", "", text)
    rows = []
    for key, fmt, value in substitutions:
        if fmt == "raw" and not re.search(r"\d", value):
            continue  # names / labels
        needle = re.sub(r"\s+", "", value)
        rows.append({"key": key, "format": fmt, "value": value, "in_pdf": needle in norm})
    return pd.DataFrame(rows).drop_duplicates()


LITERAL_ALLOW = re.compile(
    r"^(\d\.?|\d{1,2}|20\d\d[.,]?|100%|0%|₹10)$"  # list markers, years, Jar's ₹10 ticket
)


def literal_scan(template_path: Path) -> pd.DataFrame:
    """List digits typed directly into the Q1 parts of the template (outside placeholders)."""
    tpl = template_path.read_text(encoding="utf-8")
    start, end = tpl.index("## Executive summary"), tpl.index("## 5. Q2")
    q1 = re.sub(r"\{\{[^{}]+\}\}", "", tpl[start:end])
    q1 = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", q1)           # image links
    q1 = re.sub(r"`[^`]*`", "", q1)                        # code spans
    rows = []
    for ln_no, line in enumerate(q1.splitlines(), 1):
        if line.startswith("#") or line.startswith("Figure "):
            continue
        for tok in re.findall(r"[₹±]?\d[\d,.]*%?×?", line):
            if not LITERAL_ALLOW.match(tok):
                rows.append({"line": line.strip()[:110], "literal": tok})
    return pd.DataFrame(rows, columns=["line", "literal"])


def run(numbers_path: Path, substitutions: list[tuple[str, str, str]], pdf_path: Path | None) -> dict[str, Any]:
    """Run all checks, write CSV evidence to outputs/tables and return a summary."""
    numbers = json.loads(numbers_path.read_text(encoding="utf-8"))
    rec = recompute(numbers)
    rec.to_csv(C.TABLE_DIR / "verify_recompute.csv", index=False)
    lit = literal_scan(C.REPORT_DIR / "report_template.md")
    lit.to_csv(C.TABLE_DIR / "verify_literals.csv", index=False)
    summary: dict[str, Any] = {
        "recompute_checked": len(rec), "recompute_mismatches": int((~rec["match"]).sum()),
        "literals_to_review": lit["literal"].tolist(),
    }
    if pdf_path is not None and pdf_path.exists():
        aud = pdf_text_audit(pdf_path, substitutions)
        aud.to_csv(C.TABLE_DIR / "verify_pdf_text.csv", index=False)
        summary.update({"pdf_values_checked": len(aud), "pdf_values_missing": aud.loc[~aud["in_pdf"], "value"].tolist()})
    return summary

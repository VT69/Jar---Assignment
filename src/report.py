"""Render the report: template + numbers -> Markdown -> HTML -> PDF.

Every number in the narrative comes from ``{{key|format}}`` placeholders that are
resolved against ``outputs/report_numbers.json``. Rendering fails on any
missing key, and data-dependent statements written as prose are guarded by
explicit *claims* that must hold for the build to pass.
"""
from __future__ import annotations

import html
import os
import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import markdown
import matplotlib
import pandas as pd

from src import config as C
from src.formatting import indian_group, inr

PLACEHOLDER = re.compile(r"\{\{([^{}|]+?)(?:\|([a-z0-9_]+))?\}\}")
TEMPLATE_PATH: Path = C.REPORT_DIR / "report_template.md"

FORMATTERS: dict[str, Callable[[Any], str]] = {
    "raw": lambda v: str(v),
    "int": lambda v: indian_group(int(round(v))),
    "inr": lambda v: inr(v),
    "inr2": lambda v: inr(v, 2),
    "pct0": lambda v: f"{v:.0f}%",
    "pct1": lambda v: f"{v:.1f}%",
    "pct2": lambda v: f"{v:.2f}%",
    "spct1": lambda v: f"{v:+.1f}%",
    "spct2": lambda v: f"{v:+.2f}%",
    "f0": lambda v: f"{v:.0f}",
    "f1": lambda v: f"{v:.1f}",
    "f2": lambda v: f"{v:.2f}",
    "x1": lambda v: f"{v:.1f}×",
    "x2": lambda v: f"{v:.2f}×",
    "mn": lambda v: f"{v / 1e6:g} million",
    "lakh": lambda v: f"{round(v / 1e5, 1):g} lakh",
    "cr0": lambda v: f"₹{indian_group(int(round(v / 1e7)))} crore",
    "cr1": lambda v: f"₹{v / 1e7:.1f} crore",
    "cr2": lambda v: f"₹{v / 1e7:.2f} crore",
}


@dataclass
class Rendered:
    """Rendered Markdown plus an audit trail of every substituted value."""

    markdown: str
    substitutions: list[tuple[str, str, str]] = field(default_factory=list)  # (key, fmt, text)


# --------------------------------------------------------------------------- #
# Claims: prose statements in the template that depend on the data
# --------------------------------------------------------------------------- #
def check_claims(n: dict[str, Any], t: dict[str, Any]) -> list[tuple[str, bool]]:
    """Evaluate every data-dependent prose claim; the build fails if any is False."""
    cat, states, cities, mom, opps = t["cat"], t["states"], t["cities"], t["mom"], t["opps"]
    stcat = t["state_cat"]

    def worst_category(state: str) -> str:
        s = stcat[stcat["State"] == state]
        return s.loc[s["profit"].idxmin(), "Category"]

    flagged = mom.loc[mom["flag_relative"], "Month"].dt.strftime("%Y-%m").tolist()
    biggest_cities = cities.sort_values("sales", ascending=False)["City"].head(2).tolist()
    top_loss = cities[cities["State"].isin(t["top"].index) & (cities["profit"] < 0)]
    claims = [
        ("Top-5 table row order is MP, MH, RJ, GJ, PB",
         [n[f"top.{i}"] for i in range(1, 6)] == ["Madhya Pradesh", "Maharashtra", "Rajasthan", "Gujarat", "Punjab"]),
        ("No tie at the top-5 cut-off", not n["p3.top_tied"]),
        ("Electronics #1 on sales and profit/order", cat.loc["Electronics", ["rank_amount", "rank_profit_per_order"]].eq(1).all()),
        ("Clothing #1 on total profit and margin", cat.loc["Clothing", ["rank_profit", "rank_margin_pct"]].eq(1).all()),
        ("Furniture last on all four metrics",
         cat.loc["Furniture", ["rank_amount", "rank_profit", "rank_profit_per_order", "rank_margin_pct"]].eq(3).all()),
        ("Per-order and per-line rank categories identically", n["p1.ranks_agree"]),
        ("Exactly two loss-making sub-categories: Tables and Electronic Games",
         n["p1.n_loss_subcats"] == 2 and set(n["p1.loss_subcats"].split(" and ")) == {"Tables", "Electronic Games"}),
        ("Furniture ex-Tables margin is within 0.5 pp of Electronics",
         abs(n["p1.furn_ex_tables_margin"] - cat.loc["Electronics", "margin_pct"]) < 0.5),
        ("Median quantity identical on loss and profitable lines", n["p1.qty_median_loss"] == n["p1.qty_median_profit"]),
        ("Price exception is a single sub-category (Trousers)", n["p1.price_exception"] == "Trousers"),
        ("Clothing appears in the most orders", cat["orders"].idxmax() == "Clothing"),
        ("z-rule flags exactly Jul and Nov 2018", flagged == ["2018-07", "2018-11"]),
        ("Mar 2019 is the near miss", n["p2.near_miss_month"] == "Mar 2019"),
        ("Leading miss run is Apr-Oct 2018", n["p2.lead_miss_months"] == 7 and n["p2.lead_miss_end"] == "Oct 2018"),
        ("Electronics over-attained, Clothing under-attained",
         n["att.Electronics.annual_attainment_pct"] > 100 > n["att.Clothing.annual_attainment_pct"]),
        ("MP sales share exceeds its profit share",
         states.loc["Madhya Pradesh", "sales_share_pct"] > states.loc["Madhya Pradesh", "profit_share_pct"]),
        ("Loss states' driver categories: TN/AP Furniture, PB/BR Electronics",
         [worst_category(s) for s in ("Tamil Nadu", "Andhra Pradesh", "Punjab", "Bihar")]
         == ["Furniture", "Furniture", "Electronics", "Electronics"]),
        ("Over-earning states are UP, Delhi, WB, Kerala",
         n["p3.overearners"] == "Uttar Pradesh, Delhi, West Bengal and Kerala"),
        ("Mumbai and Indore are the two largest cities", sorted(biggest_cities) == ["Indore", "Mumbai"]),
        ("Loss cities in top-5 states are Ahmedabad, Chandigarh (PB), Jaipur",
         sorted(top_loss["City"]) == ["Ahmedabad", "Chandigarh", "Jaipur"]
         and set(top_loss["State"]) == {"Gujarat", "Punjab", "Rajasthan"}),
        ("Sister cities earn double-digit margins",
         min(n["city.Surat@Gujarat.margin_pct"], n["city.Amritsar@Punjab.margin_pct"],
             n["city.Udaipur@Rajasthan.margin_pct"]) >= 10),
        ("Allahabad is UP's high-margin city",
         n["city.Allahabad@Uttar Pradesh.margin_pct"] > n["city.Lucknow@Uttar Pradesh.margin_pct"]),
        ("Q3 table order is B, A, C, D, E", opps["code"].tolist() == ["B", "A", "C", "D", "E"]),
        ("Indore within 1pp of company margin", abs(n["city.Indore@Madhya Pradesh.margin_pct"] - n["total.margin"]) < 1),
        ("Electronics has the higher unit price; Furniture within 10% of it ('similar')",
         1 > cat.loc["Furniture", "unit_price"] / cat.loc["Electronics", "unit_price"] > 0.9),
        ("Furniture keeps less profit per unit than Electronics",
         cat.loc["Furniture", "profit_per_unit"] < cat.loc["Electronics", "profit_per_unit"]),
        ("Leakage-free (ex-Furniture) re-phasing still beats the flat target",
         n["p2.mape_rephased_exfurn"] < n["p2.mape_current"]),
        ("Chennai is Tamil Nadu's only city and loss is Furniture-driven",
         n["city.Chennai@Tamil Nadu.orders"] == n["state.Tamil Nadu.orders"]),
        ("Opportunity B GMV exceeds Nek's reported revenue (text says 'about Nx')", n["q3.B.gmv_vs_nek"] > 1),
        ("A's quantified value is under 5% of core revenue, consistent with impact below 5.0",
         n["q3.A.share_of_core_pct"] < 5 and n["opp.A.impact"] < 5),
        ("A is no longer the top-impact opportunity (text: 'not the largest on the list')",
         n["opp.A.impact"] < max(n[f"opp.{c}.impact"] for c in "BCDE")),
    ]
    return [(desc, bool(ok)) for desc, ok in claims]


# --------------------------------------------------------------------------- #
# Appendix tables
# --------------------------------------------------------------------------- #
def _md_table(df: pd.DataFrame, align: list[str]) -> str:
    head = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---:" if a == "r" else "---" for a in align) + "|"
    rows = ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def appendix_tables(t: dict[str, Any]) -> dict[str, str]:
    """Build the Markdown detail tables for Appendix B."""
    sub = t["sub"].copy()
    sub = pd.DataFrame({
        "Category": sub["Category"], "Sub-category": sub["Sub-Category"],
        "Sales": sub["amount"].map(inr), "Profit": sub["profit"].map(inr),
        "Margin": sub["margin_pct"].map(lambda v: f"{v:.1f}%"), "Lines": sub["lines"],
        "Orders": sub["orders"], "Loss lines": sub["loss_line_share_pct"].map(lambda v: f"{v:.1f}%"),
        "Profit / line": sub["profit_per_line"].map(lambda v: inr(v, 2)),
    })
    rp = t["rephased"]
    mom = t["mom"]
    mt = pd.DataFrame({
        "Month": mom["Month"].dt.strftime("%b %Y"), "Target": mom["Target"].map(inr),
        "Change (₹)": mom["mom_abs"].map(lambda v: "–" if pd.isna(v) else f"+{inr(v)}"),
        "MoM %": mom["mom_pct"].map(lambda v: "–" if pd.isna(v) else f"{v:+.2f}%"),
        "z-score": mom["mom_z"].map(lambda v: "–" if pd.isna(v) else f"{v:+.2f}"),
        "Flag (z-rule)": mom["flag_relative"].map(lambda f: "**Flagged**" if f else ""),
    })
    fm = pd.DataFrame({
        "Month": rp["Month"].dt.strftime("%b %Y"), "Target": rp["Target"].map(inr),
        "Actual": rp["Actual"].map(inr), "Gap": rp["gap"].map(inr),
        "Attainment": rp["attainment_pct"].map(lambda v: f"{v:.1f}%"),
        "Furniture profit": rp["Profit"].map(inr), "Re-phased target": rp["Rephased"].map(inr),
    })
    st = t["states"].reset_index()
    stt = pd.DataFrame({
        "Rank": st["order_rank"], "State": st["State"], "Orders": st["orders"], "Sales": st["sales"].map(inr),
        "Profit": st["profit"].map(inr), "Margin": st["margin_pct"].map(lambda v: f"{v:.1f}%"),
        "Profit / order": st["profit_per_order"].map(lambda v: inr(v, 2)),
        "Sales share": st["sales_share_pct"].map(lambda v: f"{v:.1f}%"),
        "Profit share": st["profit_share_pct"].map(lambda v: f"{v:.1f}%"),
    })
    focus = set(t["top"].index) | set(t["states"].index[t["states"]["profit"] < 0])
    ct = t["cities"][t["cities"]["State"].isin(focus)].sort_values(["State", "sales"], ascending=[True, False])
    ctt = pd.DataFrame({
        "State": ct["State"], "City": ct["City"], "Orders": ct["orders"], "Sales": ct["sales"].map(inr),
        "Profit": ct["profit"].map(inr), "Margin": ct["margin_pct"].map(lambda v: f"{v:.1f}%"),
        "Share of state sales": ct["share_of_state_sales_pct"].map(lambda v: f"{v:.1f}%"),
        "Loss lines": ct["loss_line_share_pct"].map(lambda v: f"{v:.1f}%"),
    })
    return {
        "subcategory": _md_table(sub, ["l", "l"] + ["r"] * 7),
        "mom": _md_table(mt, ["l", "r", "r", "r", "r", "l"]),
        "furniture_months": _md_table(fm, ["l"] + ["r"] * 6),
        "states": _md_table(stt, ["r", "l"] + ["r"] * 7),
        "cities": _md_table(ctt, ["l", "l"] + ["r"] * 6),
    }


# --------------------------------------------------------------------------- #
# Template rendering
# --------------------------------------------------------------------------- #
def meta_numbers(author: str, date: str, github: str) -> dict[str, Any]:
    """Non-data values shown in the report (author, date, repository, environment)."""
    return {
        "meta.author": author,
        "meta.github": github,
        "meta.date": date,
        "meta.top_n_loss": str(C.TOP_N_LOSS_LINES),
        "meta.python": platform.python_version(),
        "meta.pandas": pd.__version__,
        "meta.matplotlib": matplotlib.__version__,
    }


def render_template(template: str, numbers: dict[str, Any], tables: dict[str, str]) -> Rendered:
    """Substitute placeholders; raise listing every missing key or unknown format."""
    subs: list[tuple[str, str, str]] = []
    errors: list[str] = []

    def sub(m: re.Match[str]) -> str:
        key, fmt = m.group(1).strip(), m.group(2) or "raw"
        if key.startswith("table:"):
            name = key.split(":", 1)[1]
            if name not in tables:
                errors.append(f"unknown table {name}")
                return m.group(0)
            return tables[name]
        if key not in numbers:
            errors.append(f"missing key {key}")
            return m.group(0)
        if fmt not in FORMATTERS:
            errors.append(f"unknown format {fmt} for {key}")
            return m.group(0)
        value = numbers[key]
        if value is None or (isinstance(value, float) and pd.isna(value)):
            errors.append(f"null value for {key}")
            return m.group(0)
        text = FORMATTERS[fmt](value)
        subs.append((key, fmt, text))
        return text

    out = PLACEHOLDER.sub(sub, template)
    if errors:
        raise KeyError("Template rendering failed:\n  " + "\n  ".join(sorted(set(errors))))
    assert "{{" not in out and "}}" not in out, "Unresolved placeholder syntax remains"
    return Rendered(out, subs)


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
CSS = """
@page { size: A4; margin: 18mm 17mm 20mm 17mm; }
:root { --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --rule:#e1e0d9; --accent:#2a78d6; --critical:#d03b3b;
        --wash:#f4f7fc; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Segoe UI", "Nirmala UI", system-ui, "Noto Sans", "DejaVu Sans", sans-serif; color: var(--ink);
       font-size: 10pt; line-height: 1.45; background: #fff; margin: 0; }
h2 { font-size: 17pt; margin: 0 0 10px; padding-bottom: 6px; border-bottom: 2px solid var(--accent);
     break-before: page; break-after: avoid; }
h2.cont { break-before: auto; margin-top: 22px; }
h3 { font-size: 12.2pt; margin: 18px 0 6px; color: var(--ink); break-after: avoid; }
p { margin: 6px 0 8px; orphans: 3; widows: 3; }
strong { font-weight: 650; }
ul, ol { margin: 4px 0 10px; padding-left: 22px; } li { margin: 2px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 14px; font-size: 8.7pt; font-variant-numeric: tabular-nums;
        break-inside: auto; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { text-align: left; color: var(--ink2); font-weight: 600; border-bottom: 1.2px solid var(--ink2); padding: 5px 6px;
     vertical-align: bottom; }
td { border-bottom: 0.6px solid var(--rule); padding: 4.5px 6px; vertical-align: top; }
img { max-width: 100%; max-height: 106mm; width: auto; height: auto; display: block; margin: 10px auto 2px; }
p:has(+ p > img), h3:has(+ p > img) { break-after: avoid; }
p:has(> strong:only-child) { break-after: avoid; }  /* keep bold lead-ins (card titles) with their content */
p:has(> img) { break-inside: avoid; break-after: avoid; margin: 0; }
p.small { font-size: 8.2pt; color: var(--ink2); line-height: 1.45; }
p.caption { font-size: 8.6pt; color: var(--muted); margin: 2px 0 14px; }
blockquote { margin: 10px 0; padding: 8px 12px; background: var(--wash); border-left: 3px solid var(--accent);
             color: var(--ink2); break-inside: avoid; }
blockquote p { margin: 2px 0; }
code { font-family: Consolas, "DejaVu Sans Mono", monospace; font-size: 8.8pt; background: #f2f1ee; padding: 0 3px;
       border-radius: 3px; }
.shot { border: 1.2px dashed var(--muted); color: var(--muted); padding: 18px 12px; text-align: center; font-size: 8.8pt;
        margin: 6px 0 14px; border-radius: 6px; break-inside: avoid; }
.title-page { height: 255mm; display: flex; flex-direction: column; justify-content: space-between; }
.title-page .kicker { color: var(--accent); font-weight: 650; letter-spacing: .08em; text-transform: uppercase;
                      font-size: 9.5pt; margin-top: 55mm; }
.title-page h1 { font-size: 30pt; line-height: 1.15; margin: 8px 0 10px; }
.title-page .sub { font-size: 13pt; color: var(--ink2); }
.title-page .meta { color: var(--ink2); font-size: 10pt; border-top: 1px solid var(--rule); padding-top: 10px; }
.toc { break-before: page; }
.toc h2.toc-title { break-before: auto; }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li { display: flex; align-items: baseline; margin: 5px 0; }
.toc li.l3 { padding-left: 18px; font-size: 9.4pt; color: var(--ink2); margin: 2px 0; }
.toc li .dots { flex: 1; border-bottom: 1px dotted var(--muted); margin: 0 6px; transform: translateY(-3px); }
.toc a { color: inherit; text-decoration: none; }
"""


@dataclass
class HtmlDoc:
    """Built HTML plus the headings used for the contents page."""

    html: str
    headings: list[tuple[int, str, str]]  # (level, text, id)


def build_html(md_text: str, page_numbers: dict[str, int] | None = None) -> HtmlDoc:
    """Convert rendered Markdown to a styled, print-ready HTML document."""
    lines = md_text.splitlines()
    first_h2 = next(i for i, ln in enumerate(lines) if ln.startswith("## "))
    front = [ln for ln in lines[:first_h2] if ln.strip()]
    title = front[0].lstrip("# ").strip()
    subtitle = front[1] if len(front) > 1 else ""
    byline = front[2] if len(front) > 2 else ""
    code_line = front[3] if len(front) > 3 else ""
    body_md = "\n".join(lines[first_h2:])

    md = markdown.Markdown(extensions=["tables", "attr_list", "md_in_html", "toc"],
                           extension_configs={"toc": {"toc_depth": "2-3"}})
    body_html = md.convert(body_md)
    headings: list[tuple[int, str, str]] = []

    def walk(tokens: list[dict[str, Any]]) -> None:
        for tok in tokens:
            headings.append((tok["level"], html.unescape(tok["name"]), tok["id"]))
            walk(tok["children"])

    walk(md.toc_tokens)
    toc_items = []
    for level, text, hid in headings:
        page = (page_numbers or {}).get(hid, "")
        toc_items.append(f'<li class="l{level}"><a href="#{hid}">{html.escape(text)}</a>'
                         f'<span class="dots"></span><span>{page}</span></li>')
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<section class="title-page">
  <div><div class="kicker">Growth Intern assignment</div><h1>{html.escape(title)}</h1>
  <div class="sub">{html.escape(subtitle)}</div></div>
  <div class="meta">{html.escape(byline)}<br>{html.escape(code_line)}<br>Analysis in Python · all figures and numbers regenerated by <code>python main.py</code></div>
</section>
<nav class="toc"><h2 class="toc-title">Contents</h2><ol>{''.join(toc_items)}</ol></nav>
{body_html}
</body></html>"""
    return HtmlDoc(doc, headings)


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def find_browser() -> str | None:
    """Locate a Chromium-based browser for headless printing (env override: CHROME_PATH)."""
    candidates = [os.environ.get("CHROME_PATH", "")]
    if platform.system() == "Windows":
        for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""),
                     os.environ.get("LOCALAPPDATA", "")):
            candidates += [str(Path(base) / "Google/Chrome/Application/chrome.exe"),
                           str(Path(base) / "Microsoft/Edge/Application/msedge.exe")]
    elif platform.system() == "Darwin":
        candidates += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                       "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    candidates += [shutil.which(n) or "" for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge")]
    return next((c for c in candidates if c and Path(c).is_file()), None)


def html_to_pdf(html_path: Path, pdf_path: Path, browser: str) -> None:
    """Print an HTML file to PDF with headless Chromium."""
    with tempfile.TemporaryDirectory() as profile:
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
               f"--user-data-dir={profile}", "--virtual-time-budget=10000",
               f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
    assert pdf_path.exists() and pdf_path.stat().st_size > 10_000, "PDF was not produced"


def _norm(s: str) -> str:
    return re.sub(r"[\s ]+", "", s).replace("–", "-").replace("—", "-").lower()


def locate_headings(pdf_path: Path, headings: list[tuple[int, str, str]]) -> dict[str, int]:
    """Find the 1-based page on which each heading first appears (after the contents)."""
    from pypdf import PdfReader

    pages = [_norm(p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages]
    start = 2  # skip title (0) and contents (1+) - headings are searched from page index 2
    found: dict[str, int] = {}
    cursor = start
    for _, text, hid in headings:
        key = _norm(text)
        for i in range(cursor, len(pages)):
            if key in pages[i]:
                found[hid] = i + 1
                cursor = i
                break
    return found


def stamp_footer(pdf_path: Path, label: str) -> int:
    """Add 'label · page N of M' to every page except the title page. Returns page count."""
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    with tempfile.TemporaryDirectory() as tmp:
        overlay_path = Path(tmp) / "overlay.pdf"
        with PdfPages(overlay_path, metadata={"Creator": None, "Producer": None, "CreationDate": None}) as pp:
            for i, page in enumerate(reader.pages):
                w, h = float(page.mediabox.width) / 72, float(page.mediabox.height) / 72
                fig = plt.figure(figsize=(w, h))
                if i > 0:
                    fig.text(0.5, 9 / 25.4 / h, f"{label}  ·  page {i + 1} of {total}", ha="center", va="bottom",
                             fontsize=7.5, color=C.INK_MUTED, family="DejaVu Sans")
                pp.savefig(fig, transparent=True)
                plt.close(fig)
        overlay = PdfReader(str(overlay_path))
        writer = PdfWriter()
        for page, ov in zip(reader.pages, overlay.pages):
            page.merge_page(ov)
            writer.add_page(page)
        writer.add_metadata({"/Title": "Jar — Growth Intern Assignment", "/Author": label})
        with open(pdf_path, "wb") as fh:
            writer.write(fh)
    return total


def build(numbers: dict[str, Any], tables: dict[str, Any], author: str, date: str, make_pdf: bool = True,
          github: str = C.GITHUB_URL) -> dict[str, Any]:
    """Render Markdown/HTML/PDF and return paths plus the substitution audit trail."""
    claims = check_claims(numbers, tables)
    failed = [d for d, ok in claims if not ok]
    if failed:
        raise AssertionError("Report claims no longer hold:\n  " + "\n  ".join(failed))
    all_numbers = {**numbers, **meta_numbers(author, date, github)}
    rendered = render_template(TEMPLATE_PATH.read_text(encoding="utf-8"), all_numbers, appendix_tables(tables))
    C.REPORT_MD.write_text(rendered.markdown, encoding="utf-8")

    doc = build_html(rendered.markdown)
    C.REPORT_HTML.write_text(doc.html, encoding="utf-8")
    result: dict[str, Any] = {"md": C.REPORT_MD, "html": C.REPORT_HTML, "pdf": None, "claims": claims,
                              "substitutions": rendered.substitutions, "pages": None, "body_pages": None}
    if not make_pdf:
        return result
    browser = find_browser()
    if browser is None:
        print("WARNING: no Chromium-based browser found (set CHROME_PATH); skipping PDF.")
        return result
    # Pass 1: locate headings; pass 2: re-render the contents with page numbers.
    html_to_pdf(C.REPORT_HTML, C.REPORT_PDF, browser)
    pages = locate_headings(C.REPORT_PDF, doc.headings)
    missing = [t for _, t, hid in doc.headings if hid not in pages]
    assert not missing, f"Headings not found in PDF: {missing}"
    doc2 = build_html(rendered.markdown, pages)
    C.REPORT_HTML.write_text(doc2.html, encoding="utf-8")
    html_to_pdf(C.REPORT_HTML, C.REPORT_PDF, browser)
    assert locate_headings(C.REPORT_PDF, doc2.headings) == pages, "Page numbers shifted between passes"
    result["pages"] = stamp_footer(C.REPORT_PDF, f"Jar Growth Intern Assignment  ·  {author}")
    result["pdf"] = C.REPORT_PDF
    result["heading_pages"] = pages
    ids = [hid for _, _, hid in doc.headings]
    first = pages[ids[0]]
    appendix = next(pages[h] for h in ids if h.startswith("appendix"))
    result["body_pages"] = appendix - first
    return result

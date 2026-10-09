# Jar — Growth Intern Assignment

Python analysis and report for the Jar Growth Intern take-home: sales analysis (Q1), an app review from a hands-on session (Q2) and product opportunities (Q3).

**Submission:** [`Jar_Growth_Intern_Assignment.pdf`](Jar_Growth_Intern_Assignment.pdf). The Markdown source is at [`report/Jar_Growth_Intern_Assignment.md`](report/Jar_Growth_Intern_Assignment.md).

## Run

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux
python main.py --author "Your Name"
```

`python main.py` regenerates everything, deterministically, from the raw files in `data/`:

| Output | Location |
|---|---|
| Intermediate tables (CSV) | `outputs/tables/` |
| Figures (PNG, 200 dpi) | `outputs/figures/` |
| Every number quoted in the report | `outputs/report_numbers.json` |
| Report Markdown + HTML | `report/` |
| Report PDF | `Jar_Growth_Intern_Assignment.pdf` |
| Verification evidence | `outputs/tables/verify_*.csv` |

Options: `--no-pdf` builds Markdown and HTML only. `--date "9 October 2026"` fixes the title-page date. `--github <url>` sets the repository link on the title page.

**Notebook:** [`Q1_Sales_Analysis.ipynb`](Q1_Sales_Analysis.ipynb) walks through Q1 step by step using the same `src/` functions. It asserts that its tables are identical to the pipeline's output. To re-run it, install `requirements-dev.txt` (Jupyter kernel tooling) and open it from the project root.

**PDF rendering** uses a locally installed Chromium browser (Chrome or Edge) in headless mode. Set `CHROME_PATH` if it isn't found automatically. If no browser is available, the run still produces Markdown and HTML.

## Environment

Python 3.12 · pandas 3.0 · matplotlib 3.11 · openpyxl · Markdown · pypdf (pinned in `requirements.txt`).

## Layout

```
data/                 raw inputs (read-only)
src/config.py         paths, thresholds, palette - every tunable number
src/data.py           loading, date repair, validated merge (JoinReport)
src/sales.py          Q1 Part 1: category / sub-category / loss / price-realisation metrics
src/targets.py        Q1 Part 2: MoM %, fluctuation flags, target vs actual, re-phasing
src/regional.py       Q1 Part 3: state and city metrics
src/opportunities.py  Q3 scoring + effort-vs-impact matrix
src/insights.py       derives every report number -> report_numbers.json
src/plotting.py       all figures (one consistent style and palette)
src/report.py         template -> Markdown -> HTML -> PDF (two-pass contents page numbers)
src/verify.py         independent recompute + PDF text audit + literal scan
report/report_template.md   narrative with {{key|format}} placeholders
main.py               single entry point
```

## How the report stays correct

1. **No hand-typed numbers.** The narrative in `report/report_template.md` uses `{{key|format}}` placeholders resolved from `report_numbers.json`. A missing key fails the build.
2. **Claims are tested.** Data-dependent prose ("Tables and Electronic Games are the only loss-making sub-categories", "Jul and Nov are the flagged months", ...) is encoded as assertions in `report.check_claims`. If the data changes, the build fails rather than publishing a stale sentence.
3. **Independent recompute.** `verify.py` re-derives about 90 headline figures straight from the Excel files through a separate code path and compares them with the JSON.
4. **PDF text audit.** Every substituted value must appear in the text extracted from the final PDF.
5. **Literal scan.** Lists any digits typed directly into the Q1 narrative, for manual review.
6. **Assertions after each transform.** Covers row counts, unique keys, no NaN, margins within ±100%, and sales and profit reconciling to totals.

## Key decisions and assumptions

- **Merge.** Order Details is left-joined to List of Orders (`validate="many_to_one"`), with a hard assertion of zero unmatched IDs on both sides: 1,500 lines in, 1,500 out.
- **Average profit.** Per order is primary: group profit ÷ distinct orders containing the group. Per line item is reported alongside.
- **Order Date repair.** 193 cells Excel auto-converted month-first have day and month swapped back. 307 text cells are parsed as `dd-mm-yyyy`. The repaired dates are monotonic in Order ID (asserted).
- **Target month repair.** "Apr-18" had been stored as 18 April of the current year, so year = 2000 + day.
- **Fluctuation rule.** A month is flagged if |z| of its MoM % exceeds 1.5 standard deviations, with a ≥5% materiality cross-check. Both thresholds are in `config.py`.
- **Price realisation.** There is no discount column, so realised unit price on loss lines is compared with profitable lines within each sub-category. Lower realised prices fit discounting (a hypothesis) or a cheaper product mix; the data can't separate the two.
- **Re-phased target.** Uses same-year company-wide seasonality. That includes Furniture, so leakage is partial; an ex-Furniture sensitivity is reported alongside.
- **Small sample.** 500 orders over one year. Single-city and single-month findings are directional.
- **Data quirks kept as recorded.** 3 orders show city "Delhi" under state Madhya Pradesh. Chandigarh appears under both Punjab and Haryana.
- **Q2** is written from a hands-on session (Vivo T2x 5G on Jio 5G). Jar blocks screenshots, so observations are described rather than shown.
- **Q3** impact and effort scores, and the sizing inputs (a 20% active share of registered users, a 10% jewellery gross margin), are analyst judgement and are labelled as such.

The full assumptions log is in Appendix A of the report.

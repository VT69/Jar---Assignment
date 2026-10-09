"""Single entry point: ``python main.py`` regenerates every output and the report.

Steps: load + repair + merge data -> compute tables -> export CSVs and figures
-> render Markdown/HTML/PDF report -> verify the report against the numbers.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from src import config as C
from src import pipeline, report, verify


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--author", default=C.AUTHOR, help="Name shown on the title page and footer")
    p.add_argument("--github", default=C.GITHUB_URL, help="Repository link shown on the title page")
    p.add_argument("--date", default=None, help="Report date (default: today, e.g. '9 October 2026')")
    p.add_argument("--no-pdf", action="store_true", help="Skip PDF rendering (Markdown + HTML only)")
    return p.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ₹ on Windows consoles
    args = parse_args()
    report_date = args.date or date.today().strftime("%-d %B %Y" if sys.platform != "win32" else "%#d %B %Y")
    print("1/4  Computing analysis ...")
    run = pipeline.run()
    print(f"     {len(run['table_files'])} tables -> {C.TABLE_DIR.relative_to(C.PROJECT_ROOT)}")
    print(f"     {len(run['figures'])} figures -> {C.FIGURE_DIR.relative_to(C.PROJECT_ROOT)}")
    print("2/4  Rendering report ...")
    built = report.build(run["numbers"], run["tables"], args.author, report_date, make_pdf=not args.no_pdf,
                         github=args.github)
    print(f"     claims checked: {len(built['claims'])} (all hold)")
    print(f"     numbers substituted: {len(built['substitutions'])}")
    if built["pdf"]:
        print(f"     PDF: {built['pdf'].name} ({built['pages']} pages; body = {built['body_pages']} pages, "
              f"Executive summary to Section 6)")
    print("3/4  Verifying ...")
    summary = verify.run(C.NUMBERS_JSON, built["substitutions"], built["pdf"])
    print(f"     independent recompute: {summary['recompute_checked']} checks, "
          f"{summary['recompute_mismatches']} mismatches")
    if "pdf_values_checked" in summary:
        print(f"     PDF text audit: {summary['pdf_values_checked']} values, "
              f"{len(summary['pdf_values_missing'])} missing {summary['pdf_values_missing'][:10]}")
    print(f"     hand-typed literals in Q1 text to review: {summary['literals_to_review']}")
    ok = summary["recompute_mismatches"] == 0 and not summary.get("pdf_values_missing")
    print("4/4  " + ("All checks passed." if ok else "VERIFICATION FAILED - see outputs/tables/verify_*.csv"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

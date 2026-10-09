"""Central configuration: paths, analysis parameters and the chart palette.

Every tunable number used by the analysis lives here so that no magic numbers
are buried in the computation modules.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths (all relative to the project root - no absolute paths)
# --------------------------------------------------------------------------- #
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = PROJECT_ROOT / "data"
OUTPUT_DIR: Path = PROJECT_ROOT / "outputs"
FIGURE_DIR: Path = OUTPUT_DIR / "figures"
TABLE_DIR: Path = OUTPUT_DIR / "tables"
REPORT_DIR: Path = PROJECT_ROOT / "report"

ORDERS_FILE: Path = DATA_DIR / "List of Orders.xlsx"
DETAILS_FILE: Path = DATA_DIR / "Order Details.xlsx"
TARGETS_FILE: Path = DATA_DIR / "Sales target.xlsx"

REPORT_MD: Path = REPORT_DIR / "Jar_Growth_Intern_Assignment.md"
REPORT_HTML: Path = REPORT_DIR / "Jar_Growth_Intern_Assignment.html"
REPORT_PDF: Path = PROJECT_ROOT / "Jar_Growth_Intern_Assignment.pdf"
NUMBERS_JSON: Path = OUTPUT_DIR / "report_numbers.json"

# --------------------------------------------------------------------------- #
# Data-repair parameters
# --------------------------------------------------------------------------- #
ORDER_DATE_TEXT_FORMAT: str = "%d-%m-%Y"   # format of the text-typed Order Date cells
TARGET_YEAR_CENTURY: int = 2000            # "Apr-18" was stored as 18-Apr; day + 2000 = year
EXPECTED_ORDER_PERIOD: tuple[str, str] = ("2018-04-01", "2019-03-31")  # FY 2018-19

# --------------------------------------------------------------------------- #
# Analysis parameters
# --------------------------------------------------------------------------- #
TARGET_CATEGORY: str = "Furniture"
FLUCTUATION_Z: float = 1.5                 # flag |z| of MoM % above this many SDs
MATERIAL_MOM_PCT: float = 5.0              # business materiality threshold for MoM swings
TOP_N_STATES: int = 5
TOP_N_LOSS_LINES: int = 10                 # used for loss-concentration metric
TARGET_BAND_PCT: float = 15.0              # +/- band used to judge 'close to target'
OVEREARNER_GAP_PP: float = 4.0             # profit share exceeds sales share by > this (pp)
MARGIN_PLAUSIBLE_RANGE: tuple[float, float] = (-100.0, 100.0)  # % sanity bounds

# --------------------------------------------------------------------------- #
# Figure style (validated reference palette; slots 1-3 pass all-pairs CVD checks)
# --------------------------------------------------------------------------- #
FIG_DPI: int = 200
CATEGORY_COLORS: dict[str, str] = {
    "Clothing": "#2a78d6",     # slot 1 blue
    "Electronics": "#eb6834",  # slot 2 orange
    "Furniture": "#1baf7a",    # slot 3 aqua
}
ACCENT: str = "#2a78d6"        # single-series colour
CRITICAL: str = "#d03b3b"      # status: loss / flagged (never a series colour)
GOOD: str = "#0ca30c"          # status: on/above target
NEUTRAL: str = "#b5b3ab"       # de-emphasised marks
INK_PRIMARY: str = "#0b0b0b"
INK_SECONDARY: str = "#52514e"
INK_MUTED: str = "#898781"
GRID: str = "#e1e0d9"
BASELINE: str = "#c3c2b7"
SURFACE: str = "#fcfcfb"

# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
AUTHOR: str = "Vaibhav Tiwari"             # override with: python main.py --author "Your Name"
GITHUB_URL: str = "https://github.com/VT69/Jar---Assignment"  # override with: python main.py --github https://github.com/...

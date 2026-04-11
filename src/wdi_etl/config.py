"""
================================================================================
Configuration Module — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy (Senior Data Engineer)
Version     : 1.0.0
Created     : 2026-04-11

Description :
    Single source of truth for all pipeline parameters. This module eliminates
    hard-coded values across the codebase, following the
    "configuration-as-code" principle. All tunable behaviour — from API
    endpoints to missing-value strategies — is controlled here.

    Adopting a new indicator or changing the year range requires only a
    modification to this file; no changes are needed in extract, transform,
    or load modules.

Design Principles
-----------------
    1. Centralised configuration  — one file to audit, lock, or parameterise
    2. Type-annotated values      — catch config errors before runtime
    3. Sensible defaults          — pipeline runs without any env vars set
    4. Documented constants       — every value carries a rationale comment

Usage
-----
    from wdi_etl.config import INDICATORS, YEAR_START, YEAR_END

Environment Overrides
---------------------
    For production deployments, replace any constant with an environment
    variable lookup, e.g.:
        import os
        YEAR_START = int(os.getenv("WDI_YEAR_START", 2014))
================================================================================
"""

from pathlib import Path
from typing import Literal

# ── Project Directory Structure ─────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.parent
"""
Root directory of the project. Resolved relative to this file's location.
"""

DATA_DIR: Path = PROJECT_ROOT / "data"
OUTPUT_DIR: Path = DATA_DIR / "output"
RAW_DIR: Path = DATA_DIR / "raw"
INTERIM_DIR: Path = DATA_DIR / "interim"

# ── World Bank API Connection ───────────────────────────────────────────────────
WB_API_BASE: str = "https://api.worldbank.org/v2"
WB_FORMAT: str = "json"
WB_PER_PAGE: int = 10_000

# ── Indicator Definitions ──────────────────────────────────────────────────────
# To add a new indicator, append a new {code: description} pair here only.
# Schema key: NY=National Accounts, IT=Infrastructure, SP=Social,
#              SL=Social/Labour, SE=Education, etc.
INDICATORS: dict[str, str] = {
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "IT.NET.USER.ZS": "Internet users (% of population)",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total)",
    "SL.TLF.CACT.FE.ZS": "Labor force participation rate, female (% of female population ages 15+)",
    "NY.GNP.PCAP.CD": "GNI per capita, Atlas method (current US$)",
}

# ── Temporal Scope ─────────────────────────────────────────────────────────────
YEAR_START: int = 2014
YEAR_END: int = 2023

# ── Missing-Value Handling ─────────────────────────────────────────────────────
# Options: "drop", "forward_fill", "backward_fill", "interpolate", "keep"
MISSING_STRATEGY: Literal[
    "drop", "forward_fill", "backward_fill", "interpolate", "keep"
] = "keep"

# ── Country Name Standardisation ───────────────────────────────────────────────
COUNTRY_NAME_CORRECTIONS: dict[str, str] = {
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Korea, Rep.": "Korea, Republic of",
    "Iran, Islamic Rep.": "Iran, Islamic Republic of",
    "Russian Federation": "Russia",
    "Egypt, Arab Rep.": "Egypt",
    "Venezuela, RB": "Venezuela",
    "Lao PDR": "Laos",
    "Yemen, Rep.": "Yemen",
    "Congo, Rep.": "Congo",
    "Congo, Dem. Rep.": "Democratic Republic of the Congo",
    "Kyrgyz Republic": "Kyrgyzstan",
    "Slovak Republic": "Slovakia",
    "Micronesia, Fed. Sts.": "Micronesia",
    "St. Kitts and Nevis": "Saint Kitts and Nevis",
    "St. Lucia": "Saint Lucia",
    "St. Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "Gambia, The": "Gambia",
}

# ── Validation Thresholds ───────────────────────────────────────────────────────
MIN_COMPLETENESS_RATIO: float = 0.5
MIN_COUNTRIES: int = 10

# ── Output Configuration ────────────────────────────────────────────────────────
OUTPUT_CSV: Path = OUTPUT_DIR / "wdi_panel.csv"
OUTPUT_PARQUET: Path = OUTPUT_DIR / "wdi_panel.parquet"

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_DIR: Path = PROJECT_ROOT / "logs"
LOG_FILE: Path = LOG_DIR / "wdi_etl.log"
LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

# ── Pipeline ────────────────────────────────────────────────────────────────────
REGIONAL_AGGREGATES_ENABLED: bool = True

"""
================================================================================
Configuration Module — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy
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
    2. Type-annotated values       — catch config errors before runtime
    3. Sensible defaults           — pipeline runs without any env vars set
    4. Documented constants        — every value carries a rationale comment

Usage
-----
    from wdi_etl.config import INDICATORS, YEAR_START, YEAR_END

Environment Overrides
---------------------
    For production deployments, replace any constant with an environment
    variable lookup, e.g.:
        import os
        YEAR_START = int(os.getenv("WDI_YEAR_START", 2014))

Notes on Regional Aggregates
-----------------------------
    The World Bank API returns both sovereign countries AND regional/national
    grouping aggregates (e.g. "World", "OECD members", "Sub-Saharan Africa").
    These records carry a 2-character WB code in the 'id' field and a valid
    3-character code in the 'countryiso3code' field.  The transform stage
    removes known aggregate ISO3 codes (WLD, OED, IDA, etc.) but retains
    regional groupings such as "Africa Eastern and Southern" that have
    valid 3-char ISO3 codes.  Set REGIONAL_AGGREGATES_ENABLED = False
    in this module to suppress them entirely.
================================================================================
"""

from pathlib import Path
from typing import Literal

# ── Project Directory Structure ─────────────────────────────────────────────────
# All pipeline I/O is rooted under the project directory, ensuring the
# pipeline is fully self-contained and reproducible on any machine that
# clones the repository.

PROJECT_ROOT: Path = Path(__file__).parent.parent
"""
Root directory of the project. Resolved relative to this file's location.
Used as the anchor for all other path constants.
"""

DATA_DIR: Path = PROJECT_ROOT / "data"
"""
Top-level data directory. Houses raw, interim, and output sub-trees.
"""

OUTPUT_DIR: Path = DATA_DIR / "output"
"""
Final pipeline artefacts (CSV, Parquet) land here.
"""

RAW_DIR: Path = DATA_DIR / "raw"
"""
Raw JSON responses from the World Bank API are cached here after extraction.
Caching allows the transform/load stages to run without re-fetching data.
"""

INTERIM_DIR: Path = DATA_DIR / "interim"
"""
Intermediate artefacts (e.g. cleaned indicator CSVs) can be written here
during development for debugging. Not required for normal operation.
"""

# ── World Bank API Connection ───────────────────────────────────────────────────
# The World Bank API is a free, public REST API. No authentication is required.
# See: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581

WB_API_BASE: str = "https://api.worldbank.org/v2"
"""
Base URL for the World Bank API v2. All indicator queries are relative to this.
"""

WB_FORMAT: str = "json"
"""
Response format. Only 'json' is supported by this pipeline.
"""

WB_PER_PAGE: int = 10_000
"""
Maximum records returned per API page. The WB API accepts values up to 10,000.
Setting this to the maximum reduces the number of pagination round-trips.
"""

# ── Indicator Definitions ──────────────────────────────────────────────────────
# Each entry maps a World Bank indicator code to a human-readable description.
# To add a new indicator, append a new {code: description} pair here and
# only here — no other module needs to change.
#
# Indicator code schema (World Bank convention):
#   NY.GDP.PCAP.CD  → NY: National Accounts | GDP | PCAP: per capita | CD: current US$
#   IT.NET.USER.ZS  → IT: Infrastructure    | NET: network         | USERS % of population
#   SP.URB.TOTL.IN.ZS → SP: Social         | URB: urban            | % of total
#   SL.TLF.CACT.FE.ZS  → SL: Social         | LF: labour force      | female participation
#   NY.GNP.PCAP.CD  → NY: National Accounts | GNP | PCAP: per capita | Atlas method

INDICATORS: dict[str, str] = {
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "IT.NET.USER.ZS": "Internet users (% of population)",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total)",
    "SL.TLF.CACT.FE.ZS": "Labor force participation rate, female (% of female population ages 15+)",
    "NY.GNP.PCAP.CD": "GNI per capita, Atlas method (current US$)",
}

# ── Temporal Scope ─────────────────────────────────────────────────────────────
# Inclusive year boundaries for all indicator queries.
# Adjust these to widen/narrow the panel. The transform stage enforces these
# boundaries, so changing them here does not require changes elsewhere.

YEAR_START: int = 2014
"""
First year (inclusive) to include in the panel.
"""

YEAR_END: int = 2023
"""
Last year (inclusive) to include in the panel.
"""

# ── Missing-Value Handling ──────────────────────────────────────────────────────
# Real-world economic data always contains missing observations.  This strategy
# is applied AFTER the data has been cleaned and merged into a panel, operating
# per (country, indicator) group along the time dimension.
#
# Available strategies:
#   "drop"           — Remove rows with NaN values entirely. Use when missingness
#                      is believed to be random and少量的 data would be lost.
#   "forward_fill"   — Propagate the last observed value forward.  Appropriate
#                      when the true value is not expected to change sharply
#                      between reporting periods.
#   "backward_fill"  — Fill backwards from the next observed value.  Use with
#                      care; can introduce look-ahead bias in some analyses.
#   "interpolate"    — Linear interpolation between known values.  Suitable for
#                      smooth economic indicators (e.g. GDP per capita).
#   "keep"           — Retain NaN rows.  Required for analyses that explicitly
#                      model missingness or when downstream tools handle it.

MISSING_STRATEGY: Literal[
    "drop", "forward_fill", "backward_fill", "interpolate", "keep"
] = "keep"
"""
Default strategy applied to handle missing values in the panel.
Overridden via the CLI flag --missing-strategy at runtime.
"""

# ── Country Name Standardisation ───────────────────────────────────────────────
# The World Bank uses a set of country name variants that differ from
# ISO/UN standard names.  This dictionary maps the WB name (key) to the
# canonical name (value) used in the output panel.
#
# Only entries for countries that appear in our indicator set are included.
# Add entries here when a new indicator introduces a previously unseen variant.

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

# ── Validation & Quality Thresholds ───────────────────────────────────────────
# These thresholds govern quality gates in the transform stage.  Indicators
# that breach MIN_COMPLETENESS_RATIO or MIN_COUNTRIES are flagged in the
# validation report but are NOT automatically dropped, preserving analyst
# agency to make case-by-case decisions.

MIN_COMPLETENESS_RATIO: float = 0.5
"""
Minimum fraction of (country, year) cells that must be non-null for an
indicator to be considered sufficiently complete.  An indicator with more
than (1 - MIN_COMPLETENESS_RATIO) missing data triggers a warning.
Set to 0.5 meaning: warn if >50% of cells are missing.
"""

MIN_COUNTRIES: int = 10
"""
Minimum number of distinct countries that must have at least one valid
observation for an indicator to be retained.  Prevents indicators that
only cover a handful of small states from inflating the panel.
"""

# ── Output Configuration ───────────────────────────────────────────────────────
# Final output file paths.  Both paths are relative to OUTPUT_DIR and are
# controlled here so that downstream consumers (dashboards, archival scripts)
# can discover outputs from a single location.

OUTPUT_CSV: Path = OUTPUT_DIR / "wdi_panel.csv"
"""
Path for the tidy panel CSV. Written with UTF-8-BOM encoding to ensure
correct rendering of Unicode characters in Microsoft Excel on Windows.
"""

OUTPUT_PARQUET: Path = OUTPUT_DIR / "wdi_panel.parquet"
"""
Path for the Parquet artefact.  Parquet provides column-wise compression,
faster reads for analytics workloads, and type preservation (year stays int64,
not object).  Written with pyarrow engine.
"""

# ── Regional Aggregates Control ─────────────────────────────────────────────────
# Set to False to exclude regional/national-grouping aggregates from the output.
# When True, aggregates with valid 3-char ISO3 codes (e.g. AFE = Africa Eastern
# and Southern) are included alongside sovereign countries.

REGIONAL_AGGREGATES_ENABLED: bool = True
"""
Toggle inclusion of regional grouping aggregates in the output panel.
"""

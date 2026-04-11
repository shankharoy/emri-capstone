"""
================================================================================
Transform Stage — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy (Senior Data Engineer)
Version     : 1.0.0
Created     : 2026-04-11

Description :
    Responsible for the Transform phase. Takes raw JSON responses, cleans and
    standardises the data, merges all indicators into a single tidy panel,
    applies the configured missing-value strategy, and runs validation checks.

Tidy Data Principles
-------------------
    1. Each column is a variable  — country_iso3, year, indicator_code, value
    2. Each row is an observation — one country's value in one year for one indicator
    3. One table, many indicators — stored as column values, not separate columns

Missing-Value Strategies
------------------------
    Applied per (country, indicator) group along the year axis:
      forward_fill   : last known value propagated forward
      backward_fill  : next known value propagated backward
      interpolate    : linear interpolation between observed values
      drop           : remove NaN rows entirely
      keep           : leave NaN rows (required for explicit missingness tracking)

Validation Checks
----------------
    validate_panel() runs three checks and returns a structured report:
      1. Year-range completeness
      2. Duplicate (country_iso3, year, indicator) rows
      3. Per-indicator completeness vs MIN_COMPLETENESS_RATIO threshold
================================================================================
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pandas as pd

from wdi_etl.config import (
    COUNTRY_NAME_CORRECTIONS,
    YEAR_END,
    YEAR_START,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# ── Aggregate ISO3 codes to exclude ────────────────────────────────────────────
_AGGREGATE_CODES: frozenset[str] = frozenset({
    "WLD", "OED", "IDA", "IBD", "IBRD", "LDC", "LTE",
})


# ════════════════════════════════════════════════════════════════════════════════
# Private Helpers
# ════════════════════════════════════════════════════════════════════════════════


def _parse_indicator_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """
    Flatten a single WB API observation record into a canonical dict.

    Returns None for records with null values (handled upstream by dropping Nones).
    Uses 'countryiso3code' field for the ISO3 code — see note in docstring.
    """
    if record.get("value") is None:
        return None

    country: dict[str, Any] = record.get("country", {})

    return {
        "country_name": country.get("value", "").strip(),
        # WB API provides TWO country codes:
        #   country["id"]       — 2-char WB area code (e.g. "AL")
        #   countryiso3code     — 3-char ISO 3166-1 alpha-3 (e.g. "ALB")
        # We use countryiso3code as it is internationally standard.
        "country_iso3": record.get("countryiso3code", "").strip(),
        "indicator_code": record.get("indicator", {}).get("id", ""),
        "indicator_name": record.get("indicator", {}).get("value", ""),
        "year": int(record.get("date", 0)),
        "value": float(record["value"]),
    }


def _standardize_country_name(name: str) -> str:
    """Apply config.COUNTRY_NAME_CORRECTIONS mapping."""
    return COUNTRY_NAME_CORRECTIONS.get(name, name).strip()


def _standardize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce correct pandas dtypes on the indicator DataFrame.

    Operates on a copy to avoid SettingWithCopyWarning.
    """
    df = df.copy()
    df["year"] = df["year"].astype(int)
    df["value"] = pd.to_numeric(df["value"], errors="coerce").astype(float)
    df["country_name"] = df["country_name"].astype(str)
    df["country_iso3"] = df["country_iso3"].astype(str).str.upper().str.strip()
    df["indicator_code"] = df["indicator_code"].astype(str)
    df["indicator_name"] = df["indicator_name"].astype(str)
    return df


def _filter_years(df: pd.DataFrame) -> pd.DataFrame:
    """Retain only rows within [YEAR_START, YEAR_END]."""
    return df[(df["year"] >= YEAR_START) & (df["year"] <= YEAR_END)]


def _fill_missing(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """
    Apply the configured missing-value strategy per (country, indicator).

    groupby ensures fill values do NOT bleed across different indicators
    or countries.  interpolate() does NOT extrapolate beyond observed range
    — edge NaNs remain as NaN, which is correct for economic data.
    """
    df = df.copy()
    df = df.sort_values(["country_iso3", "indicator_code", "year"])

    grouped: pd.core.groupby.DataFrameGroupBy = df.groupby(
        ["country_iso3", "indicator_code"], group_keys=False
    )

    if strategy == "forward_fill":
        df["value"] = grouped["value"].transform(lambda s: s.ffill())
    elif strategy == "backward_fill":
        df["value"] = grouped["value"].transform(lambda s: s.bfill())
    elif strategy == "interpolate":
        df["value"] = grouped["value"].transform(lambda s: s.interpolate())

    return df


# ════════════════════════════════════════════════════════════════════════════════
# Public Transform Functions
# ════════════════════════════════════════════════════════════════════════════════


def clean_indicator(raw_records: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Parse, standardise, and lightly validate raw API records for one indicator.

    Steps
    -----
        1. Flatten nested API records, discard null values
        2. Apply country name corrections
        3. Enforce correct dtypes
        4. Filter to [YEAR_START, YEAR_END]
        5. Retain only valid 3-char ISO3 codes
        6. Remove known aggregate groupings

    Parameters
    ----------
    raw_records : list of raw WB API observation dicts.

    Returns
    -------
    pd.DataFrame
        Columns: country_name, country_iso3, indicator_code, indicator_name, year, value.
        Returns empty DataFrame with correct schema if all records are null/invalid.
    """
    # Step 1 + 2: Parse and discard nulls
    rows: list[dict[str, Any]] = [
        r for r in (_parse_indicator_record(rec) for rec in raw_records)
        if r is not None
    ]

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(
            columns=["country_name", "country_iso3", "indicator_code",
                     "indicator_name", "year", "value"]
        )

    # Step 3: Name corrections
    df["country_name"] = df["country_name"].apply(_standardize_country_name)

    # Step 4: dtype enforcement
    df = _standardize_dtypes(df)

    # Step 5: Year range
    df = _filter_years(df)

    # Step 6: Valid ISO3 filter (exactly 3 uppercase characters)
    df = df[df["country_iso3"].str.len() == 3]

    # Step 7: Remove known aggregates
    df = df[~df["country_iso3"].isin(_AGGREGATE_CODES)]

    logger.debug("clean_indicator: %d input records -> %d clean rows",
                 len(raw_records), len(df))
    return df.reset_index(drop=True)


def merge_to_panel(
    indicator_dfs: dict[str, pd.DataFrame],
    missing_strategy: str = "keep",
) -> pd.DataFrame:
    """
    Stack all per-indicator DataFrames into a single tidy panel.

    Parameters
    ----------
    indicator_dfs : dict[str, pd.DataFrame]
        Mapping from indicator code to its cleaned DataFrame.
    missing_strategy : str
        One of "drop", "forward_fill", "backward_fill", "interpolate", "keep".

    Returns
    -------
    pd.DataFrame
        Tidy panel: country_iso3, country_name, year, value, indicator_code.
    """
    frames: list[pd.DataFrame] = []

    for code, df in indicator_dfs.items():
        subset = df[["country_iso3", "country_name", "year", "value"]].copy()
        subset["indicator_code"] = code
        frames.append(subset)

    panel = pd.concat(frames, ignore_index=True)

    # Re-apply year filter in case concat introduced out-of-range rows
    panel = panel[(panel["year"] >= YEAR_START) & (panel["year"] <= YEAR_END)]

    # Missing-value strategy
    if missing_strategy == "drop":
        panel = panel.dropna(subset=["value"])
    elif missing_strategy in {"forward_fill", "backward_fill", "interpolate"}:
        panel = _fill_missing(panel, missing_strategy)
    # "keep" -> leave NaN rows

    logger.info("merge_to_panel: shape=%s, missing_strategy=%s",
                panel.shape, missing_strategy)
    return panel.reset_index(drop=True)


def validate_panel(df: pd.DataFrame) -> dict[str, Any]:
    """
    Run data-quality validation checks and return a structured report.

    Checks
    ------
    1. Year-range completeness
    2. Duplicate (country_iso3, year, indicator_code) rows  → hard error
    3. Per-indicator missing ratio vs config threshold       → warning

    Returns
    -------
    dict[str, Any]
        Keys: "passed" (bool), "errors" (list), "warnings" (list),
        and per-indicator missing ratios.
    """
    report: dict[str, Any] = {
        "passed": True,
        "warnings": [],
        "errors": [],
    }

    # Check 1: Year range
    expected_years: set[int] = set(range(YEAR_START, YEAR_END + 1))
    observed_years: set[int] = set(df["year"].unique())
    missing_years = expected_years - observed_years

    if missing_years:
        report["warnings"].append(
            f"Missing years in panel: {sorted(missing_years)}"
        )

    # Check 2: Duplicates
    dup_mask = df.duplicated(subset=["country_iso3", "year", "indicator_code"], keep=False)
    n_dups = dup_mask.sum()
    if n_dups > 0:
        report["errors"].append(f"Found {n_dups} duplicate rows — pipeline bug")
        report["passed"] = False

    # Check 3: Per-indicator completeness
    n_countries = df["country_iso3"].nunique()
    total_cells = n_countries * len(expected_years)

    for code, grp in df.groupby("indicator_code"):
        n_non_null = grp["value"].notna().sum()
        n_missing = total_cells - n_non_null
        ratio = n_missing / total_cells if total_cells else 0.0
        report[f"indicator_{code}_missing_ratio"] = round(ratio, 4)

        if ratio > 0.5:
            report["warnings"].append(
                f"'{code}' has {ratio:.1%} missing data — consider dropping"
            )

    if report["errors"]:
        report["passed"] = False

    logger.info("validate_panel: passed=%s, errors=%d, warnings=%d",
                report["passed"], len(report["errors"]), len(report["warnings"]))
    return report


def transform_all(
    raw_data: dict[str, list[dict[str, Any]]],
    missing_strategy: str = "keep",
) -> pd.DataFrame:
    """
    Execute the complete transform pipeline: clean -> merge -> validate.

    Parameters
    ----------
    raw_data : dict mapping indicator code to raw API records.
    missing_strategy : str
        Strategy for handling missing values.

    Returns
    -------
    pd.DataFrame
        Validated tidy panel DataFrame.
    """
    logger.info("Starting transform stage")
    cleaned: dict[str, pd.DataFrame] = {}

    for code, records in raw_data.items():
        cleaned[code] = clean_indicator(records)
        logger.info("  %s: %d clean rows", code, len(cleaned[code]))

    panel = merge_to_panel(cleaned, missing_strategy=missing_strategy)
    report = validate_panel(panel)

    for err in report["errors"]:
        logger.error("  %s", err)
    for warning in report["warnings"]:
        logger.warning("  %s", warning)

    logger.info("Transform complete: shape=%s, validation_passed=%s",
                panel.shape, report["passed"])
    return panel

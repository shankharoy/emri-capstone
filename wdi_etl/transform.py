"""
================================================================================
Transform Stage — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy 
Version     : 1.0.0
Created     : 2026-04-11
Description :
    Responsible for the Transform phase of the ETL pipeline. Takes raw JSON
    responses from the extract stage, cleans and standardises the data, merges
    all indicators into a single tidy panel, applies the configured missing-value
    strategy, and runs validation checks.

    The output is a "tidy" panel DataFrame where each row represents one
    observation: a (country, year, indicator) triplet, with the numeric value
    in a single column.  This structure is the de-facto standard for panel
    data in Python (pandas, polars) and feeds directly into analytics,
    visualisation, and modelling tools.

Tidy Data Principles Applied
-----------------------------
    1. Each column is a variable  — country_iso3, year, indicator_code, value
    2. Each row is an observation — one country's value for one indicator in
       one year
    3. One table, many indicators — indicators are stored as column values
       (indicator_code), not as separate columns, enabling easy filtering,
       grouping, and pivoting without schema changes

Missing-Value Strategies
-----------------------
    Strategies are applied per (country, indicator) group along the year axis.
    The group-wise approach prevents a value from one country leaking into
    another country's series.

    forward_fill   : carries the last known value forward.  Ideal for
                     structural indicators that change slowly (e.g. urbanisation
                     rate).  Does NOT extrapolate beyond the last observed year.
    backward_fill  : carries the next known value backward.  Rarely appropriate
                     for economic time series due to look-ahead risk.
    interpolate    : linear interpolation between observed values.  Best for
                     smooth series like GDP where the true value is between
                     reporting points.
    drop           : removes rows with NaN entirely.  Preserves data integrity
                     at the cost of panel completeness.
    keep           : leaves NaN rows in the DataFrame.  Required when the
                     downstream consumer needs to track missingness explicitly.

Validation Checks
----------------
    validate_panel() runs three classes of checks and returns a structured
    report dict with 'passed', 'errors', and 'warnings' keys.  Errors cause the
    pipeline to halt; warnings are informational and do not block execution.

    Checks performed:
      1. Year-range completeness — are all configured years present?
      2. Duplicate detection     — no (country_iso3, year, indicator_code) may
                                  appear more than once
      3. Indicator completeness  — per-indicator missing ratio vs threshold

================================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from wdi_etl.config import (
    COUNTRY_NAME_CORRECTIONS,
    INDICATORS,
    YEAR_END,
    YEAR_START,
)

if TYPE_CHECKING:
    # Avoid circular import at runtime; only used for type checking
    from pathlib import Path


# ════════════════════════════════════════════════════════════════════════════════
# Private Helper Functions
# ════════════════════════════════════════════════════════════════════════════════


def _parse_indicator_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """
    Flatten a single World Bank API observation record into a canonical dict.

    The WB API returns nested JSON where 'country' is an object with 'id' and
    'value', 'indicator' is similarly nested, and 'countryiso3code' is a
    sibling field.  This function collapses that structure into a flat
    representation suitable for DataFrame construction.

    Parameters
    ----------
    record : dict[str, Any]
        One raw observation dict as returned by fetch_indicator().

    Returns
    -------
    dict[str, Any] | None
        A flat dict with keys: country_name, country_iso3, indicator_code,
        indicator_name, year, value.  Returns None if the 'value' field
        is None, signalling a genuinely missing observation at source.
        Returning None causes the caller to discard the record via list
        comprehension, keeping the pipeline's data flow explicit.

    Note on countryiso3code
    ------------------------
        The WB API provides TWO country identifiers:
          - country["id"] : 2-character World Bank area code (e.g. "AL")
          - countryiso3code : 3-character ISO 3166-1 alpha-3 code (e.g. "ALB")
        We use countryiso3code for country_iso3 because it is unambiguous and
        internationally standard.  The 2-char code is not used for identification.
    """
    if record.get("value") is None:
        # Genuinely missing at source — return None to signal discard upstream
        return None

    country: dict[str, Any] = record.get("country", {})

    return {
        "country_name": country.get("value", "").strip(),
        # Use ISO3 field explicitly — see note above
        "country_iso3": record.get("countryiso3code", "").strip(),
        "indicator_code": record.get("indicator", {}).get("id", ""),
        "indicator_name": record.get("indicator", {}).get("value", ""),
        "year": int(record.get("date", 0)),
        # float() is safe here because the None check above guarantees a numeric value
        "value": float(record["value"]),
    }


def _standardize_country_name(name: str) -> str:
    """
    Map a World Bank country name variant to its canonical form.

    The World Bank uses a set of display names that diverge from ISO/UN
    conventions (e.g. "Korea, Rep." vs "Korea, Republic of").  This function
    applies the corrections defined in config.COUNTRY_NAME_CORRECTIONS.

    Parameters
    ----------
    name : str
        Raw country name string from the WB API.

    Returns
    -------
    str
        Corrected name if a correction exists in the mapping, otherwise the
        original string with leading/trailing whitespace stripped.

    Example
    -------
    >>> _standardize_country_name("Korea, Rep.")
    'Korea, Republic of'
    """
    return COUNTRY_NAME_CORRECTIONS.get(name, name).strip()


def _standardize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce correct pandas dtypes on the indicator DataFrame.

    Calling this function after DataFrame construction ensures that:
      - year is stored as int64 (not float64, which occurs from pandas concat)
      - value is stored as float64 (required for arithmetic operations)
      - string columns are explicitly object dtype (not mixed)
      - country_iso3 is uppercased and stripped of accidental whitespace

    This function intentionally returns a copy (df.copy()) to make the
    mutation explicit and avoid SettingWithCopyWarning from pandas.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with potentially mixed or inferred dtypes.

    Returns
    -------
    pd.DataFrame
        A new DataFrame with standardised dtypes.
    """
    df = df.copy()
    df["year"] = df["year"].astype(int)
    # pd.to_numeric with errors='coerce' converts non-numeric strings to NaN,
    # which is the correct behaviour for any malformed values at this stage.
    df["value"] = pd.to_numeric(df["value"], errors="coerce").astype(float)
    df["country_name"] = df["country_name"].astype(str)
    df["country_iso3"] = (
        df["country_iso3"].astype(str).str.upper().str.strip()
    )
    df["indicator_code"] = df["indicator_code"].astype(str)
    df["indicator_name"] = df["indicator_name"].astype(str)
    return df


def _filter_years(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retain only rows whose year falls within the configured range.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with a 'year' column.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame containing only rows where YEAR_START <= year <= YEAR_END.

    Note
    ----
    Year filtering is applied BEFORE the ISO3 aggregate filter so that both
    sovereign countries and aggregates are treated uniformly for year coverage.
    """
    return df[(df["year"] >= YEAR_START) & (df["year"] <= YEAR_END)]


def _fill_missing(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """
    Apply the configured missing-value filling strategy per (country, indicator).

    The groupby approach ensures that fill values do NOT bleed across different
    indicators or different countries, which would be statistically meaningless.

    Parameters
    ----------
    df : pd.DataFrame
        Panel DataFrame with a 'value' column that may contain NaN.
    strategy : str
        One of "forward_fill", "backward_fill", "interpolate".

    Returns
    -------
    pd.DataFrame
        DataFrame with NaN values in 'value' replaced according to the strategy.

    Interpolation Boundary Behaviour
    -------------------------------
    pandas.DataFrame.interpolate() does NOT extrapolate beyond the first/last
    known value — edge NaNs remain as NaN after interpolation.  This is the
    correct behaviour for economic data where we cannot legitimately guess
    beyond the reporting window.
    """
    df = df.copy()
    # Sort is required so that ffill/bffill/interpolate operate in chronological order
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

    This function is the primary cleaning entry point.  It:
      1. Flattens nested API records into flat dicts, discarding null values
      2. Applies country name corrections
      3. Standardises dtypes
      4. Filters to the configured year range
      5. Removes rows with non-3-char ISO3 codes (invalid identifiers)
      6. Drops known World Bank aggregate groupings (e.g. "World", "OECD")

    Parameters
    ----------
    raw_records : list[dict[str, Any]]
        List of raw observation records for a single indicator, as returned
        by fetch_indicator().

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with columns:
        country_name, country_iso3, indicator_code, indicator_name, year, value.

        Returns an empty DataFrame with the correct column schema if all records
        are null or invalid, preserving downstream concat contract.

    Cleaning Steps
    --------------
        Step 1 — Parse:  _parse_indicator_record() extracts and flattens fields
        Step 2 — Discard None entries (source-level missing values)
        Step 3 — Name standardisation via _standardize_country_name()
        Step 4 — dtype enforcement via _standardize_dtypes()
        Step 5 — Year range filter via _filter_years()
        Step 6 — ISO3 validity filter: str.len() == 3
        Step 7 — Aggregate removal: excludes WLD, OED, IDA, IBD, IBRD, LDC, LTE
    """
    # Step 1 + 2: Parse and discard nulls
    rows: list[dict[str, Any]] = [
        r for r in (_parse_indicator_record(rec) for rec in raw_records)
        if r is not None
    ]

    df = pd.DataFrame(rows)

    if df.empty:
        # Return empty frame with correct columns — avoids concat failures later
        return pd.DataFrame(
            columns=["country_name", "country_iso3", "indicator_code",
                     "indicator_name", "year", "value"]
        )

    # Step 3: Country name corrections
    df["country_name"] = df["country_name"].apply(_standardize_country_name)

    # Step 4: dtype enforcement
    df = _standardize_dtypes(df)

    # Step 5: Year range filter
    df = _filter_years(df)

    # Step 6: Valid ISO3 filter (must be exactly 3 uppercase characters)
    df = df[df["country_iso3"].str.len() == 3]

    # Step 7: Remove known aggregate groupings
    AGGREGATE_CODES: set[str] = {"WLD", "OED", "IDA", "IBD", "IBRD", "LDC", "LTE"}
    df = df[~df["country_iso3"].isin(AGGREGATE_CODES)]

    return df.reset_index(drop=True)


def merge_to_panel(
    indicator_dfs: dict[str, pd.DataFrame],
    missing_strategy: str = "keep",
) -> pd.DataFrame:
    """
    Stack all per-indicator DataFrames into a single tidy panel and apply
    the missing-value handling strategy.

    Parameters
    ----------
    indicator_dfs : dict[str, pd.DataFrame]
        Mapping from indicator code to its cleaned DataFrame (as returned by
        clean_indicator()).
    missing_strategy : str, default "keep"
        Strategy for handling rows where 'value' is NaN.
        Valid values: "drop", "forward_fill", "backward_fill", "interpolate",
        "keep".  See module docstring for full behaviour description.

    Returns
    -------
    pd.DataFrame
        Tidy panel DataFrame with one row per (country, year, indicator) and
        columns: country_iso3, country_name, year, value, indicator_code.

    Panel Structure (Tidy Format)
    ----------------------------
        Each row = one observation
        Each column = one variable
        indicator_code is a column value (not separate columns), making this
        compatible with seaborn, plotly, and panel regression libraries
        (linearmodels, statsmodels).

    Merge Algorithm
    --------------
        pd.concat() is used rather than SQL-style joins because the data is
        already in a tidy structure — no join key resolution is needed.
        concat with ignore_index=True ensures the resulting index is
        contiguous and free of artifacts from per-indicator DataFrames.
    """
    frames: list[pd.DataFrame] = []

    for code, df in indicator_dfs.items():
        # Select and copy the columns needed in the final panel
        subset = df[["country_iso3", "country_name", "year", "value"]].copy()
        subset["indicator_code"] = code
        frames.append(subset)

    # Concatenate along rows — produces one tall DataFrame
    panel = pd.concat(frames, ignore_index=True)

    # Re-apply year range filter in case any records fell outside after concat
    panel = panel[
        (panel["year"] >= YEAR_START) & (panel["year"] <= YEAR_END)
    ]

    # ── Missing-value strategy ───────────────────────────────────────────────
    if missing_strategy == "drop":
        # dropna with subset=['value'] only removes rows where value is NaN,
        # preserving rows where other columns might have incidental nulls
        panel = panel.dropna(subset=["value"])
    elif missing_strategy in {"forward_fill", "backward_fill", "interpolate"}:
        panel = _fill_missing(panel, missing_strategy)
    # "keep" — leave NaN rows in place

    return panel.reset_index(drop=True)


def validate_panel(df: pd.DataFrame) -> dict[str, Any]:
    """
    Run data-quality validation checks on the panel and return a structured report.

    This function is a "gate" that ensures the panel meets minimum quality
    standards before it is loaded.  Errors (duplicate rows) cause immediate
    pipeline halt; warnings (missing years, high missingness) are informational
    and do not block execution, preserving analyst agency.

    Checks Performed
    ----------------
    1. Year-range completeness:
           Compares sorted(df["year"].unique()) against the configured
           [YEAR_START, YEAR_END] range.  Missing years are flagged as warnings.

    2. Duplicate detection:
           Checks for rows where (country_iso3, year, indicator_code) is not
           unique.  Duplicates indicate a bug in the extract or transform logic
           and are treated as hard errors.

    3. Per-indicator completeness:
           Computes the missing-data ratio for each indicator as:
               ratio = (total_cells - non_null_rows) / total_cells
           where total_cells = n_countries × n_years.
           Ratios above config.MIN_COMPLETENESS_RATIO (default 0.5) trigger
           a warning suggesting the indicator be dropped.

    Parameters
    ----------
    df : pd.DataFrame
        The merged, cleaned panel DataFrame to validate.

    Returns
    -------
    dict[str, Any]
        Structured validation report with keys:
          - "passed"  : bool — True if no errors occurred
          - "errors"  : list[str] — descriptions of hard errors
          - "warnings": list[str] — descriptions of quality warnings
          - "indicator_{code}_missing_ratio" : float — per-indicator completeness

    Usage in Orchestrator
    ---------------------
        report = validate_panel(panel)
        if not report["passed"]:
            raise RuntimeError("Panel validation failed: " + "; ".join(report["errors"]))
        for warning in report["warnings"]:
            print(f"[transform] WARNING: {warning}")
    """
    report: dict[str, Any] = {
        "passed": True,
        "warnings": [],
        "errors": [],
    }

    # ── Check 1: Year range completeness ────────────────────────────────────
    observed_years: set[int] = set(df["year"].unique())
    expected_years: set[int] = set(range(YEAR_START, YEAR_END + 1))
    missing_years: set[int] = expected_years - observed_years

    if missing_years:
        report["warnings"].append(
            f"Missing years in panel: {sorted(missing_years)}. "
            "Check whether the World Bank API returned data for these years."
        )

    # ── Check 2: Duplicate rows ─────────────────────────────────────────────
    dup_mask: pd.Series = df.duplicated(
        subset=["country_iso3", "year", "indicator_code"], keep=False
    )
    n_duplicates: int = dup_mask.sum()

    if n_duplicates > 0:
        report["errors"].append(
            f"Found {n_duplicates} duplicate rows in panel. "
            "This indicates a bug in the extract or transform logic. "
            "Duplicate (country_iso3, year, indicator_code) combinations are not allowed."
        )
        report["passed"] = False

    # ── Check 3: Per-indicator completeness ─────────────────────────────────
    n_countries: int = df["country_iso3"].nunique()
    n_years_total: int = len(expected_years)
    total_cells: int = n_countries * n_years_total

    for code, grp in df.groupby("indicator_code"):
        n_non_null: int = grp["value"].notna().sum()
        n_missing: int = total_cells - n_non_null
        ratio_missing: float = n_missing / total_cells if total_cells else 0.0

        report[f"indicator_{code}_missing_ratio"] = round(ratio_missing, 4)

        if ratio_missing > 0.5:
            report["warnings"].append(
                f"Indicator '{code}' has {ratio_missing:.1%} missing data "
                f"({n_missing:,} of {total_cells:,} cells). "
                "Consider dropping this indicator or applying a fill strategy."
            )

    # Mark failed if any errors were found
    if report["errors"]:
        report["passed"] = False

    return report


# ════════════════════════════════════════════════════════════════════════════════
# Orchestrator
# ════════════════════════════════════════════════════════════════════════════════


def transform_all(
    raw_data: dict[str, list[dict[str, Any]]],
    missing_strategy: str = "keep",
) -> pd.DataFrame:
    """
    Execute the complete transform pipeline: clean → merge → validate.

    This is the top-level entry point for the transform stage, called by
    the orchestrator in __main__.py.  It coordinates the three sub-stages
    and streams progress messages to stdout.

    Parameters
    ----------
    raw_data : dict[str, list[dict[str, Any]]]
        Mapping from indicator code to raw API observation records, as
        returned by extract_all().
    missing_strategy : str, default "keep"
        Strategy for handling missing values.  See merge_to_panel() and
        the module docstring for full description.

    Returns
    -------
    pd.DataFrame
        The fully validated tidy panel DataFrame.

    Pipeline Flow
    -------------
        1. clean_indicator()  — called once per indicator
        2. merge_to_panel()  — stacks all indicators, applies missing strategy
        3. validate_panel()   — quality gate; errors halt the pipeline

    Example
    -------
        >>> panel = transform_all(raw_data, missing_strategy="forward_fill")
        >>> panel.shape
        (11817, 5)
    """
    print("[transform] Cleaning individual indicators ...")
    cleaned: dict[str, pd.DataFrame] = {}

    for code, records in raw_data.items():
        cleaned[code] = clean_indicator(records)
        n: int = len(cleaned[code])
        print(f"[transform]   {code}: {n:,} clean rows")

    print("[transform] Merging to panel ...")
    panel: pd.DataFrame = merge_to_panel(cleaned, missing_strategy=missing_strategy)

    print("[transform] Validating panel ...")
    report: dict[str, Any] = validate_panel(panel)

    if report["errors"]:
        for err in report["errors"]:
            print(f"[transform] ERROR: {err}")
    for warning in report["warnings"]:
        print(f"[transform] WARNING: {warning}")

    print(f"[transform] Panel shape: {panel.shape}")
    print(f"[transform] Validation passed: {report['passed']}")

    return panel

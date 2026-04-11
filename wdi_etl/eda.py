"""
================================================================================
Exploratory Data Analysis (EDA) Module — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy (Senior Data Engineer)
Version     : 1.0.0
Created     : 2026-04-11

Description
-----------
    Provides a suite of standalone EDA functions that operate on the tidy panel
    DataFrame produced by the ETL pipeline.  Functions are designed to be
    composable and are also auto-invoked from run_eda(), making this module
    usable both as a library (imported from wdi_etl.eda) and as a standalone
    script (python -m wdi_etl.eda).

Functions
---------
    load_panel(path)              — Load the CSV or Parquet output into a DataFrame
    summary_stats(df)            — Descriptive statistics for the full panel
    missingness_report(df)       — Missing-value heatmap + per-indicator breakdown
    coverage_by_country(df)      — Country-level data completeness
    coverage_by_year(df)         — Year-level data completeness
    indicator_correlation(df)    — Pairwise Pearson correlation across indicators
    distribution_by_indicator(df) — Distribution summary per indicator
    time_series_plot(df, iso3, indicator) — Time-series line chart for a country
    top_bottom(df, indicator, n) — Top / bottom N countries for an indicator
    run_eda(path)                — Auto-runs all EDA functions and prints a report

Usage
-----
    # As a library
    from wdi_etl.eda import run_eda, summary_stats
    panel = load_panel("data/output/wdi_panel.csv")
    stats = summary_stats(panel)

    # As a standalone script
    python -m wdi_etl.eda                              # uses default path
    python -m wdi_etl.eda data/output/wdi_panel.csv   # custom path

    # Inside a Jupyter notebook
    %run wdi_etl/eda.py
    eda_report = run_eda()
================================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Module-level constants (same layout as config.py)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_PANEL_CSV: Path = Path(__file__).parent.parent / "data" / "output" / "wdi_panel.csv"
"""Default path to the ETL pipeline output CSV."""

INDICATOR_LABELS: dict[str, str] = {
    "NY.GDP.PCAP.CD":   "GDP per capita (US$)",
    "IT.NET.USER.ZS":  "Internet users (%)",
    "SP.URB.TOTL.IN.ZS": "Urban population (%)",
    "SL.TLF.CACT.FE.ZS": "Female labour force participation (%)",
    "NY.GNP.PCAP.CD":   "GNI per capita, Atlas (US$)",
}
"""Human-readable display names for each indicator code."""

SEABORN_AVAILABLE: bool = True
"""Flag used to gracefully handle environments without seaborn / matplotlib."""


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────


def load_panel(path: Optional[Path | str] = None) -> pd.DataFrame:
    """
    Load the tidy panel from the ETL output CSV or Parquet file.

    Parameters
    ----------
    path : Path | str | None, default None
        Path to the output file.  If None, defaults to DEFAULT_PANEL_CSV.
        The function auto-detects the format from the file extension (.csv
        or .parquet) and uses the appropriate pandas reader.

    Returns
    -------
    pd.DataFrame
        Tidy panel with columns: country_iso3, country_name, year,
        indicator_code, value.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    ValueError
        If the file extension is neither .csv nor .parquet.

    Example
    -------
    >>> df = load_panel()
    >>> df.shape
    (11817, 5)
    """
    if path is None:
        path = DEFAULT_PANEL_CSV
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Panel file not found: {path}. "
            "Run 'python -m wdi_etl' first to produce the output."
        )

    if path.suffix == ".csv":
        df = pd.read_csv(path)
    elif path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(
            f"Unsupported file format: '{path.suffix}'. Use .csv or .parquet."
        )

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Summary Statistics
# ─────────────────────────────────────────────────────────────────────────────


def summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute descriptive statistics for the panel DataFrame.

    Produces a per-indicator summary table covering:
        - count  : number of non-null observations
        - mean   : arithmetic mean
        - std    : standard deviation
        - min    : minimum value
        - 25%    : first quartile
        - 50%    : median
        - 75%    : third quartile
        - max    : maximum value
        - null   : count of missing values

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel DataFrame from load_panel().

    Returns
    -------
    pd.DataFrame
        Summary statistics indexed by indicator_code.

    Example
    -------
    >>> stats = summary_stats(panel)
    >>> stats.loc["NY.GDP.PCAP.CD", "mean"]   # avg GDP per capita across all countries
    """
    # Compute stats directly on raw values per indicator — avoids the pivot
    # (which would compute describe() across-country means instead of all obs)
    indicator_codes = df["indicator_code"].unique()
    n_countries = df["country_iso3"].nunique()
    n_years_total = df["year"].nunique()
    total_cells = n_countries * n_years_total

    stats_list: list[pd.DataFrame] = []
    for code in indicator_codes:
        series = df.loc[df["indicator_code"] == code, "value"]
        desc = series.describe()
        null_count = total_cells - int(desc["count"])
        row = dict(desc)
        row["indicator_code"] = code
        row["null"] = null_count
        stats_list.append(row)

    summary = (
        pd.DataFrame(stats_list)
        .set_index("indicator_code")[[
            "count", "mean", "std", "min", "25%", "50%", "75%", "max", "null"
        ]]
        .rename(columns={
            "count": "n_obs",
            "50%": "median",
            "25%": "q25",
            "75%": "q75",
        })
        .loc[indicator_codes]   # preserve config order
    )
    summary.index.name = "indicator_code"

    # Rename the count column to 'count' (describe returns it as 'count')
    summary.rename(columns={"count": "n_obs"}, inplace=True)

    return summary.round(2)


# ─────────────────────────────────────────────────────────────────────────────
# Missing-Value Report
# ─────────────────────────────────────────────────────────────────────────────


def missingness_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-indicator missing-value ratios.

    Produces a DataFrame with one row per indicator and columns:
        - total_cells    : country × year combinations for this indicator
        - non_null       : number of non-null observations
        - null_count     : number of missing values
        - missing_ratio  : fraction of cells that are null (0.0 = complete)

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel DataFrame.

    Returns
    -------
    pd.DataFrame
        Missingness summary indexed by indicator_code.

    Example
    -------
    >>> miss = missingness_report(panel)
    >>> miss[miss["missing_ratio"] > 0.3]   # indicators with >30% missing data
    """
    indicators = df["indicator_code"].unique()
    n_countries = df["country_iso3"].nunique()
    n_years = df["year"].nunique()
    total_cells = n_countries * n_years

    rows = []
    for code in indicators:
        sub = df[df["indicator_code"] == code]
        non_null = sub["value"].notna().sum()
        null_count = total_cells - non_null
        rows.append(
            {
                "indicator_code": code,
                "total_cells": total_cells,
                "non_null": non_null,
                "null_count": null_count,
                "missing_ratio": round(null_count / total_cells, 4)
                if total_cells > 0
                else 0.0,
            }
        )

    result = pd.DataFrame(rows).set_index("indicator_code")
    result.sort_values("missing_ratio", ascending=False, inplace=True)
    return result


def missingness_heatmap_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a (country × year) pivot table of non-null presence for each indicator.

    Returns a DataFrame suitable for rendering as a heatmap (e.g. with seaborn
    or pandas.DataFrame.style).  Each cell is 1 if the observation is non-null
    and 0 if NaN.

    Returns
    -------
    pd.DataFrame
        Multi-level pivot: rows = country_iso3, columns = (indicator_code, year),
        values = 1.0 (present) or 0.0 (missing).

    Note
    ----
    The returned DataFrame can be large (one column per indicator-year pair).
    For large panels, slice to a subset of countries or years before visualising.
    """
    df_with_flag = df.copy()
    df_with_flag["present"] = df_with_flag["value"].notna().astype(int)

    heatmap = df_with_flag.pivot_table(
        index="country_iso3",
        columns=["indicator_code", "year"],
        values="present",
        aggfunc="max",
    )
    return heatmap.fillna(0).astype(int)


# ─────────────────────────────────────────────────────────────────────────────
# Coverage Analysis
# ─────────────────────────────────────────────────────────────────────────────


def coverage_by_country(df: pd.DataFrame, min_years: int = 5) -> pd.DataFrame:
    """
    Compute per-country data completeness: how many indicators and years have data.

    A country is considered "well-covered" if it has at least ``min_years``
    non-null observations across all indicators combined.

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel DataFrame.
    min_years : int, default 5
        Minimum number of years with non-null values for a country to be
        flagged as "well-covered".

    Returns
    -------
    pd.DataFrame
        One row per country, with columns: n_indicators_with_data,
        n_years_with_data, n_total_obs, is_well_covered.

    Example
    -------
    >>> cov = coverage_by_country(panel)
    >>> cov[cov["is_well_covered"]].shape[0]   # number of well-covered countries
    """
    rows = []
    for iso3, grp in df.groupby("country_iso3"):
        country_name = grp["country_name"].iloc[0]
        n_indicators = grp["indicator_code"].nunique()
        n_years = grp["year"].nunique()
        n_obs = grp["value"].notna().sum()
        is_well_covered = n_obs >= min_years * n_indicators
        rows.append(
            {
                "country_iso3": iso3,
                "country_name": country_name,
                "n_indicators_with_data": n_indicators,
                "n_years_with_data": n_years,
                "n_total_obs": n_obs,
                "is_well_covered": is_well_covered,
            }
        )

    result = pd.DataFrame(rows)
    result.sort_values("n_total_obs", ascending=False, inplace=True)
    return result.reset_index(drop=True)


def coverage_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-year data completeness for each indicator.

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel DataFrame.

    Returns
    -------
    pd.DataFrame
        Pivot table: rows = year, columns = indicator_code, values = count of
        non-null observations.  Also includes a 'total_indicators_reported'
        column showing how many of the 5 indicators had at least one non-null
        observation in that year.

    Example
    -------
    >>> yr_cov = coverage_by_year(panel)
    >>> yr_cov[yr_cov.index == 2023]   # data availability in the most recent year
    """
    pivoted = df.pivot_table(
        index="year",
        columns="indicator_code",
        values="value",
        aggfunc="count",          # count non-null values per indicator per year
    ).fillna(0).astype(int)

    pivoted["total_indicators_reported"] = (pivoted > 0).sum(axis=1)
    return pivoted


# ─────────────────────────────────────────────────────────────────────────────
# Indicator Correlation
# ─────────────────────────────────────────────────────────────────────────────


def indicator_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute pairwise Pearson correlation of indicator means across countries.

    For each country, the mean value per indicator (across all years) is
    computed.  Then the pairwise Pearson correlation between these mean series
    is returned as a symmetric matrix.

    This reveals structural relationships in the data — e.g. GDP per capita
    and internet penetration are typically strongly positively correlated across
    countries.

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel DataFrame.

    Returns
    -------
    pd.DataFrame
        Symmetric correlation matrix indexed and columns by indicator_code.
        Diagonal values are 1.0.

    Example
    -------
    >>> corr = indicator_correlation(panel)
    >>> corr.loc["NY.GDP.PCAP.CD", "IT.NET.USER.ZS"]   # correlation between GDP and internet
    """
    # Country-level means per indicator (average over years for each country)
    country_means = df.pivot_table(
        index="country_iso3",
        columns="indicator_code",
        values="value",
        aggfunc="mean",
    )

    # corr() computes Pearson pairwise correlation; pairwise non-null pairs used
    corr = country_means.corr(method="pearson")
    return corr.round(4)


# ─────────────────────────────────────────────────────────────────────────────
# Distribution Summary
# ─────────────────────────────────────────────────────────────────────────────


def distribution_by_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """
    Produce a distribution summary (skewness, kurtosis, IQR) per indicator.

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel DataFrame.

    Returns
    -------
    pd.DataFrame
        Per-indicator distribution metrics: skewness, kurtosis (excess),
        IQR (interquartile range), coefficient of variation (CV = std/mean).

    Note on Skewness Interpretation
    ------------------------------
        > 0  : right-skewed (long right tail — a few very high values, e.g. GDP)
        < 0  : left-skewed
        ≈ 0  : approximately symmetric

    Note on Kurtosis Interpretation
    -------------------------------
        ≈ 0  : normal-like tails (excess kurtosis under normal distribution)
        > 0  : heavier tails than normal (more extreme values than Gaussian)
        < 0  : lighter tails than normal
    """
    rows = []
    for code, grp in df.groupby("indicator_code"):
        series = grp["value"].dropna()
        if len(series) < 3:
            continue  # need at least 3 points for meaningful skew/kurtosis

        mean_val = series.mean()
        std_val = series.std()
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        cv = (std_val / mean_val) if mean_val != 0 else float("nan")

        rows.append(
            {
                "indicator_code": code,
                "n": len(series),
                "mean": round(mean_val, 2),
                "std": round(std_val, 2),
                "cv": round(cv, 4),
                "min": round(series.min(), 2),
                "q25": round(q1, 2),
                "median": round(series.median(), 2),
                "q75": round(q3, 2),
                "max": round(series.max(), 2),
                "iqr": round(iqr, 2),
                "skewness": round(series.skew(), 4),
                "kurtosis": round(series.kurtosis(), 4),
            }
        )

    result = pd.DataFrame(rows).set_index("indicator_code")
    result.sort_values("mean", ascending=False, inplace=True)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Top / Bottom Countries
# ─────────────────────────────────────────────────────────────────────────────


def top_bottom(
    df: pd.DataFrame,
    indicator: str,
    n: int = 10,
    year_range: tuple[int, int] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Return the top-N and bottom-N countries for a given indicator.

    Countries are ranked by their mean value across the specified year range
    (default: all available years).  Ranking uses mean because some countries
    may have data for only a subset of years.

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel DataFrame.
    indicator : str
        Indicator code to rank by (e.g. "NY.GDP.PCAP.CD").
    n : int, default 10
        Number of top and bottom countries to return.
    year_range : tuple[int, int] | None, default None
        Optional (start_year, end_year) tuple to restrict the ranking window.
        If None, all available years are used.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys: "top" and "bottom".  Each value is a DataFrame with columns:
        country_iso3, country_name, mean_value, n_years, first_year, last_year.

    Example
    -------
    >>> result = top_bottom(panel, "NY.GDP.PCAP.CD", n=5)
    >>> print(result["top"])
    >>> print(result["bottom"])
    """
    if indicator not in df["indicator_code"].values:
        raise ValueError(
            f"Indicator '{indicator}' not found. "
            f"Available: {df['indicator_code'].unique().tolist()}"
        )

    sub = df[df["indicator_code"] == indicator].copy()

    if year_range:
        sub = sub[(sub["year"] >= year_range[0]) & (sub["year"] <= year_range[1])]

    # Aggregate to country level — each column aggregated independently
    # (value -> mean/count, year -> min/max to get actual year range)
    agg = (
        sub.groupby(["country_iso3", "country_name"])
        .agg(
            mean_value=("value", "mean"),
            n_years=("year", "count"),
            first_year=("year", "min"),
            last_year=("year", "max"),
        )
        .reset_index()
    )
    agg = agg.dropna(subset=["mean_value"])
    agg = agg.sort_values("mean_value", ascending=False)

    top_n = agg.head(n).reset_index(drop=True)
    bottom_n = agg.tail(n).sort_values("mean_value", ascending=True).reset_index(drop=True)

    return {"top": top_n, "bottom": bottom_n}


# ─────────────────────────────────────────────────────────────────────────────
# Time-Series Helpers
# ─────────────────────────────────────────────────────────────────────────────


def time_series_data(
    df: pd.DataFrame,
    iso3: str,
    indicator: str | None = None,
) -> pd.DataFrame:
    """
    Extract a country-level time series from the panel.

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel DataFrame.
    iso3 : str
        ISO3 country code (e.g. "USA", "IND", "BRA").
    indicator : str | None
        Indicator code to filter to.  If None, returns all indicators.

    Returns
    -------
    pd.DataFrame
        Columns: year, indicator_code, value.  Sorted by year ascending.
        Returns an empty DataFrame if the iso3 is not found.

    Example
    -------
    >>> ts = time_series_data(panel, "USA", "NY.GDP.PCAP.CD")
    >>> ts.plot(x="year", y="value")   # matplotlib plot
    """
    sub = df[df["country_iso3"] == iso3.upper()].copy()
    if indicator:
        sub = sub[sub["indicator_code"] == indicator]
    sub = sub.sort_values("year")
    return sub[["year", "indicator_code", "value"]].reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Full Auto-EDA Report
# ─────────────────────────────────────────────────────────────────────────────


def run_eda(path: Optional[Path | str] = None) -> dict[str, pd.DataFrame]:
    """
    Run a comprehensive auto-EDA report on the panel and print findings to stdout.

    This is the single-call convenience function that invokes all other EDA
    functions in sequence and prints their outputs.  Designed for rapid
    situational awareness and for use in Jupyter notebooks at the start of
    an analysis session.

    Parameters
    ----------
    path : Path | str | None
        Path to the panel CSV or Parquet file.  Passed to load_panel().
        Defaults to DEFAULT_PANEL_CSV.

    Returns
    -------
    dict[str, pd.DataFrame]
        A dictionary mapping function names to their returned DataFrames:
          "summary_stats", "missingness", "coverage_country", "coverage_year",
          "correlation", "distribution", "top_gdp", "bottom_gdp", ...

    Example
    -------
    >>> results = run_eda()
    >>> results["summary_stats"]      # access any table programmatically
    >>> results["correlation"]        # correlation matrix as a DataFrame
    """
    print("=" * 70)
    print("World Bank WDI — Exploratory Data Analysis Report")
    print("Author: Shankha Roy (Senior Data Engineer)  |  Version: 1.0.0")
    print("=" * 70)

    # ── Load ──────────────────────────────────────────────────────────────────
    print("\n[eda] Loading panel data ...")
    df = load_panel(path)
    n_countries = df["country_iso3"].nunique()
    n_years = df["year"].nunique()
    n_indicators = df["indicator_code"].nunique()
    print(f"[eda] Shape: {df.shape}  |  Countries: {n_countries}  |  "
          f"Years: {n_years}  |  Indicators: {n_indicators}")

    results: dict[str, pd.DataFrame] = {}

    # ── Summary Statistics ────────────────────────────────────────────────────
    print("\n[eda] 1/7 — Summary Statistics (per-indicator) ...")
    results["summary_stats"] = summary_stats(df)
    print(results["summary_stats"].to_string())

    # ── Missingness Report ────────────────────────────────────────────────────
    print("\n[eda] 2/7 — Missingness Report ...")
    results["missingness"] = missingness_report(df)
    print(results["missingness"].to_string())

    # ── Coverage by Country ───────────────────────────────────────────────────
    print("\n[eda] 3/7 — Coverage by Country (top 15 by observation count) ...")
    results["coverage_country"] = coverage_by_country(df)
    top_coverage = results["coverage_country"].head(15)
    print(top_coverage.to_string(index=False))

    # ── Coverage by Year ──────────────────────────────────────────────────────
    print("\n[eda] 4/7 — Coverage by Year (non-null observation count) ...")
    results["coverage_year"] = coverage_by_year(df)
    print(results["coverage_year"].to_string())

    # ── Indicator Correlation ─────────────────────────────────────────────────
    print("\n[eda] 5/7 — Indicator Correlation (Pearson, across country means) ...")
    results["correlation"] = indicator_correlation(df)
    print(results["correlation"].round(3).to_string())

    # ── Distribution Summary ───────────────────────────────────────────────────
    print("\n[eda] 6/7 — Distribution Summary ...")
    results["distribution"] = distribution_by_indicator(df)
    print(results["distribution"].to_string())

    # ── Top / Bottom Countries for GDP per capita ──────────────────────────────
    print("\n[eda] 7/7 — Top 10 / Bottom 10 Countries by GDP per capita ...")
    gdp_result = top_bottom(df, "NY.GDP.PCAP.CD", n=10)
    results["top_gdp"] = gdp_result["top"]
    results["bottom_gdp"] = gdp_result["bottom"]
    print("\n  TOP 10 (highest GDP per capita):")
    print(results["top_gdp"].to_string(index=False))
    print("\n  BOTTOM 10 (lowest GDP per capita):")
    print(results["bottom_gdp"].to_string(index=False))

    print("\n" + "=" * 70)
    print("EDA report complete.  Results dict is returned for programmatic access.")
    print("=" * 70)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Standalone Script Entry Point
# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Allow passing a custom path as the first command-line argument
    panel_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_eda(panel_path)

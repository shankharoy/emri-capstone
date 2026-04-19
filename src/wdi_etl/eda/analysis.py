"""
================================================================================
EDA Analysis — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy (Senior Data Engineer)
Version     : 1.0.0
Created     : 2026-04-11

Description :
    Exploratory Data Analysis functions for the tidy panel DataFrame.
================================================================================
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
# Libraries to help with data visualization
import matplotlib.pyplot as plt  # Plotting library
import seaborn as sns  # Statistical data visualization library
import numpy as np  # Numerical computing library
logger = logging.getLogger(__name__)

DEFAULT_PANEL_CSV: Path = (
    Path(__file__).parent.parent.parent / "data" / "output" / "wdi_panel.csv"
)

INDICATOR_LABELS: dict[str, str] = {
    "NY.GDP.PCAP.CD":   "GDP per capita (US$)",
    "IT.NET.USER.ZS":  "Internet users (%)",
    "SP.URB.TOTL.IN.ZS": "Urban population (%)",
    "SL.TLF.CACT.FE.ZS": "Female labour force participation (%)",
    "NY.GNP.PCAP.CD":   "GNI per capita, Atlas (US$)",
}


def load_panel(path: Optional[Path | str] = None) -> pd.DataFrame:
    """
    Load the tidy panel from CSV or Parquet.

    Parameters
    ----------
    path : Path | str | None
        File path. Auto-detects format from extension (.csv or .parquet).
        Defaults to DEFAULT_PANEL_CSV.

    Returns
    -------
    pd.DataFrame
        Columns: country_iso3, country_name, year, value, indicator_code.
    """
    if path is None:
        path = DEFAULT_PANEL_CSV
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Panel file not found: {path}. Run 'python -m wdi_etl' first."
        )

    df = pd.read_csv(path) if path.suffix == ".csv" else pd.read_parquet(path)
    logger.debug("load_panel: loaded %s (%s)", path, df.shape)
    return df


def summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Descriptive statistics for each indicator using raw (non-pivoted) values.

    Computes: count, mean, std, min, 25%, 50%, 75%, max, null count.

    Returns
    -------
    pd.DataFrame indexed by indicator_code.
    """
    from wdi_etl.core.config import YEAR_END, YEAR_START

    n_countries = df["country_iso3"].nunique()
    n_years = df["year"].nunique()
    total_cells = n_countries * n_years

    rows = []
    for code in df["indicator_code"].unique():
        series = df.loc[df["indicator_code"] == code, "value"]
        desc = series.describe()
        rows.append({
            "indicator_code": code,
            "n_obs": int(desc["count"]),
            "mean": round(desc["mean"], 2),
            "std": round(desc["std"], 2),
            "min": round(desc["min"], 2),
            "q25": round(desc["25%"], 2),
            "median": round(desc["50%"], 2),
            "q75": round(desc["75%"], 2),
            "max": round(desc["max"], 2),
            "null": total_cells - int(desc["count"]),
        })

    return (
        pd.DataFrame(rows)
        .set_index("indicator_code")
        .loc[df["indicator_code"].unique()]
    )


def missingness_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-indicator missing-value ratios."""
    n_countries = df["country_iso3"].nunique()
    n_years = df["year"].nunique()
    total_cells = n_countries * n_years

    rows = []
    for code in df["indicator_code"].unique():
        sub = df[df["indicator_code"] == code]
        non_null = sub["value"].notna().sum()
        null_count = total_cells - non_null
        rows.append({
            "indicator_code": code,
            "total_cells": total_cells,
            "non_null": non_null,
            "null_count": null_count,
            "missing_ratio": round(null_count / total_cells, 4) if total_cells else 0.0,
        })

    result = pd.DataFrame(rows).set_index("indicator_code")
    result.sort_values("missing_ratio", ascending=False, inplace=True)
    return result


def missingness_heatmap_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Country x (Indicator x Year) presence matrix (1=present, 0=missing).
    Suitable for rendering as a heatmap.
    """
    df = df.copy()
    df["present"] = df["value"].notna().astype(int)
    return (
        df.pivot_table(
            index="country_iso3",
            columns=["indicator_code", "year"],
            values="present",
            aggfunc="max",
        )
        .fillna(0)
        .astype(int)
    )



def labeled_barplot(data, feature, perc=False, n=None):
    """
    Creates a labeled bar plot with counts or percentages.

    Parameters:
    - data (DataFrame): The dataset.
    - feature (str): Column name to be plotted.
    - perc (bool, optional): Whether to display percentages instead of counts (default is False).
    - n (int, optional): Number of top categories to display (default is None, meaning all categories).
    """

    # Count the total occurrences of the feature
    total = len(data[feature])

    # Get the unique category count for the feature
    unique_categories = data[feature].nunique()

    # Set figure size based on number of categories or specified 'n'
    plt.figure(figsize=(min(n or unique_categories, unique_categories) + 1, 5))

    # Set x-axis label rotation and font size
    plt.xticks(rotation=90, fontsize=12)

    # Create a bar plot sorted by category frequency
    ax = sns.countplot(
        data=data,
        x=feature,
        palette="Paired",
        order=data[feature].value_counts().index[:n]  # Select top 'n' categories if specified
    )

    # Annotate each bar with count or percentage
    for p in ax.patches:
        height = p.get_height()  # Bar height (count value)

        # Determine label format: percentage or count
        label = f"{height:.1f}%" if perc else f"{height}"

        # Get bar center position for annotation
        x = p.get_x() + p.get_width() / 2
        y = height

        # Add annotation above each bar
        ax.annotate(
            label,
            (x, y),
            ha="center",  # Horizontal alignment
            va="bottom",  # Vertical alignment
            fontsize=12,
            xytext=(0, 5),  # Offset annotation slightly above the bar
            textcoords="offset points"
        )

    # Display the plot
    plt.show()



def analyze_column(dataframe, col_names):
    """
    Analyze the statistical properties and visualizations of columns in a DataFrame.

    Args:
        dataframe (pd.DataFrame): The DataFrame containing the dataset.
        col_names (list): A list of column names to analyze.

    Returns:
        None: This function prints the analysis results and displays visualizations.
    """
    for i, col_val in enumerate(col_names):
        print("----------------------------------------------------")
        print("Five number summary of '{}' variable ".format(col_val))
        print("----------------------------------------------------")
        print(dataframe[col_val].describe())
        print("")
        print("----------------------------------------------------")
        print("The Measures of Dispersion of varibale '{}' ".format(col_val))
        print("----------------------------------------------------")
        print("Range is ", dataframe[col_val].max() - dataframe[col_val].min())
        print("Variance is ", dataframe[col_val].var())
        Q1 = dataframe[col_val].quantile(0.25)
        Q3 = dataframe[col_val].quantile(0.75)
        IQR = Q3 - Q1
        print("IQR value is ", IQR)
        print("Count of outlier observations is ", np.count_nonzero((dataframe[col_val] < (Q1 - 1.5 * IQR)) | (dataframe[col_val] > (Q3 + 1.5 * IQR))))
        print('Number of duplicate rows is %d' % (dataframe[col_val].duplicated().sum()))
        print("----------------------------------------------------")
        print("Measure skewness of '{}' is ".format(col_val), dataframe[col_val].skew())
        # If Mode < Median < Mean then the distribution is positively skewed.
        # If Mode > Median > Mean then the distribution is negatively skewed.
        if (dataframe[col_val].mode()[0] < dataframe[col_val].median()) and (dataframe[col_val].median() < dataframe[col_val].mean()):
            print("{} the distribution is positively skewed".format(col_val))
        elif (dataframe[col_val].mode()[0] > dataframe[col_val].median()) and (dataframe[col_val].median() > dataframe[col_val].mean()):
            print("{} the distribution is negatively skewed".format(col_val))
        else:
            print("{} the distribution is normal".format(col_val))
        print("----------------------------------------------------")
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(2, 2, 1)
        sns.boxplot(x=dataframe[col_val])
        ax.set_title('Box plot - {}'.format(col_names[i]), fontsize=14)
        ax = fig.add_subplot(2, 2, 2)
        sns.distplot(dataframe[col_val], hist=True)
        ax.set_title('Freq dist ' + col_val, fontsize=12)
        ax.set_xlabel(col_val, fontsize=10)
        ax.set_ylabel('Count', fontsize=10)
        plt.show()
        print("----------------------------------------------------")

        print("")
        print("")

def coverage_by_country(df: pd.DataFrame, min_years: int = 5) -> pd.DataFrame:
    """
    Per-country completeness: n_indicators, n_years, n_total_obs, is_well_covered.
    """
    rows = []
    for iso3, grp in df.groupby("country_iso3"):
        rows.append({
            "country_iso3": iso3,
            "country_name": grp["country_name"].iloc[0],
            "n_indicators_with_data": grp["indicator_code"].nunique(),
            "n_years_with_data": grp["year"].nunique(),
            "n_total_obs": grp["value"].notna().sum(),
            "is_well_covered": grp["value"].notna().sum() >= min_years * grp["indicator_code"].nunique(),
        })

    result = pd.DataFrame(rows).sort_values("n_total_obs", ascending=False)
    return result.reset_index(drop=True)


def coverage_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Per-year non-null observation counts per indicator."""
    pivoted = (
        df.pivot_table(
            index="year",
            columns="indicator_code",
            values="value",
            aggfunc="count",
        )
        .fillna(0)
        .astype(int)
    )
    pivoted["total_indicators_reported"] = (pivoted > 0).sum(axis=1)
    return pivoted


def indicator_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pairwise Pearson correlation of indicator means across countries.

    Each country contributes its mean value per indicator (averaged over years).
    """
    country_means = df.pivot_table(
        index="country_iso3",
        columns="indicator_code",
        values="value",
        aggfunc="mean",
    )
    return country_means.corr(method="pearson").round(4)


def distribution_by_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """Per-indicator distribution metrics: skewness, kurtosis, IQR, CV."""
    rows = []
    for code, grp in df.groupby("indicator_code"):
        series = grp["value"].dropna()
        if len(series) < 3:
            continue
        mean_val, std_val = series.mean(), series.std()
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        rows.append({
            "indicator_code": code,
            "n": len(series),
            "mean": round(mean_val, 2),
            "std": round(std_val, 2),
            "cv": round(std_val / mean_val, 4) if mean_val else float("nan"),
            "min": round(series.min(), 2),
            "q25": round(q1, 2),
            "median": round(series.median(), 2),
            "q75": round(q3, 2),
            "max": round(series.max(), 2),
            "iqr": round(q3 - q1, 2),
            "skewness": round(float(series.skew()), 4),
            "kurtosis": round(float(series.kurtosis()), 4),
        })

    result = pd.DataFrame(rows).set_index("indicator_code")
    result.sort_values("mean", ascending=False, inplace=True)
    return result


def top_bottom(
    df: pd.DataFrame,
    indicator: str,
    n: int = 10,
    year_range: tuple[int, int] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Top-N and bottom-N countries ranked by mean value of the given indicator.

    Returns dict with keys "top" and "bottom", each a DataFrame with columns:
    country_iso3, country_name, mean_value, n_years, first_year, last_year.
    """
    if indicator not in df["indicator_code"].values:
        raise ValueError(f"Indicator '{indicator}' not found.")

    sub = df[df["indicator_code"] == indicator].copy()
    if year_range:
        sub = sub[(sub["year"] >= year_range[0]) & (sub["year"] <= year_range[1])]

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
    bottom_n = (
        agg.tail(n)
        .sort_values("mean_value", ascending=True)
        .reset_index(drop=True)
    )
    return {"top": top_n, "bottom": bottom_n}


def time_series_data(
    df: pd.DataFrame,
    iso3: str,
    indicator: str | None = None,
) -> pd.DataFrame:
    """Extract country-level time series for plotting."""
    sub = df[df["country_iso3"] == iso3.upper()].copy()
    if indicator:
        sub = sub[sub["indicator_code"] == indicator]
    sub = sub.sort_values("year")
    return sub[["year", "indicator_code", "value"]].reset_index(drop=True)


def run_eda(path: Optional[Path | str] = None) -> dict[str, pd.DataFrame]:
    """
    Run the complete EDA report and return a dict of result DataFrames.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys: summary_stats, missingness, coverage_country, coverage_year,
        correlation, distribution, top_gdp, bottom_gdp.
    """
    from wdi_etl.utils.logging_config import setup_logging
    setup_logging(level="INFO")

    print("=" * 70)
    print("World Bank WDI — Exploratory Data Analysis Report")
    print("Author: Shankha Roy (Senior Data Engineer)  |  Version: 1.0.0")
    print("=" * 70)

    print("\n[eda] Loading panel data ...")
    df = load_panel(path)
    print(f"[eda] Shape: {df.shape}  |  Countries: {df['country_iso3'].nunique()}  |  "
          f"Years: {df['year'].nunique()}  |  Indicators: {df['indicator_code'].nunique()}")

    results: dict[str, pd.DataFrame] = {}

    print("\n[eda] 1/7 — Summary Statistics ...")
    results["summary_stats"] = summary_stats(df)
    print(results["summary_stats"].to_string())

    print("\n[eda] 2/7 — Missingness Report ...")
    results["missingness"] = missingness_report(df)
    print(results["missingness"].to_string())

    print("\n[eda] 3/7 — Coverage by Country (top 15) ...")
    results["coverage_country"] = coverage_by_country(df)
    print(results["coverage_country"].head(15).to_string(index=False))

    print("\n[eda] 4/7 — Coverage by Year ...")
    results["coverage_year"] = coverage_by_year(df)
    print(results["coverage_year"].to_string())

    print("\n[eda] 5/7 — Indicator Correlation ...")
    results["correlation"] = indicator_correlation(df)
    print(results["correlation"].round(3).to_string())

    print("\n[eda] 6/7 — Distribution Summary ...")
    results["distribution"] = distribution_by_indicator(df)
    print(results["distribution"].to_string())

    print("\n[eda] 7/7 — Top 10 / Bottom 10 by GDP per capita ...")
    gdp_result = top_bottom(df, "NY.GDP.PCAP.CD", n=10)
    results["top_gdp"] = gdp_result["top"]
    results["bottom_gdp"] = gdp_result["bottom"]
    print("\n  TOP 10:")
    print(results["top_gdp"].to_string(index=False))
    print("\n  BOTTOM 10:")
    print(results["bottom_gdp"].to_string(index=False))

    print("\n" + "=" * 70)
    print("EDA report complete.")
    print("=" * 70)
    return results


if __name__ == "__main__":
    import sys
    panel_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_eda(panel_path)

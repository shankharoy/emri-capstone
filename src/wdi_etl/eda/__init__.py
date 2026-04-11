"""
EDA Module — Exploratory Data Analysis
"""
from wdi_etl.eda.analysis import (
    coverage_by_country,
    coverage_by_year,
    distribution_by_indicator,
    indicator_correlation,
    load_panel,
    missingness_heatmap_data,
    missingness_report,
    run_eda,
    summary_stats,
    time_series_data,
    top_bottom,
)

__all__ = [
    "load_panel",
    "summary_stats",
    "missingness_report",
    "missingness_heatmap_data",
    "coverage_by_country",
    "coverage_by_year",
    "indicator_correlation",
    "distribution_by_indicator",
    "top_bottom",
    "time_series_data",
    "run_eda",
]

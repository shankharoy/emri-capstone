"""
================================================================================
World Bank WDI ETL Pipeline — Package Root
================================================================================
Author      : Shankha Roy 
Version     : 1.0.0
Created     : 2026-04-11

Package Structure
----------------
    wdi_etl/
        __init__.py      — this file; exposes public API
        config.py        — all pipeline configuration constants
        extract.py       — Extract stage (World Bank API)
        transform.py     — Transform stage (clean, merge, validate)
        load.py          — Load stage (CSV + Parquet output)
        __main__.py      — CLI entry point (python -m wdi_etl)

Public API
----------
    from wdi_etl import extract_all, transform_all, load_panel

    raw_data = extract_all()           # fetch from World Bank API
    panel    = transform_all(raw_data) # clean, merge, validate
    outputs  = load_panel(panel)      # write CSV + Parquet

Design Philosophy
----------------
    This pipeline follows the ETL pattern common in data engineering:
      Extract  — pull raw data from external sources (World Bank API)
      Transform — clean, validate, and reshape into analysis-ready form
      Load     — persist the final dataset to storage

    The three stages are strictly ordered and each is implemented in its own
    module.  This separation:
      - Makes unit testing straightforward (mock one stage to test another)
      - Allows selective re-runs (--skip-extract uses cached raw data)
      - Prevents business logic from leaking across stage boundaries

Quick Start
-----------
    # Full pipeline run
    python -m wdi_etl

    # Re-run without re-downloading
    python -m wdi_etl --skip-extract

    # Use forward-fill for missing values
    python -m wdi_etl --missing-strategy forward_fill

    # Show all CLI options
    python -m wdi_etl --help
================================================================================
"""

from wdi_etl.extract import extract_all
from wdi_etl.load import load_panel
from wdi_etl.transform import transform_all

__all__ = ["extract_all", "transform_all", "load_panel"]
__author__ = "Shankha Roy"
__version__ = "1.0.0"

"""
World Bank WDI ETL Pipeline — Production Package
Author : Shankha Roy (Senior Data Engineer)
Version : 1.0.0

Public API
----------
    from wdi_etl import extract_all, transform_all, load_panel

Quick Start
-----------
    # Full pipeline run
    python -m wdi_etl

    # Re-run without re-downloading
    python -m wdi_etl --skip-extract

    # Run EDA
    python -m wdi_etl.eda
"""

from wdi_etl.api.client import extract_all
from wdi_etl.core.load import load_panel
from wdi_etl.core.transform import transform_all

__all__ = ["extract_all", "transform_all", "load_panel"]
__author__ = "Shankha Roy"
__version__ = "1.0.0"

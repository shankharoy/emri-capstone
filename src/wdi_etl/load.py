"""
================================================================================
Load Stage — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy (Senior Data Engineer)
Version     : 1.0.0
Created     : 2026-04-11

Description :
    Responsible for the Load phase. Persists the validated panel DataFrame to
    CSV and Parquet formats with full dtype preservation.

Output Formats
--------------
    CSV    : UTF-8 with BOM — correct Unicode in Microsoft Excel on Windows
    Parquet: Columnar binary, Snappy compression (PyArrow default),
             dtype-preserving (year stays int64, not object)

Design Decisions
---------------
    1. UTF-8-BOM on CSV — Windows Excel misinterprets UTF-8 without BOM
    2. Output dir auto-creation — prevents FileNotFoundError
    3. Path flexibility — accepts Path, str, or None (uses config default)
================================================================================
"""

import logging
from pathlib import Path

import pandas as pd

from wdi_etl.config import OUTPUT_CSV, OUTPUT_DIR, OUTPUT_PARQUET

logger = logging.getLogger(__name__)


def load_panel(
    df: pd.DataFrame,
    csv_path: Path | str | None = None,
    parquet_path: Path | str | None = None,
    partition_by: str | None = None,
) -> dict[str, Path]:
    """
    Write the validated panel DataFrame to disk.

    Parameters
    ----------
    df : pd.DataFrame
        Tidy panel with columns: country_iso3, country_name, year, value, indicator_code.
    csv_path : Path | str | None
        CSV destination. Defaults to config.OUTPUT_CSV.
    parquet_path : Path | str | None
        Parquet destination. Defaults to config.OUTPUT_PARQUET.
    partition_by : str | None
        If set, writes a partitioned Parquet dataset (one file per unique value
        in this column). Recommended for panels > 100 MB.

    Returns
    -------
    dict[str, Path]
        Mapping from format name to output Path.
    """
    csv_path = Path(csv_path) if csv_path else OUTPUT_CSV
    parquet_path = Path(parquet_path) if parquet_path else OUTPUT_PARQUET

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    # ── CSV ────────────────────────────────────────────────────────────────
    # UTF-8 with BOM (utf-8-sig) ensures correct Unicode rendering in Excel on Windows
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    outputs["csv"] = csv_path
    size_kb = csv_path.stat().st_size / 1024
    logger.info("Wrote CSV: %s (%.1f KB)", csv_path, size_kb)

    # ── Parquet ────────────────────────────────────────────────────────────
    if parquet_path:
        if partition_by and partition_by in df.columns:
            parquet_path.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path=parquet_path, partition_cols=[partition_by], engine="pyarrow")
        elif partition_by:
            raise ValueError(f"partition_by='{partition_by}' not in DataFrame columns")
        else:
            df.to_parquet(path=parquet_path, index=False, engine="pyarrow")

        outputs["parquet"] = parquet_path
        logger.info("Wrote Parquet: %s", parquet_path)

    return outputs

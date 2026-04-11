"""
================================================================================
Load Stage — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy
Version     : 1.0.0
Created     : 2026-04-11
Description :
    Responsible for the Load phase of the ETL pipeline.  Accepts the validated
    tidy panel DataFrame from the transform stage and persists it to the
    configured storage formats.

    Two output formats are produced:
      1. CSV  — Human-readable, universally interoperable, suitable for sharing
                 and archival.  Written with UTF-8-BOM encoding to ensure correct
                 Unicode rendering in Microsoft Excel on Windows.
      2. Parquet — Columnar, compressed binary format optimised for analytical
                 workloads.  Preserves dtype information (year stays int64, not
                 object) and offers significant I/O speedups for large datasets.

    Both formats are written in a single call, ensuring they are always in sync.

Design Decisions
----------------
    1. Parquet-first for analytics — Parquet is the preferred format for any
          downstream Python/Spark analytics workload.  CSV is a secondary output
          for interoperability.
    2. UTF-8-BOM on CSV           — Windows Excel misinterprets UTF-8 CSV files
          without a BOM, showing garbled characters for non-ASCII names.
          The BOM is a 3-byte prefix that tells Windows apps the file is UTF-8.
    3. Output directory auto-creation — OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
          is called before any write, preventing FileNotFoundError if the
          directory has not been created manually.
    4. Path flexibility            — Both csv_path and parquet_path accept Path,
          str, or None (None resolves to config defaults), making the function
          usable both in the orchestrator and in ad-hoc scripts.

Partitioned Parquet
--------------------
    When ``partition_by`` is specified (e.g. "year"), PyArrow writes a
    partitioned Parquet dataset — a directory tree where each partition
    (year) is a separate Parquet file.  This dramatically improves query
    performance for workloads that filter by the partition column (e.g.
    reading only 2023 data).  Set partition_by=None for a single file output.
================================================================================
"""

from pathlib import Path

import pandas as pd

from wdi_etl.config import OUTPUT_CSV, OUTPUT_DIR, OUTPUT_PARQUET


def load_panel(
    df: pd.DataFrame,
    csv_path: Path | str | None = None,
    parquet_path: Path | str | None = None,
    partition_by: str | None = None,
) -> dict[str, Path]:
    """
    Write the validated panel DataFrame to disk in all configured formats.

    Parameters
    ----------
    df : pd.DataFrame
        The validated tidy panel DataFrame from the transform stage.
        Expected columns: country_iso3, country_name, year, value, indicator_code.
    csv_path : Path | str | None, default None
        Destination path for the CSV file.  If None, resolves to
        config.OUTPUT_CSV.
    parquet_path : Path | str | None, default None
        Destination path for the Parquet file.  If None, resolves to
        config.OUTPUT_PARQUET.
    partition_by : str | None, default None
        If set to a column name (e.g. "year"), writes a partitioned Parquet
        dataset (one file per partition value).  If None, writes a single
        Parquet file.  Partitioning is recommended when the panel exceeds
        100 MB or when downstream queries almost always filter on the
        partition column.

    Returns
    -------
    dict[str, Path]
        Mapping from format name ("csv", "parquet") to the Path where that
        file was written.  Both keys are always present in the returned dict
        regardless of whether the format was explicitly enabled.

    Raises
    ------
    OSError
        Propagated from file I/O operations if directories cannot be created
        or files cannot be written.
    ValueError
        If ``partition_by`` is set to a column name that does not exist in ``df``.

    Output Format Details
    --------------------
    CSV:
        - Encoding    : UTF-8 with BOM (utf-8-sig) — required for correct Unicode
                       rendering in Microsoft Excel on Windows
        - Index      : False — row number is not meaningful in panel data
        - Separator  : comma (default for .csv)

    Parquet:
        - Engine     : pyarrow — the reference implementation, no extra install
        - Compression: Snappy (PyArrow default) — fast decompression for
                       analytical queries
        - Dtype preservation: year is int64, value is float64 — no conversion
                              to object dtype as can happen with CSV round-trips

    Example
    -------
    >>> outputs = load_panel(panel, partition_by="year")
    >>> outputs["csv"]
    WindowsPath('data/output/wdi_panel.csv')
    """
    # Resolve paths to absolute Path objects
    csv_path = Path(csv_path) if csv_path else OUTPUT_CSV
    parquet_path = Path(parquet_path) if parquet_path else OUTPUT_PARQUET

    # Ensure output directory exists before writing any file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}

    # ── Write CSV ───────────────────────────────────────────────────────────────
    #
    # utf-8-sig encoding prepends a UTF-8 BOM (0xEF 0xBB 0xBF) which signals to
    # Windows applications (Excel, Notepad) that the file is UTF-8 encoded.
    # Without the BOM, Windows defaults to the system ANSI codepage (e.g. CP1252)
    # resulting in garbled characters for accented country names like Côte d'Ivoire.
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    outputs["csv"] = csv_path

    csv_size_kb: float = csv_path.stat().st_size / 1024
    print(f"[load] Wrote CSV: {csv_path}  ({csv_size_kb:.1f} KB)")

    # ── Write Parquet ───────────────────────────────────────────────────────────
    if parquet_path:
        if partition_by and partition_by in df.columns:
            # Partitioned write: creates a directory tree, one file per partition value.
            # e.g.  parquet/wdi_panel/year=2014/part.0.parquet
            parquet_path.mkdir(parents=True, exist_ok=True)
            df.to_parquet(
                path=parquet_path,
                partition_cols=[partition_by],
                engine="pyarrow",
            )
        elif partition_by and partition_by not in df.columns:
            # Validate partition column before writing
            raise ValueError(
                f"partition_by='{partition_by}' but column not in DataFrame. "
                f"Available columns: {df.columns.tolist()}"
            )
        else:
            # Single-file Parquet: one .parquet file with all rows
            df.to_parquet(
                path=parquet_path,
                index=False,
                engine="pyarrow",
            )

        outputs["parquet"] = parquet_path
        print(f"[load] Wrote Parquet: {parquet_path}")

    return outputs

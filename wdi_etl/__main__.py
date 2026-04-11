"""
================================================================================
Pipeline Orchestrator — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy
Version     : 1.0.0
Created     : 2026-04-11
Description :
    Entry point for the World Bank WDI ETL pipeline.  Orchestrates the three
    stages (Extract → Transform → Load) and exposes runtime behaviour through
    command-line flags.

    This module intentionally contains no business logic — it is a pure
    coordinator that:
      1. Parses CLI arguments
      2. Calls extract_all() or loads cached raw files
      3. Calls transform_all()
      4. Calls load_panel()
      5. Reports timing and output paths

Usage
-----
    # Full run (extract + transform + load)
    python -m wdi_etl

    # Re-run without re-downloading (uses cached raw JSON)
    python -m wdi_etl --skip-extract

    # Use forward-fill for missing values
    python -m wdi_etl --missing-strategy forward_fill

    # Partition Parquet output by year (recommended for large panels)
    python -m wdi_etl --partition-by year

    # Show all options
    python -m wdi_etl --help

CLI Arguments
-------------
    --missing-strategy  : Strategy for NaN values (drop|forward_fill|
                         backward_fill|interpolate|keep)
    --skip-extract     : Skip API calls; reload from cached raw JSON
    --raw-dir          : Custom directory for raw JSON cache
    --interim-dir      : Custom directory for intermediate files
    --output-dir       : Custom directory for final output
    --partition-by     : Column name to partition Parquet output on (e.g. year)
    --skip-parquet     : Only write CSV output

Exit Codes
----------
    0 : Pipeline completed successfully (transform may have issued warnings)
    1 : Pipeline failed due to a caught exception (API error, validation error,
        I/O error, etc.)

Architecture Note
----------------
    This orchestrator is intentionally simple.  For production deployments
    that require scheduling, alerting, and retry logic, consider replacing
    this with:
      - Apache Airflow  : workflow orchestration with retry/DAG features
      - Prefect        : modern Python-native alternative to Airflow
      - dagster        : great for data-centric pipelines with asset versioning
    The modular design (extract/transform/load as separate functions) makes
    this substitution straightforward.
================================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from wdi_etl.config import (
    INTERIM_DIR,
    MISSING_STRATEGY,
    OUTPUT_DIR,
    RAW_DIR,
)
from wdi_etl.extract import extract_all
from wdi_etl.load import load_panel
from wdi_etl.transform import transform_all


# ── CLI Argument Parser ─────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    """
    Build and return the CLI argument parser with all pipeline options.

    Returns
    -------
    argparse.Namespace
        Parsed arguments accessible as attributes (e.g. args.missing_strategy).
    """
    parser = argparse.ArgumentParser(
        prog="python -m wdi_etl",
        description="World Bank WDI ETL pipeline (2014-2023) — Author: Shankha Roy",
        # RawDescriptionHelpFormatter preserves the formatting in the epilog below
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m wdi_etl\n"
            "  python -m wdi_etl --skip-extract\n"
            "  python -m wdi_etl --missing-strategy forward_fill --partition-by year\n"
        ),
    )

    parser.add_argument(
        "--missing-strategy",
        type=str,
        default=MISSING_STRATEGY,
        choices={"drop", "forward_fill", "backward_fill", "interpolate", "keep"},
        help=(
            "Strategy for handling missing values in the panel. "
            f"Default: '{MISSING_STRATEGY}' (from config)."
        ),
    )

    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help=(
            "Skip the Extract stage and reload raw JSON from --raw-dir. "
            "Use this to re-run the transform/load stages without re-fetching "
            "data from the World Bank API."
        ),
    )

    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help=f"Directory containing cached raw JSON files. Default: {RAW_DIR}",
    )

    parser.add_argument(
        "--interim-dir",
        type=Path,
        default=INTERIM_DIR,
        help=f"Directory for intermediate artefacts. Default: {INTERIM_DIR}",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Directory for final output files. Default: {OUTPUT_DIR}",
    )

    parser.add_argument(
        "--partition-by",
        type=str,
        default=None,
        help=(
            "Column name to partition the Parquet output on (e.g. 'year'). "
            "Creates a directory tree with one Parquet file per partition value. "
            "Recommended for panels > 100 MB or workloads that filter by year."
        ),
    )

    parser.add_argument(
        "--skip-parquet",
        action="store_true",
        help="Skip Parquet output; write only the CSV file.",
    )

    return parser.parse_args()


# ── Pipeline Runner ─────────────────────────────────────────────────────────────


def run() -> None:
    """
    Execute the full Extract → Transform → Load pipeline.

    Steps
    -----
        1. Parse CLI arguments and print pipeline configuration header.
        2a. If --skip-extract: load raw JSON from --raw-dir (disk cache).
        2b. Otherwise: call extract_all() to fetch from World Bank API.
        3. Call transform_all() to clean, merge, and validate the panel.
        4. Call load_panel() to write CSV and Parquet outputs.
        5. Print elapsed time and output file paths.

    Error Handling
    -------------
        All exceptions are caught, printed to stderr, and cause sys.exit(1).
        This ensures the CI/CD shell receives a non-zero exit code on failure.
    """
    t0 = time.monotonic()
    args = parse_args()

    # Print pipeline configuration header
    print("=" * 60)
    print("World Bank WDI ETL Pipeline")
    print("Author: Shankha Roy (Senior Data Engineer)")
    print("=" * 60)
    print(f"Missing strategy : {args.missing_strategy}")
    print(f"Raw dir         : {args.raw_dir}")
    print(f"Interim dir     : {args.interim_dir}")
    print(f"Output dir      : {args.output_dir}")
    print(f"Partition by    : {args.partition_by or 'None (single file)'}")
    print("-" * 60)

    # ── Stage 1: Extract ────────────────────────────────────────────────────
    if args.skip_extract:
        # Reload from disk cache — skip API calls entirely
        print(
            "[orchestrator] --skip-extract set: loading raw JSON from disk cache ..."
        )
        raw_data: dict[str, list[dict]] = {}
        json_files = sorted(args.raw_dir.glob("*.json"))

        if not json_files:
            raise FileNotFoundError(
                f"No JSON files found in {args.raw_dir}. "
                "Run without --skip-extract to download fresh data."
            )

        for json_file in json_files:
            with open(json_file, encoding="utf-8") as f:
                raw_data[json_file.stem] = json.load(f)

        print(
            f"[orchestrator] Loaded {len(raw_data)} cached indicator files "
            f"from {args.raw_dir}"
        )
    else:
        # Full extraction from World Bank API
        raw_data = extract_all(raw_dir=args.raw_dir)

    # ── Stage 2: Transform ────────────────────────────────────────────────────
    panel = transform_all(raw_data, missing_strategy=args.missing_strategy)

    # ── Stage 3: Load ───────────────────────────────────────────────────────
    parquet_path_arg: Path | None = None if args.skip_parquet else None
    outputs = load_panel(
        panel,
        parquet_path=parquet_path_arg,
        partition_by=args.partition_by,
    )

    # ── Summary ──────────────────────────────────────────────────────────────
    elapsed_s: float = time.monotonic() - t0
    print("-" * 60)
    print(f"Done.  Panel shape: {panel.shape}")
    print(f"Elapsed time      : {elapsed_s:.1f}s")
    print(f"Output files      : {list(outputs.values())}")


# ── Entry Point ─────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # pragma: no cover — defensive; real errors are in functions
        print(f"[ERROR] Pipeline failed: {exc}", file=sys.stderr)
        sys.exit(1)

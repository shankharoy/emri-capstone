"""
================================================================================
Orchestrator — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy (Senior Data Engineer)
Version     : 1.0.0
Created     : 2026-04-11

Usage
-----
    python -m wdi_etl                  # full run
    python -m wdi_etl --skip-extract   # use cached raw JSON
    python -m wdi_etl --help           # show all options
================================================================================
"""

from __future__ import annotations

import argparse
import json
import logging
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
from wdi_etl.logger import setup_logging
from wdi_etl.transform import transform_all

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m wdi_etl",
        description="World Bank WDI ETL pipeline (2014-2023) — Author: Shankha Roy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--missing-strategy", type=str,
        default=MISSING_STRATEGY,
        choices={"drop", "forward_fill", "backward_fill", "interpolate", "keep"},
        help=f"Missing-value strategy. Default: '{MISSING_STRATEGY}'",
    )
    parser.add_argument(
        "--skip-extract", action="store_true",
        help="Skip API calls; reload from cached raw JSON.",
    )
    parser.add_argument(
        "--raw-dir", type=Path, default=RAW_DIR,
        help=f"Raw JSON cache directory. Default: {RAW_DIR}",
    )
    parser.add_argument(
        "--interim-dir", type=Path, default=INTERIM_DIR,
        help=f"Intermediate artefacts directory. Default: {INTERIM_DIR}",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=OUTPUT_DIR,
        help=f"Output directory. Default: {OUTPUT_DIR}",
    )
    parser.add_argument(
        "--partition-by", type=str, default=None,
        help="Column name to partition Parquet output on (e.g. 'year').",
    )
    parser.add_argument(
        "--skip-parquet", action="store_true",
        help="Skip Parquet output; write CSV only.",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices={"DEBUG", "INFO", "WARNING", "ERROR"},
        help="Console log level. Default: INFO.",
    )
    return parser.parse_args()


def run() -> None:
    t0 = time.monotonic()
    args = parse_args()
    setup_logging(level=args.log_level)

    logger.info("=" * 60)
    logger.info("World Bank WDI ETL Pipeline — Shankha Roy")
    logger.info("=" * 60)

    # ── Stage 1: Extract ───────────────────────────────────────────────
    if args.skip_extract:
        logger.info("Loading cached raw JSON from %s", args.raw_dir)
        raw_data: dict = {}
        json_files = sorted(args.raw_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(
                f"No JSON files in {args.raw_dir}. Run without --skip-extract."
            )
        for json_file in json_files:
            with open(json_file, encoding="utf-8") as f:
                raw_data[json_file.stem] = json.load(f)
        logger.info("Loaded %d cached indicator files", len(raw_data))
    else:
        raw_data = extract_all(raw_dir=args.raw_dir)

    # ── Stage 2: Transform ────────────────────────────────────────────
    panel = transform_all(raw_data, missing_strategy=args.missing_strategy)

    # ── Stage 3: Load ────────────────────────────────────────────────
    parquet_path: Path | None = None if args.skip_parquet else None
    outputs = load_panel(panel, parquet_path=parquet_path,
                         partition_by=args.partition_by)

    elapsed = time.monotonic() - t0
    logger.info("Done. Shape: %s | Elapsed: %.1fs", panel.shape, elapsed)
    logger.info("Outputs: %s", list(outputs.values()))


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        sys.exit(1)

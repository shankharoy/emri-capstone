"""
================================================================================
Logging Configuration — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy (Senior Data Engineer)
Version     : 1.0.0
Created     : 2026-04-11

Description :
    Centralised logging setup for the pipeline.  Produces both a timed
    rotating log file (for audit trails) and a stream handler (console).

    The rotating file handler keeps the last LOG_MAX_BYTES of log entries
    per file, with up to LOG_BACKUP_COUNT backup files retained.

Usage
-----
    from wdi_etl.logger import setup_logging
    setup_logging()
    logger = logging.getLogger(__name__)
================================================================================
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from wdi_etl.config import LOG_DIR, LOG_FILE, LOG_LEVEL


def setup_logging(level: str | None = None) -> None:
    """
    Configure logging with both file (rotating) and console handlers.

    Parameters
    ----------
    level : str | None
        Log level as string (DEBUG, INFO, WARNING, ERROR).  Defaults to
        the value of config.LOG_LEVEL.
    """
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    _level = getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO)

    # ── Formatters ─────────────────────────────────────────────────────────────
    FILE_FORMAT = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    CONSOLE_FORMAT = logging.Formatter(
        "[%(levelname)s] %(message)s"
    )

    # ── Rotating file handler (audit trail) ───────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=10 * 1024 * 1024,   # 10 MB per file
        backupCount=5,                # keep last 5 files
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(FILE_FORMAT)

    # ── Console handler (stdout for --verbose) ────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_level)
    console_handler.setFormatter(CONSOLE_FORMAT)

    # ── Root logger ──────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # capture DEBUG in file; console filters by level
    root.addHandler(file_handler)
    root.addHandler(console_handler)

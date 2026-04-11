"""
Unit tests for logging configuration.
Author: Shankha Roy (Senior Data Engineer)
"""
import logging
import tempfile
from pathlib import Path

import pytest

from wdi_etl.logger import setup_logging


class TestSetupLogging:
    """Test logging setup functionality."""

    def test_configures_root_logger(self):
        """Should configure root logger."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.log"

            # Temporarily patch LOG_FILE in config
            import wdi_etl.config
            original_log_file = wdi_etl.config.LOG_FILE
            wdi_etl.config.LOG_FILE = log_file

            try:
                setup_logging(level="DEBUG")
                root_logger = logging.getLogger()
                assert len(root_logger.handlers) >= 2  # File + console
            finally:
                wdi_etl.config.LOG_FILE = original_log_file

    def test_creates_log_directory(self):
        """Should create log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "new_logs"
            log_file = log_dir / "test.log"

            import wdi_etl.config
            original_log_file = wdi_etl.config.LOG_FILE
            wdi_etl.config.LOG_FILE = log_file

            try:
                setup_logging()
                assert log_dir.exists()
            finally:
                wdi_etl.config.LOG_FILE = original_log_file

    def test_respects_level_parameter(self):
        """Should respect custom log level."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.log"

            import wdi_etl.config
            original_log_file = wdi_etl.config.LOG_FILE
            wdi_etl.config.LOG_FILE = log_file

            try:
                setup_logging(level="WARNING")
                root_logger = logging.getLogger()
                # Console handler should have WARNING level
                console_handlers = [
                    h for h in root_logger.handlers
                    if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler)
                ]
                if console_handlers:
                    assert console_handlers[0].level == logging.WARNING
            finally:
                wdi_etl.config.LOG_FILE = original_log_file

    def test_file_handler_configuration(self):
        """Should configure rotating file handler."""
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "test.log"

            import wdi_etl.config
            original_log_file = wdi_etl.config.LOG_FILE
            wdi_etl.config.LOG_FILE = log_file

            try:
                setup_logging()
                root_logger = logging.getLogger()
                file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
                assert len(file_handlers) == 1
                assert file_handlers[0].maxBytes == 10 * 1024 * 1024  # 10 MB
                assert file_handlers[0].backupCount == 5
            finally:
                wdi_etl.config.LOG_FILE = original_log_file

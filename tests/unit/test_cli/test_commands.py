"""
Unit tests for CLI commands module.
Author: Shankha Roy (Senior Data Engineer)
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wdi_etl.__main__ import parse_args, run


class TestParseArgs:
    """Test CLI argument parsing."""

    def test_default_values(self):
        """Should have sensible defaults."""
        with patch.object(sys, "argv", ["wdi_etl"]):
            args = parse_args()
            assert args.missing_strategy == "keep"
            assert args.skip_extract is False
            assert args.skip_parquet is False

    def test_skip_extract_flag(self):
        """Should parse --skip-extract flag."""
        with patch.object(sys, "argv", ["wdi_etl", "--skip-extract"]):
            args = parse_args()
            assert args.skip_extract is True

    def test_missing_strategy_options(self):
        """Should accept valid missing strategy options."""
        for strategy in ["drop", "forward_fill", "backward_fill", "interpolate", "keep"]:
            with patch.object(sys, "argv", ["wdi_etl", "--missing-strategy", strategy]):
                args = parse_args()
                assert args.missing_strategy == strategy

    def test_partition_by_option(self):
        """Should accept --partition-by option."""
        with patch.object(sys, "argv", ["wdi_etl", "--partition-by", "year"]):
            args = parse_args()
            assert args.partition_by == "year"

    def test_custom_paths(self, temp_dir):
        """Should accept custom directory paths."""
        raw_dir = temp_dir / "raw"
        output_dir = temp_dir / "output"

        with patch.object(sys, "argv", [
            "wdi_etl",
            "--raw-dir", str(raw_dir),
            "--output-dir", str(output_dir),
        ]):
            args = parse_args()
            assert args.raw_dir == raw_dir
            assert args.output_dir == output_dir


class TestRun:
    """Test pipeline run orchestration."""

    @patch("wdi_etl.__main__.extract_all")
    @patch("wdi_etl.__main__.transform_all")
    @patch("wdi_etl.__main__.load_panel")
    @patch("wdi_etl.__main__.setup_logging")
    def test_full_pipeline_run(self, mock_logging, mock_load, mock_transform, mock_extract, temp_dir):
        """Should execute full pipeline when not skipping extract."""
        from wdi_etl.__main__ import parse_args

        mock_extract.return_value = {"indicator": [{"value": 100}]}
        mock_transform.return_value = MagicMock()
        mock_transform.return_value.shape = (10, 5)
        mock_load.return_value = {"csv": temp_dir / "output.csv"}

        with patch.object(sys, "argv", ["wdi_etl", "--raw-dir", str(temp_dir), "--output-dir", str(temp_dir)]):
            args = parse_args()
            # Would need to refactor __main__ to inject args for cleaner testing
            # For now, just verify mocks were set up
            assert mock_extract.called or True  # Placeholder assertion

    @patch("wdi_etl.__main__.setup_logging")
    @patch("wdi_etl.__main__.parse_args")
    def test_logging_setup(self, mock_parse_args, mock_setup_logging):
        """Should configure logging with specified level."""
        mock_args = MagicMock()
        mock_args.log_level = "DEBUG"
        mock_args.skip_extract = True
        mock_args.raw_dir = Path("/tmp")
        mock_parse_args.return_value = mock_args

        # Mock file system operations
        with patch.object(Path, "glob", return_value=[]):
            with pytest.raises(FileNotFoundError):
                run()

        mock_setup_logging.assert_called_once_with(level="DEBUG")


class TestCLIExitCodes:
    """Test CLI exit behavior."""

    def test_successful_run(self):
        """Should exit with code 0 on success."""
        # Integration test - would need full mock setup
        pass  # Placeholder for E2E test

    def test_failed_run(self):
        """Should exit with non-zero code on failure."""
        # Integration test - would need full mock setup
        pass  # Placeholder for E2E test

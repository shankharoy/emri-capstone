"""
Unit tests for load module.
Author: Shankha Roy (Senior Data Engineer)
"""
from pathlib import Path

import pandas as pd
import pytest

from wdi_etl.core.load import load_panel


class TestLoadPanel:
    """Test load_panel function."""

    def test_writes_csv(self, temp_dir, sample_panel_dataframe):
        """Should write CSV file."""
        csv_path = temp_dir / "output.csv"

        result = load_panel(sample_panel_dataframe, csv_path=csv_path, parquet_path=None)

        assert csv_path.exists()
        assert result["csv"] == csv_path

    def test_csv_content(self, temp_dir, sample_panel_dataframe):
        """CSV should contain correct data."""
        csv_path = temp_dir / "output.csv"

        load_panel(sample_panel_dataframe, csv_path=csv_path, parquet_path=None)

        # Read back and verify
        df_read = pd.read_csv(csv_path)
        assert len(df_read) == len(sample_panel_dataframe)
        assert set(df_read.columns) == set(sample_panel_dataframe.columns)

    def test_writes_parquet(self, temp_dir, sample_panel_dataframe):
        """Should write Parquet file."""
        csv_path = temp_dir / "output.csv"
        parquet_path = temp_dir / "output.parquet"

        result = load_panel(sample_panel_dataframe, csv_path=csv_path, parquet_path=parquet_path)

        assert parquet_path.exists()
        assert result["parquet"] == parquet_path

    def test_parquet_preserves_dtypes(self, temp_dir, sample_panel_dataframe):
        """Parquet should preserve data types."""
        csv_path = temp_dir / "output.csv"
        parquet_path = temp_dir / "output.parquet"

        load_panel(sample_panel_dataframe, csv_path=csv_path, parquet_path=parquet_path)

        # Read back and verify types
        df_read = pd.read_parquet(parquet_path)
        assert df_read["year"].dtype == sample_panel_dataframe["year"].dtype
        assert df_read["value"].dtype == "float64"

    def test_partitioned_parquet(self, temp_dir, sample_panel_dataframe):
        """Should support partitioned Parquet output."""
        csv_path = temp_dir / "output.csv"
        parquet_dir = temp_dir / "partitioned"

        load_panel(
            sample_panel_dataframe,
            csv_path=csv_path,
            parquet_path=parquet_dir,
            partition_by="year"
        )

        # Should create directory with partitions
        assert parquet_dir.exists()

    def test_invalid_partition_column(self, temp_dir, sample_panel_dataframe):
        """Should raise ValueError for invalid partition column."""
        csv_path = temp_dir / "output.csv"
        parquet_path = temp_dir / "output.parquet"

        with pytest.raises(ValueError) as exc_info:
            load_panel(
                sample_panel_dataframe,
                csv_path=csv_path,
                parquet_path=parquet_path,
                partition_by="nonexistent_column"
            )
        assert "not in DataFrame columns" in str(exc_info.value)

    def test_returns_output_paths(self, temp_dir, sample_panel_dataframe):
        """Should return dict with output paths."""
        csv_path = temp_dir / "output.csv"
        parquet_path = temp_dir / "output.parquet"

        result = load_panel(sample_panel_dataframe, csv_path=csv_path, parquet_path=parquet_path)

        assert isinstance(result, dict)
        assert "csv" in result
        assert "parquet" in result
        assert result["csv"] == csv_path
        assert result["parquet"] == parquet_path

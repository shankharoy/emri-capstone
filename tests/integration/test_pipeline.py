"""
Integration tests for the full ETL pipeline.
Author: Shankha Roy (Senior Data Engineer)
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from wdi_etl.api.client import extract_all
from wdi_etl.core.load import load_panel
from wdi_etl.core.transform import transform_all


class TestFullPipeline:
    """Test the complete Extract -> Transform -> Load pipeline."""

    @pytest.fixture
    def mock_api_responses(self):
        """Mock responses for all indicators."""
        from wdi_etl.core.config import INDICATORS

        base_response = [
            {"page": 1, "pages": 1, "per_page": 10000, "total": 3},
            [
                {
                    "value": 10000.0,
                    "country": {"id": "AL", "value": "Albania"},
                    "countryiso3code": "ALB",
                    "indicator": {"id": "IND", "value": "Indicator"},
                    "date": "2021",
                },
                {
                    "value": 11000.0,
                    "country": {"id": "AL", "value": "Albania"},
                    "countryiso3code": "ALB",
                    "indicator": {"id": "IND", "value": "Indicator"},
                    "date": "2022",
                },
                {
                    "value": 12000.0,
                    "country": {"id": "AL", "value": "Albania"},
                    "countryiso3code": "ALB",
                    "indicator": {"id": "IND", "value": "Indicator"},
                    "date": "2023",
                },
            ],
        ]
        return base_response

    @patch("wdi_etl.api.client._build_session")
    def test_extract_transform_load_roundtrip(self, mock_build_session, mock_api_responses, temp_dir):
        """Should execute complete ETL pipeline successfully."""
        # Setup mocks
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_api_responses
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_build_session.return_value = mock_session

        # Stage 1: Extract
        raw_data = extract_all(raw_dir=temp_dir / "raw")
        assert len(raw_data) > 0
        for indicator, records in raw_data.items():
            assert isinstance(records, list)
            assert len(records) > 0

        # Stage 2: Transform
        panel = transform_all(raw_data, missing_strategy="keep")
        assert isinstance(panel, pd.DataFrame)
        assert len(panel) > 0
        assert "country_iso3" in panel.columns
        assert "indicator_code" in panel.columns
        assert "value" in panel.columns

        # Stage 3: Load
        output_dir = temp_dir / "output"
        csv_path = output_dir / "panel.csv"
        parquet_path = output_dir / "panel.parquet"

        outputs = load_panel(panel, csv_path=csv_path, parquet_path=parquet_path)

        assert csv_path.exists()
        assert parquet_path.exists()
        assert outputs["csv"] == csv_path
        assert outputs["parquet"] == parquet_path

        # Verify data integrity
        df_read = pd.read_csv(csv_path)
        assert len(df_read) == len(panel)

    def test_transform_with_cached_data(self, temp_dir):
        """Should transform from cached JSON files."""
        # Create cached JSON files
        raw_dir = temp_dir / "raw"
        raw_dir.mkdir()

        cached_data = {
            "NY.GDP.PCAP.CD": [
                {
                    "value": 10000.0,
                    "country": {"id": "AL", "value": "Albania"},
                    "countryiso3code": "ALB",
                    "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
                    "date": "2021",
                },
            ],
        }

        for indicator, records in cached_data.items():
            with open(raw_dir / f"{indicator}.json", "w") as f:
                json.dump(records, f)

        # Load and transform
        raw_data = {}
        for json_file in raw_dir.glob("*.json"):
            with open(json_file) as f:
                raw_data[json_file.stem] = json.load(f)

        panel = transform_all(raw_data, missing_strategy="keep")

        assert len(panel) > 0
        assert "NY.GDP.PCAP.CD" in panel["indicator_code"].values

    def test_pipeline_with_missing_strategy(self, temp_dir):
        """Should apply missing value strategies correctly."""
        # Create data with gaps
        raw_data = {
            "GDP": [
                {
                    "value": 100.0,
                    "country": {"id": "US", "value": "United States"},
                    "countryiso3code": "USA",
                    "indicator": {"id": "GDP", "value": "GDP"},
                    "date": "2021",
                },
                {
                    "value": None,  # Missing
                    "country": {"id": "US", "value": "United States"},
                    "countryiso3code": "USA",
                    "indicator": {"id": "GDP", "value": "GDP"},
                    "date": "2022",
                },
                {
                    "value": 120.0,
                    "country": {"id": "US", "value": "United States"},
                    "countryiso3code": "USA",
                    "indicator": {"id": "GDP", "value": "GDP"},
                    "date": "2023",
                },
            ],
        }

        # Test forward fill
        panel_ff = transform_all(raw_data, missing_strategy="forward_fill")
        # The middle value should now be filled

        # Test drop
        panel_drop = transform_all(raw_data, missing_strategy="drop")
        assert len(panel_drop) == 2  # One dropped


class TestPipelineEdgeCases:
    """Test edge cases in the pipeline."""

    def test_empty_data(self):
        """Should handle empty data gracefully."""
        raw_data = {"GDP": []}
        panel = transform_all(raw_data, missing_strategy="keep")
        assert isinstance(panel, pd.DataFrame)
        assert len(panel) == 0

    def test_all_null_values(self):
        """Should handle all-null indicator data."""
        raw_data = {
            "GDP": [
                {
                    "value": None,
                    "country": {"id": "XX", "value": "Unknown"},
                    "countryiso3code": "XXX",
                    "indicator": {"id": "GDP", "value": "GDP"},
                    "date": "2021",
                },
            ],
        }
        panel = transform_all(raw_data, missing_strategy="keep")
        assert len(panel) == 0  # All nulls filtered

    def test_very_large_dataset(self, temp_dir):
        """Should handle large datasets without memory issues."""
        # This is a smoke test for memory efficiency
        raw_dir = temp_dir / "raw"
        raw_dir.mkdir()

        # Create moderately sized dataset
        large_data = []
        for year in range(2014, 2024):
            for iso3 in ["USA", "GBR", "FRA", "DEU", "JPN"]:
                large_data.append({
                    "value": float(year * 1000),
                    "country": {"id": iso3[:2], "value": iso3},
                    "countryiso3code": iso3,
                    "indicator": {"id": "GDP", "value": "GDP"},
                    "date": str(year),
                })

        with open(raw_dir / "GDP.json", "w") as f:
            json.dump(large_data, f)

        # Load and process
        with open(raw_dir / "GDP.json") as f:
            raw_data = {"GDP": json.load(f)}

        panel = transform_all(raw_data, missing_strategy="keep")
        assert len(panel) == 50  # 10 years * 5 countries

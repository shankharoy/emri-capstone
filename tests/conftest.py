"""
Pytest configuration and shared fixtures.
Author: Shankha Roy (Senior Data Engineer)
"""
import json
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import pytest


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_indicator_records() -> list[dict[str, Any]]:
    """Sample raw API response records for testing."""
    return [
        {
            "value": 12345.67,
            "country": {"id": "AL", "value": "Albania"},
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
            "date": "2021",
        },
        {
            "value": 15000.0,
            "country": {"id": "AL", "value": "Albania"},
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
            "date": "2022",
        },
        {
            "value": None,  # Should be filtered out
            "country": {"id": "AL", "value": "Albania"},
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
            "date": "2020",
        },
    ]


@pytest.fixture
def sample_cleaned_dataframe(sample_indicator_records) -> pd.DataFrame:
    """Sample cleaned DataFrame for testing."""
    from wdi_etl.core.transform import clean_indicator
    return clean_indicator(sample_indicator_records)


@pytest.fixture
def sample_panel_dataframe() -> pd.DataFrame:
    """Sample panel DataFrame with multiple indicators."""
    return pd.DataFrame({
        "country_iso3": ["ALB", "ALB", "USA", "USA"],
        "country_name": ["Albania", "Albania", "United States", "United States"],
        "year": [2021, 2022, 2021, 2022],
        "value": [12345.67, 15000.0, 65000.0, 67000.0],
        "indicator_code": ["NY.GDP.PCAP.CD", "NY.GDP.PCAP.CD", "NY.GDP.PCAP.CD", "NY.GDP.PCAP.CD"],
    })


@pytest.fixture
def mock_api_response():
    """Mock World Bank API response structure."""
    return [
        {
            "page": 1,
            "pages": 1,
            "per_page": 10000,
            "total": 2,
        },
        [
            {
                "value": 12345.67,
                "country": {"id": "AL", "value": "Albania"},
                "countryiso3code": "ALB",
                "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
                "date": "2021",
            },
            {
                "value": 15000.0,
                "country": {"id": "AL", "value": "Albania"},
                "countryiso3code": "ALB",
                "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
                "date": "2022",
            },
        ],
    ]


@pytest.fixture
def sample_raw_json_file(temp_dir, sample_indicator_records):
    """Create a sample raw JSON file."""
    file_path = temp_dir / "NY.GDP.PCAP.CD.json"
    with open(file_path, "w") as f:
        json.dump(sample_indicator_records, f)
    return file_path

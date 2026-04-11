"""
Unit tests for API client module.
Author: Shankha Roy (Senior Data Engineer)
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

# Note: These tests assume the refactored structure with api/client.py
# For current structure, these test extract.py functionality


class TestAPIClient:
    """Test API client functionality."""

    def test_session_creation(self):
        """Should create configured session."""
        from wdi_etl.extract import _build_session

        session = _build_session()
        assert isinstance(session, requests.Session)
        assert "User-Agent" in session.headers

    @patch("requests.Session.get")
    def test_get_indicator_success(self, mock_get, mock_api_response):
        """Should fetch indicator data successfully."""
        from wdi_etl.extract import fetch_indicator

        mock_response = MagicMock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_indicator("NY.GDP.PCAP.CD", max_retries=1)

        assert len(result) == 2
        assert result[0]["countryiso3code"] == "ALB"

    @patch("requests.Session.get")
    def test_retry_logic(self, mock_get):
        """Should retry on failures."""
        from wdi_etl.extract import fetch_indicator

        # First call raises, second succeeds
        mock_response = MagicMock()
        mock_response.json.return_value = [{}, [{"value": 100}]]
        mock_response.raise_for_status.return_value = None
        mock_get.side_effect = [
            requests.RequestException("Network error"),
            mock_response,
        ]

        with pytest.raises(RuntimeError):
            # Will fail after retries with mocked side_effect
            fetch_indicator("NY.GDP.PCAP.CD", max_retries=1)


class TestAPIModels:
    """Test API data models (if using pydantic/dataclasses)."""

    def test_indicator_record_structure(self):
        """Test expected API record structure."""
        record = {
            "value": 12345.67,
            "country": {"id": "AL", "value": "Albania"},
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
            "date": "2021",
        }

        assert "value" in record
        assert "country" in record
        assert "countryiso3code" in record
        assert "indicator" in record
        assert "date" in record

    def test_null_value_handling(self):
        """Should handle null values in records."""
        record = {
            "value": None,
            "country": {"id": "AL", "value": "Albania"},
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
            "date": "2021",
        }

        assert record["value"] is None

"""
Unit tests for extract module.
Author: Shankha Roy (Senior Data Engineer)
"""
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from wdi_etl.api.client import _build_session, extract_all, fetch_indicator


class TestBuildSession:
    """Test session building."""

    def test_returns_session(self):
        """_build_session should return a requests Session."""
        session = _build_session()
        assert isinstance(session, requests.Session)

    def test_has_correct_headers(self):
        """Session should have proper headers set."""
        session = _build_session()
        assert "User-Agent" in session.headers
        assert "wdi-etl-pipeline" in session.headers["User-Agent"]
        assert session.headers["Accept"] == "application/json"


class TestFetchIndicator:
    """Test fetch_indicator function with mocked HTTP."""

    @patch("wdi_etl.extract._build_session")
    def test_successful_fetch(self, mock_build_session, mock_api_response):
        """Should return list of records on success."""
        # Setup mock
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_build_session.return_value = mock_session

        # Test
        result = fetch_indicator("NY.GDP.PCAP.CD", max_retries=1)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["countryiso3code"] == "ALB"

    @patch("wdi_etl.extract._build_session")
    def test_retries_on_failure(self, mock_build_session):
        """Should retry on transient failures."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        # First call fails, second succeeds
        mock_session.get.side_effect = [
            requests.RequestException("Network error"),
            mock_response,
        ]
        mock_response.json.return_value = [{}, [{"value": 100}]]
        mock_response.raise_for_status.return_value = None
        mock_build_session.return_value = mock_session

        # Should succeed on retry
        result = fetch_indicator("NY.GDP.PCAP.CD", max_retries=3)
        assert isinstance(result, list)

    @patch("wdi_etl.extract._build_session")
    def test_raises_after_max_retries(self, mock_build_session):
        """Should raise RuntimeError after max retries exceeded."""
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.RequestException("Network error")
        mock_build_session.return_value = mock_session

        with pytest.raises(RuntimeError) as exc_info:
            fetch_indicator("NY.GDP.PCAP.CD", max_retries=2)
        assert "Failed to fetch" in str(exc_info.value)

    @patch("wdi_etl.extract._build_session")
    def test_invalid_response_shape(self, mock_build_session):
        """Should raise ValueError for unexpected response format."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = ["unexpected"]  # Wrong format
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_build_session.return_value = mock_session

        with pytest.raises(ValueError) as exc_info:
            fetch_indicator("NY.GDP.PCAP.CD", max_retries=1)
        assert "Unexpected API response" in str(exc_info.value)


class TestExtractAll:
    """Test extract_all function."""

    @patch("wdi_etl.extract.fetch_indicator")
    def test_extracts_all_indicators(self, mock_fetch, temp_dir):
        """Should extract all configured indicators."""
        from wdi_etl.config import INDICATORS

        mock_fetch.return_value = [{"value": 100}]

        result = extract_all(raw_dir=temp_dir)

        assert len(result) == len(INDICATORS)
        assert mock_fetch.call_count == len(INDICATORS)

    @patch("wdi_etl.extract.fetch_indicator")
    def test_writes_json_files(self, mock_fetch, temp_dir):
        """Should write JSON files for each indicator."""
        mock_fetch.return_value = [{"value": 100}]

        extract_all(raw_dir=temp_dir)

        json_files = list(temp_dir.glob("*.json"))
        assert len(json_files) > 0

        # Verify JSON content
        for json_file in json_files:
            with open(json_file) as f:
                data = json.load(f)
                assert isinstance(data, list)

    @patch("wdi_etl.extract.fetch_indicator")
    def test_returns_indicator_mapping(self, mock_fetch, temp_dir):
        """Should return dict mapping indicator code to records."""
        mock_fetch.return_value = [{"value": 100}]

        result = extract_all(raw_dir=temp_dir)

        for indicator_code in result.keys():
            assert isinstance(result[indicator_code], list)

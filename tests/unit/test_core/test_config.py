"""
Unit tests for configuration module.
Author: Shankha Roy (Senior Data Engineer)
"""
from pathlib import Path

import pytest

from wdi_etl.core.config import (
    COUNTRY_NAME_CORRECTIONS,
    DATA_DIR,
    INDICATORS,
    LOG_DIR,
    MISSING_STRATEGY,
    OUTPUT_DIR,
    PROJECT_ROOT,
    RAW_DIR,
    WB_API_BASE,
    YEAR_END,
    YEAR_START,
)


class TestConfigValues:
    """Test configuration constants are properly defined."""

    def test_project_root_is_path(self):
        """PROJECT_ROOT should be a Path instance."""
        assert isinstance(PROJECT_ROOT, Path)
        assert PROJECT_ROOT.exists()

    def test_data_directories(self):
        """Data directories should be Path instances relative to project root."""
        assert isinstance(DATA_DIR, Path)
        assert isinstance(OUTPUT_DIR, Path)
        assert isinstance(RAW_DIR, Path)
        assert isinstance(LOG_DIR, Path)

    def test_year_range_valid(self):
        """Year range should be sensible."""
        assert isinstance(YEAR_START, int)
        assert isinstance(YEAR_END, int)
        assert YEAR_START < YEAR_END
        assert YEAR_START >= 1990  # Sanity check
        assert YEAR_END <= 2100  # Sanity check

    def test_api_base_is_url(self):
        """API base should be a valid HTTPS URL."""
        assert WB_API_BASE.startswith("https://")
        assert "worldbank.org" in WB_API_BASE

    def test_indicators_is_dict(self):
        """INDICATORS should be a non-empty dict with string keys."""
        assert isinstance(INDICATORS, dict)
        assert len(INDICATORS) > 0
        for code, description in INDICATORS.items():
            assert isinstance(code, str)
            assert isinstance(description, str)
            assert "." in code  # WB indicators have dot notation

    def test_missing_strategy_valid(self):
        """MISSING_STRATEGY should be a valid option."""
        valid_strategies = {"drop", "forward_fill", "backward_fill", "interpolate", "keep"}
        assert MISSING_STRATEGY in valid_strategies

    def test_country_corrections_is_dict(self):
        """COUNTRY_NAME_CORRECTIONS should map old names to new names."""
        assert isinstance(COUNTRY_NAME_CORRECTIONS, dict)
        for old, new in COUNTRY_NAME_CORRECTIONS.items():
            assert isinstance(old, str)
            assert isinstance(new, str)
            assert len(old) > 0
            assert len(new) > 0


class TestConfigExtensibility:
    """Test that config can be extended safely."""

    def test_can_add_indicator(self):
        """New indicators can be added to the dict."""
        new_indicators = INDICATORS.copy()
        new_indicators["NEW.INDICATOR"] = "New Test Indicator"
        assert len(new_indicators) == len(INDICATORS) + 1

    def test_can_add_country_correction(self):
        """New country corrections can be added."""
        new_corrections = COUNTRY_NAME_CORRECTIONS.copy()
        new_corrections["Old Name"] = "New Name"
        assert len(new_corrections) == len(COUNTRY_NAME_CORRECTIONS) + 1

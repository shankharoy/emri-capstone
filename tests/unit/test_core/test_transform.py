"""
Unit tests for transform module.
Author: Shankha Roy (Senior Data Engineer)
"""
import pandas as pd
import pytest

from wdi_etl.core.transform import (
    _filter_years,
    _fill_missing,
    _parse_indicator_record,
    _standardize_country_name,
    _standardize_dtypes,
    clean_indicator,
    merge_to_panel,
    transform_all,
    validate_panel,
)


class TestParseIndicatorRecord:
    """Test _parse_indicator_record function."""

    def test_parses_valid_record(self):
        """Should extract fields from valid record."""
        record = {
            "value": 1234.5,
            "country": {"id": "AL", "value": "Albania"},
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
            "date": "2021",
        }
        result = _parse_indicator_record(record)
        assert result is not None
        assert result["country_iso3"] == "ALB"
        assert result["country_name"] == "Albania"
        assert result["indicator_code"] == "NY.GDP.PCAP.CD"
        assert result["year"] == 2021
        assert result["value"] == 1234.5

    def test_returns_none_for_null_value(self):
        """Should return None for null values."""
        record = {
            "value": None,
            "country": {"id": "AL", "value": "Albania"},
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
            "date": "2021",
        }
        assert _parse_indicator_record(record) is None

    def test_handles_missing_country(self):
        """Should handle missing country field."""
        record = {
            "value": 1234.5,
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD"},
            "date": "2021",
        }
        result = _parse_indicator_record(record)
        assert result is not None
        assert result["country_name"] == ""


class TestStandardizeCountryName:
    """Test _standardize_country_name function."""

    def test_applies_correction(self):
        """Should apply country name corrections."""
        assert _standardize_country_name("Korea, Rep.") == "Korea, Republic of"
        assert _standardize_country_name("Cote d'Ivoire") == "Côte d'Ivoire"

    def test_passthrough_unknown(self):
        """Should pass through unknown names unchanged."""
        assert _standardize_country_name("Albania") == "Albania"
        assert _standardize_country_name("United States") == "United States"

    def test_strips_whitespace(self):
        """Should strip whitespace from names."""
        assert _standardize_country_name("  Albania  ") == "Albania"


class TestStandardizeDtypes:
    """Test _standardize_dtypes function."""

    def test_enforces_correct_types(self):
        """Should enforce correct pandas dtypes."""
        df = pd.DataFrame({
            "year": ["2021", "2022"],
            "value": ["100.5", "200.5"],
            "country_name": ["USA", "ALB"],
            "country_iso3": ["USA", "alb"],  # lowercase
            "indicator_code": ["GDP", "GNI"],
            "indicator_name": ["GDP per capita", "GNI per capita"],
        })

        result = _standardize_dtypes(df)

        assert result["year"].dtype == "int64"
        assert result["value"].dtype == "float64"
        assert result["country_iso3"].iloc[1] == "ALB"  # uppercased


class TestFilterYears:
    """Test _filter_years function."""

    def test_filters_to_range(self):
        """Should filter rows to year range."""
        from wdi_etl.core.config import YEAR_END, YEAR_START

        df = pd.DataFrame({"year": [2010, 2014, 2015, 2020, 2023, 2030]})
        result = _filter_years(df)

        expected_years = list(range(YEAR_START, YEAR_END + 1))
        assert all(year in expected_years for year in result["year"])

    def test_empty_frame(self):
        """Should handle empty DataFrame."""
        df = pd.DataFrame({"year": []})
        result = _filter_years(df)
        assert result.empty


class TestFillMissing:
    """Test _fill_missing function."""

    def test_forward_fill(self):
        """Should forward fill missing values."""
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA", "USA"],
            "indicator_code": ["GDP", "GDP", "GDP"],
            "year": [2021, 2022, 2023],
            "value": [100.0, None, 300.0],
        })
        result = _fill_missing(df, "forward_fill")
        assert result["value"].iloc[1] == 100.0

    def test_backward_fill(self):
        """Should backward fill missing values."""
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA", "USA"],
            "indicator_code": ["GDP", "GDP", "GDP"],
            "year": [2021, 2022, 2023],
            "value": [100.0, None, 300.0],
        })
        result = _fill_missing(df, "backward_fill")
        assert result["value"].iloc[1] == 300.0

    def test_interpolate(self):
        """Should interpolate missing values."""
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA", "USA"],
            "indicator_code": ["GDP", "GDP", "GDP"],
            "year": [2021, 2022, 2023],
            "value": [100.0, None, 300.0],
        })
        result = _fill_missing(df, "interpolate")
        assert result["value"].iloc[1] == pytest.approx(200.0)

    def test_respects_group_boundaries(self):
        """Should not fill across different countries/indicators."""
        df = pd.DataFrame({
            "country_iso3": ["USA", "ALB", "USA"],
            "indicator_code": ["GDP", "GDP", "GDP"],
            "year": [2021, 2022, 2023],
            "value": [100.0, None, None],
        })
        result = _fill_missing(df, "forward_fill")
        # ALB's null should not be filled from USA's value
        alb_value = result[result["country_iso3"] == "ALB"]["value"].iloc[0]
        assert pd.isna(alb_value)


class TestCleanIndicator:
    """Test clean_indicator function."""

    def test_removes_aggregates(self):
        """Should remove aggregate country codes."""
        raw = [
            {
                "value": 100.0,
                "country": {"id": "WLD", "value": "World"},
                "countryiso3code": "WLD",
                "indicator": {"id": "GDP", "value": "GDP"},
                "date": "2021",
            },
            {
                "value": 200.0,
                "country": {"id": "AL", "value": "Albania"},
                "countryiso3code": "ALB",
                "indicator": {"id": "GDP", "value": "GDP"},
                "date": "2021",
            },
        ]
        df = clean_indicator(raw)
        codes = df["country_iso3"].tolist()
        assert "WLD" not in codes
        assert "ALB" in codes

    def test_filters_invalid_iso3(self):
        """Should filter out invalid ISO3 codes."""
        raw = [
            {
                "value": 100.0,
                "country": {"id": "X", "value": "Invalid"},
                "countryiso3code": "XX",  # Too short
                "indicator": {"id": "GDP", "value": "GDP"},
                "date": "2021",
            },
            {
                "value": 200.0,
                "country": {"id": "AL", "value": "Albania"},
                "countryiso3code": "ALB",
                "indicator": {"id": "GDP", "value": "GDP"},
                "date": "2021",
            },
        ]
        df = clean_indicator(raw)
        assert len(df) == 1
        assert df["country_iso3"].iloc[0] == "ALB"

    def test_returns_empty_frame_for_all_null(self):
        """Should return empty DataFrame with correct schema if all null."""
        raw = [{"value": None, "country": {}, "countryiso3code": "", "indicator": {}, "date": ""}]
        df = clean_indicator(raw)
        assert df.empty
        expected_cols = [
            "country_name", "country_iso3", "indicator_code",
            "indicator_name", "year", "value"
        ]
        assert list(df.columns) == expected_cols


class TestMergeToPanel:
    """Test merge_to_panel function."""

    def test_merge_stacks_indicators(self):
        """Should stack multiple indicators."""
        df1 = pd.DataFrame({
            "country_iso3": ["ALB"],
            "country_name": ["Albania"],
            "year": [2021],
            "value": [100.0],
            "indicator_code": ["GDP"],
            "indicator_name": ["GDP"],
        })
        df2 = pd.DataFrame({
            "country_iso3": ["ALB"],
            "country_name": ["Albania"],
            "year": [2021],
            "value": [50.0],
            "indicator_code": ["GNI"],
            "indicator_name": ["GNI"],
        })
        panel = merge_to_panel({"GDP": df1, "GNI": df2})
        assert len(panel) == 2
        assert set(panel["indicator_code"]) == {"GDP", "GNI"}

    def test_drops_strategy(self):
        """Should drop rows with null values when strategy is drop."""
        df = pd.DataFrame({
            "country_iso3": ["ALB", "ALB"],
            "country_name": ["Albania", "Albania"],
            "year": [2021, 2022],
            "value": [100.0, None],
            "indicator_code": ["GDP", "GDP"],
        })
        panel = merge_to_panel({"GDP": df}, missing_strategy="drop")
        assert len(panel) == 1
        assert panel["value"].iloc[0] == 100.0


class TestValidatePanel:
    """Test validate_panel function."""

    def test_no_duplicates_passes(self):
        """Should pass with no duplicates."""
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA"],
            "year": [2021, 2022],
            "indicator_code": ["GDP", "GDP"],
            "value": [100.0, 200.0],
        })
        report = validate_panel(df)
        assert report["passed"] is True
        assert len(report["errors"]) == 0

    def test_duplicates_fail(self):
        """Should fail with duplicate rows."""
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA"],
            "year": [2021, 2021],
            "indicator_code": ["GDP", "GDP"],
            "value": [100.0, 200.0],
        })
        report = validate_panel(df)
        assert report["passed"] is False
        assert len(report["errors"]) > 0

    def test_reports_missing_years(self):
        """Should report missing years as warning."""
        df = pd.DataFrame({
            "country_iso3": ["USA"],
            "year": [2021],
            "indicator_code": ["GDP"],
            "value": [100.0],
        })
        report = validate_panel(df)
        # Should have warnings about missing years
        assert len(report["warnings"]) > 0

    def test_reports_missing_ratio(self):
        """Should report per-indicator missing ratios."""
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA"],
            "year": [2021, 2022],
            "indicator_code": ["GDP", "GDP"],
            "value": [100.0, None],
        })
        report = validate_panel(df)
        assert "indicator_GDP_missing_ratio" in report


class TestTransformAll:
    """Test transform_all function."""

    def test_end_to_end_transform(self, sample_indicator_records):
        """Should execute full transform pipeline."""
        raw_data = {"NY.GDP.PCAP.CD": sample_indicator_records}
        result = transform_all(raw_data, missing_strategy="keep")

        assert isinstance(result, pd.DataFrame)
        assert "country_iso3" in result.columns
        assert "indicator_code" in result.columns

"""
Unit tests for the transform stage.
Author: Shankha Roy (Senior Data Engineer)
"""
import pandas as pd
import pytest

from wdi_etl.transform import (
    _parse_indicator_record,
    _standardize_country_name,
    _standardize_dtypes,
    _filter_years,
    _fill_missing,
    clean_indicator,
    merge_to_panel,
    validate_panel,
)


class TestParseIndicatorRecord:
    def test_parses_valid_record(self):
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
        record = {
            "value": None,
            "country": {"id": "AL", "value": "Albania"},
            "countryiso3code": "ALB",
            "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita"},
            "date": "2021",
        }
        assert _parse_indicator_record(record) is None


class TestStandardizeCountryName:
    def test_applies_correction(self):
        assert _standardize_country_name("Korea, Rep.") == "Korea, Republic of"

    def test_passthrough_unknown(self):
        assert _standardize_country_name("Albania") == "Albania"


class TestFilterYears:
    def test_filters_to_range(self):
        df = pd.DataFrame({"year": [2010, 2014, 2015, 2020, 2023, 2030]})
        result = _filter_years(df)
        assert result["year"].tolist() == [2014, 2015, 2020, 2023]


class TestFillMissing:
    def test_forward_fill(self):
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA", "USA"],
            "indicator_code": ["GDP", "GDP", "GDP"],
            "year": [2021, 2022, 2023],
            "value": [100.0, None, 300.0],
        })
        result = _fill_missing(df, "forward_fill")
        assert result["value"].tolist()[1] == 100.0

    def test_interpolate(self):
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA", "USA"],
            "indicator_code": ["GDP", "GDP", "GDP"],
            "year": [2021, 2022, 2023],
            "value": [100.0, None, 300.0],
        })
        result = _fill_missing(df, "interpolate")
        assert result["value"].iloc[1] == pytest.approx(200.0)


class TestCleanIndicator:
    def test_removes_aggregates(self):
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

    def test_returns_empty_frame_for_all_null(self):
        raw = [{"value": None, "country": {}, "countryiso3code": "", "indicator": {}, "date": ""}]
        df = clean_indicator(raw)
        assert df.empty
        assert list(df.columns) == ["country_name", "country_iso3", "indicator_code", "indicator_name", "year", "value"]


class TestMergeToPanel:
    def test_merge_stacks_indicators(self):
        df1 = pd.DataFrame({
            "country_iso3": ["ALB"],
            "country_name": ["Albania"],
            "year": [2021],
            "value": [100.0],
        })
        df1["indicator_code"] = "GDP"
        df2 = pd.DataFrame({
            "country_iso3": ["ALB"],
            "country_name": ["Albania"],
            "year": [2021],
            "value": [50.0],
        })
        df2["indicator_code"] = "GNI"
        panel = merge_to_panel({"GDP": df1, "GNI": df2})
        assert len(panel) == 2
        assert set(panel["indicator_code"]) == {"GDP", "GNI"}


class TestValidatePanel:
    def test_no_duplicates_passes(self):
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
        df = pd.DataFrame({
            "country_iso3": ["USA", "USA"],
            "year": [2021, 2021],
            "indicator_code": ["GDP", "GDP"],
            "value": [100.0, 200.0],
        })
        report = validate_panel(df)
        assert report["passed"] is False
        assert len(report["errors"]) > 0

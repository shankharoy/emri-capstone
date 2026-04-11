"""
================================================================================
API Client — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy (Senior Data Engineer)
Version     : 1.0.0
Created     : 2026-04-11

Description :
    Responsible for the Extract phase of the ETL pipeline. Connects to the
    World Bank API, paginates through large result sets, applies retry logic
    with exponential back-off, and persists raw JSON responses to disk.

Key Design Decisions
-------------------
    1. Session reuse    — requests.Session() reuses TCP connections.
    2. Exponential back-off — 2^attempt seconds between retries.
    3. Rate limiting    — 250 ms sleep between pages.
    4. Full response caching — Raw JSON is written regardless.

World Bank API Reference
------------------------
    Endpoint : GET https://api.worldbank.org/v2/country/all/indicator/{indicator}
    Parameters:
        date     : YYYY:YYYY range (inclusive)
        format   : json
        per_page : 1-10000
        page     : 1-based
    Response  : [metadata_object, [record, record, ...]]
================================================================================
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

from wdi_etl.core.config import (
    INTERIM_DIR,
    INDICATORS,
    WB_API_BASE,
    WB_FORMAT,
    WB_PER_PAGE,
    YEAR_END,
    YEAR_START,
)

logger = logging.getLogger(__name__)


def _build_session() -> requests.Session:
    """Construct a requests Session configured for the World Bank API."""
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "wdi-etl-pipeline/1.0 (data-engineering; Shankha Roy)",
        }
    )
    return session


def fetch_indicator(
    indicator: str,
    year_start: int = YEAR_START,
    year_end: int = YEAR_END,
    max_retries: int = 3,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """
    Download all observations for one World Bank indicator across all countries
    for the configured year range.

    Parameters
    ----------
    indicator : str
        World Bank indicator code, e.g. "NY.GDP.PCAP.CD".
    year_start, year_end : int
        Inclusive year range.
    max_retries : int
        Number of retry attempts on transient failures.
    timeout : int
        HTTP request timeout in seconds.

    Returns
    -------
    list[dict[str, Any]]
        List of raw observation records as returned by the API.
    """
    all_records: list[dict[str, Any]] = []
    page = 1

    while True:
        url = (
            f"{WB_API_BASE}/country/all/indicator/{indicator}"
            f"?date={year_start}:{year_end}"
            f"&format={WB_FORMAT}"
            f"&per_page={WB_PER_PAGE}"
            f"&page={page}"
        )

        for attempt in range(max_retries):
            try:
                resp = _build_session().get(url, timeout=timeout)
                resp.raise_for_status()
                data: Any = resp.json()
                break
            except (requests.RequestException, json.JSONDecodeError) as exc:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Failed to fetch '{indicator}' page {page} "
                        f"after {max_retries} attempts: {exc}"
                    ) from exc
                logger.warning("Retry %d/%d for %s page %d: %s",
                               attempt + 1, max_retries, indicator, page, exc)
                time.sleep(2 ** attempt)

        if not isinstance(data, list) or len(data) < 2:
            raise ValueError(f"Unexpected API response shape for '{indicator}': {data!r}")

        records: list[dict[str, Any]] = data[1]
        if not records:
            break

        all_records.extend(records)
        page += 1
        time.sleep(0.25)

    logger.info("fetch_indicator('%s') -> %d records", indicator, len(all_records))
    return all_records


def extract_all(raw_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """
    Extract all configured indicators from the World Bank API and persist
    raw JSON responses to disk.

    Parameters
    ----------
    raw_dir : Path | None
        Directory for raw JSON cache. Defaults to INTERIM_DIR / "raw".

    Returns
    -------
    dict[str, list[dict[str, Any]]]
        Mapping from indicator code to list of raw records.
    """
    raw_dir = Path(raw_dir) if raw_dir else INTERIM_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[dict[str, Any]]] = {}

    for indicator in INDICATORS:
        logger.info("Fetching %s", indicator)
        records: list[dict[str, Any]] = fetch_indicator(indicator)
        results[indicator] = records

        out_path = raw_dir / f"{indicator}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info("%s -> %d records -> %s", indicator, len(records), out_path.name)

    return results

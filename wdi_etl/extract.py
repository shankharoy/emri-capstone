"""
================================================================================
Extract Stage — World Bank WDI ETL Pipeline
================================================================================
Author      : Shankha Roy
Version     : 1.0.0
Created     : 2026-04-11
Description :
    Responsible for the Extract phase of the ETL pipeline. Connects to the
    World Bank API, paginates through large result sets, applies retry logic
    with exponential back-off, and persists raw JSON responses to disk.

    Raw JSON files serve as an immutable cache — if the same indicator is
    re-run, the cached file can be reused (via --skip-extract) without
    making redundant API calls.  This also provides an audit trail: the
    exact data that entered the transform stage is always recoverable.

Key Design Decisions
--------------------
    1. Session reuse    — requests.Session() reuses TCP connections, reducing
                          latency across paginated calls.
    2. Exponential back-off — 2^attempt seconds between retries, capped by
                          max_retries.  Aligns with the Web API resilience
                          pattern (see Microsoft Azure Architecture Center).
    3. Rate limiting    — 250 ms sleep between pages is a courtesy to the
                          public API and prevents triggering throttling.
    4. Full response caching — Raw JSON is written regardless of whether the
                          data was modified; cache invalidation is controlled
                          by the caller deleting the file.

World Bank API Reference
------------------------
    Endpoint : GET https://api.worldbank.org/v2/country/all/indicator/{indicator}
    Parameters:
        date     : YYYY:YYYY range (inclusive)
        format   : json
        per_page : 1–10000
        page     : 1-based
    Response  : [metadata_object, [record, record, ...]]

================================================================================
"""

import json
import time
from pathlib import Path
from typing import Any

import requests

from wdi_etl.config import (
    INTERIM_DIR,
    INDICATORS,
    WB_API_BASE,
    WB_FORMAT,
    WB_PER_PAGE,
    YEAR_END,
    YEAR_START,
)


# ── HTTP Session ────────────────────────────────────────────────────────────────
# A module-level session is not used because each call to extract_all() should
# start with a fresh session (connection pool could hold stale state after
# long idle periods).  Instead, a session helper is called per-URL.


def _build_session() -> requests.Session:
    """
    Construct a requests Session configured for the World Bank API.

    Returns
    -------
    requests.Session
        A configured session with JSON accept header and descriptive
        User-Agent to aid API operators in identifying our traffic.
    """
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            # Descriptive User-Agent helps WB ops identify our pipeline
            "User-Agent": "wdi-etl-pipeline/1.0 (data-engineering; Shankha Roy)",
        }
    )
    return session


# ── Core Fetcher ───────────────────────────────────────────────────────────────


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

    The World Bank API paginates results at 10,000 records per page.  This
    function loops through all pages until an empty page is encountered,
    which signals the end of the result set.

    Parameters
    ----------
    indicator : str
        World Bank indicator code, e.g. "NY.GDP.PCAP.CD".
    year_start : int, default YEAR_START
        First year of the inclusive range to query.
    year_end : int, default YEAR_END
        Last year of the inclusive range to query.
    max_retries : int, default 3
        Number of retry attempts for each HTTP request on transient failures
        (connection error, 5xx, or JSON decode error).
    timeout : int, default 30
        Timeout in seconds for each HTTP request.  A value of 30 s accommodates
        the WB API's occasional slow response under load.

    Returns
    -------
    list[dict[str, Any]]
        List of raw observation records as returned by the API.  Each record
        is a dict with keys: country, countryiso3code, date, indicator, value,
        unit, obs_status, decimal.  Records with null values are included in
        the returned list and handled in the transform stage.

    Raises
    ------
    RuntimeError
        When all retry attempts for a page have been exhausted.
    ValueError
        When the API response structure is not a two-element list
        [metadata, records], indicating a format change or API error.

    Example
    -------
    >>> records = fetch_indicator("NY.GDP.PCAP.CD")
    >>> len(records)
    2660
    """
    all_records: list[dict[str, Any]] = []
    page = 1

    while True:
        # Build the paginated URL for the current page
        url = (
            f"{WB_API_BASE}/country/all/indicator/{indicator}"
            f"?date={year_start}:{year_end}"
            f"&format={WB_FORMAT}"
            f"&per_page={WB_PER_PAGE}"
            f"&page={page}"
        )

        # Retry loop with exponential back-off
        for attempt in range(max_retries):
            try:
                resp = _build_session().get(url, timeout=timeout)
                resp.raise_for_status()
                data: Any = resp.json()
                break  # success — exit retry loop
            except (requests.RequestException, json.JSONDecodeError) as exc:
                if attempt == max_retries - 1:
                    # All retries exhausted — propagate as RuntimeError
                    raise RuntimeError(
                        f"Failed to fetch indicator '{indicator}' page {page} "
                        f"after {max_retries} attempts: {exc}"
                    ) from exc
                # Exponential back-off: 1 s, 2 s, 4 s, ...
                time.sleep(2**attempt)

        # The WB API always returns a two-element list:
        #   data[0] : metadata object  (page count, total count, etc.)
        #   data[1] : list of observation records
        if not isinstance(data, list) or len(data) < 2:
            raise ValueError(
                f"Unexpected API response shape for '{indicator}': {data!r}"
            )

        records: list[dict[str, Any]] = data[1]

        # Empty page signals end of pagination
        if not records:
            break

        all_records.extend(records)
        page += 1

        # Respectful rate-limiting: 250 ms pause between pages
        time.sleep(0.25)

    return all_records


# ── Batch Orchestrator ──────────────────────────────────────────────────────────


def extract_all(raw_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """
    Extract all configured indicators from the World Bank API and persist
    raw JSON responses to disk.

    This function is the top-level entry point for the extract stage.  It
    iterates over every indicator defined in ``config.INDICATORS``, fetches
    the full result set, stores the raw response, and returns a dictionary
    mapping indicator codes to their list of records.

    Parameters
    ----------
    raw_dir : Path | None, default None
        Directory in which to write raw JSON files.  If None, defaults to
        ``INTERIM_DIR / "raw"``.  The directory is created if it does not
        already exist.

    Returns
    -------
    dict[str, list[dict[str, Any]]]
        Mapping from indicator code (e.g. "NY.GDP.PCAP.CD") to the list of
        raw observation records returned by the API.

    Raises
    ------
    RuntimeError
        Propagated from ``fetch_indicator`` if any API call fails after
        all retries.

    Notes
    -----
    The raw JSON files are written with ``ensure_ascii=False`` so that Unicode
    characters in country names (e.g. "Côte d'Ivoire") are stored verbatim
    rather than as escaped sequences.  This makes the files human-readable
    during development and debugging.

    The output files are named ``{indicator_code}.json`` (e.g.
    ``NY.GDP.PCAP.CD.json``) and are over-written on every run, providing
    a fresh snapshot from the live API.

    Example
    -------
    >>> raw_data = extract_all()
    >>> raw_data["NY.GDP.PCAP.CD"][0]["value"]
    1571.44918918981
    """
    # Resolve output directory
    raw_dir = Path(raw_dir) if raw_dir else INTERIM_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[dict[str, Any]]] = {}

    for indicator in INDICATORS:
        print(f"[extract] Fetching {indicator} ...")
        records: list[dict[str, Any]] = fetch_indicator(indicator)
        results[indicator] = records

        # Write raw JSON — serves as immutable cache for the transform stage
        out_path = raw_dir / f"{indicator}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            # ensure_ascii=False preserves Unicode characters (country names)
            json.dump(records, f, ensure_ascii=False, indent=2)

        print(f"[extract]   -> {len(records):,} records -> {out_path.name}")

    return results

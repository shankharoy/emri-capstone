# API Reference

## Public API

The main entry point provides three core functions:

### `wdi_etl.extract_all()`

Extract all configured indicators from the World Bank API.

```python
from pathlib import Path
from wdi_etl import extract_all

# Extract with default raw directory
raw_data = extract_all()

# Extract with custom raw directory
raw_data = extract_all(raw_dir=Path("./data/raw"))
```

**Parameters:**
- `raw_dir` (Path | None): Directory for raw JSON cache. Defaults to `data/raw`.

**Returns:**
- `dict[str, list[dict]]`: Mapping from indicator code to raw records

**Example Return:**
```python
{
    "NY.GDP.PCAP.CD": [
        {"countryiso3code": "USA", "date": "2023", "value": 76398.3, ...},
        ...
    ],
    "IT.NET.USER.ZS": [...],
    ...
}
```

---

### `wdi_etl.transform_all()`

Transform raw data into a tidy panel DataFrame.

```python
from wdi_etl import transform_all

# Transform with default strategy
panel = transform_all(raw_data)

# Transform with specific missing value strategy
panel = transform_all(
    raw_data,
    missing_strategy="forward_fill"  # Options: drop, forward_fill, backward_fill, interpolate, keep
)
```

**Parameters:**
- `raw_data` (dict): Raw API responses from `extract_all()`
- `missing_strategy` (str): Strategy for handling missing values
  - `"drop"`: Remove rows with missing values
  - `"forward_fill"`: Carry last known value forward
  - `"backward_fill"`: Carry next known value backward
  - `"interpolate"`: Linear interpolation
  - `"keep"`: Leave missing values as NaN (default)

**Returns:**
- `pd.DataFrame`: Tidy panel with columns:
  - `country_iso3`: ISO 3166-1 alpha-3 code
  - `country_name`: Standardized country name
  - `year`: Observation year (int)
  - `value`: Indicator value (float)
  - `indicator_code`: World Bank indicator code

---

### `wdi_etl.load_panel()`

Load the panel DataFrame to CSV and Parquet.

```python
from pathlib import Path
from wdi_etl import load_panel

# Basic usage
outputs = load_panel(panel)

# With custom paths
outputs = load_panel(
    panel,
    csv_path=Path("output.csv"),
    parquet_path=Path("output.parquet")
)

# With partitioning
outputs = load_panel(
    panel,
    parquet_path=Path("output.parquet"),
    partition_by="year"  # Creates hive-style partitions
)

# CSV only
outputs = load_panel(
    panel,
    parquet_path=None
)
```

**Parameters:**
- `df` (pd.DataFrame): Panel DataFrame from `transform_all()`
- `csv_path` (Path | str | None): CSV output path. Default from config.
- `parquet_path` (Path | str | None): Parquet output path. Default from config.
- `partition_by` (str | None): Column to partition Parquet on (e.g., 'year')

**Returns:**
- `dict[str, Path]`: Mapping of format to output path
  - Keys: `"csv"`, `"parquet"` (if generated)

---

## API Client

### `wdi_etl.api.client.fetch_indicator()`

Download observations for a single indicator.

```python
from wdi_etl.api.client import fetch_indicator

records = fetch_indicator(
    indicator="NY.GDP.PCAP.CD",
    year_start=2014,
    year_end=2023,
    max_retries=3,
    timeout=30
)
```

**Parameters:**
- `indicator` (str): World Bank indicator code
- `year_start` (int): Start year (inclusive)
- `year_end` (int): End year (inclusive)
- `max_retries` (int): Number of retry attempts (default: 3)
- `timeout` (int): HTTP timeout in seconds (default: 30)

**Returns:**
- `list[dict]`: Raw API records

---

## EDA Functions

### `wdi_etl.eda.run_eda()`

Run complete exploratory data analysis.

```python
from wdi_etl.eda import run_eda

# Run with default panel path
results = run_eda()

# Run with custom path
results = run_eda(path="./data/output/wdi_panel.csv")
```

**Parameters:**
- `path` (Path | str | None): Path to panel CSV/Parquet. Default: `data/output/wdi_panel.csv`

**Returns:**
- `dict[str, pd.DataFrame]`: Analysis results including:
  - `summary_stats`: Descriptive statistics per indicator
  - `missingness`: Missing value ratios
  - `coverage_country`: Per-country completeness
  - `coverage_year`: Per-year observation counts
  - `correlation`: Pairwise indicator correlations
  - `distribution`: Distribution metrics
  - `top_gdp`: Top 10 countries by GDP
  - `bottom_gdp`: Bottom 10 countries by GDP

---

### `wdi_etl.eda.load_panel()`

Load panel data for analysis.

```python
from wdi_etl.eda import load_panel

df = load_panel()  # Default path
df = load_panel("./custom/path.csv")
df = load_panel("./custom/path.parquet")
```

**Parameters:**
- `path` (Path | str | None): File path. Auto-detects format from extension.

**Returns:**
- `pd.DataFrame`: Panel DataFrame

---

### `wdi_etl.eda.summary_stats()`

Compute descriptive statistics for each indicator.

```python
from wdi_etl.eda import load_panel, summary_stats

df = load_panel()
stats = summary_stats(df)
```

**Returns:**
- `pd.DataFrame`: Statistics per indicator (count, mean, std, min, q25, median, q75, max, null)

---

### `wdi_etl.eda.missingness_report()`

Generate per-indicator missing-value report.

```python
from wdi_etl.eda import load_panel, missingness_report

df = load_panel()
missing = missingness_report(df)
```

**Returns:**
- `pd.DataFrame`: Missing value counts and ratios per indicator

---

### `wdi_etl.eda.coverage_by_country()`

Analyze data completeness per country.

```python
from wdi_etl.eda import load_panel, coverage_by_country

df = load_panel()
coverage = coverage_by_country(df, min_years=5)
```

**Parameters:**
- `df` (pd.DataFrame): Panel DataFrame
- `min_years` (int): Minimum years for "well covered" flag (default: 5)

**Returns:**
- `pd.DataFrame`: Per-country coverage metrics

---

### `wdi_etl.eda.indicator_correlation()`

Compute pairwise correlation between indicators.

```python
from wdi_etl.eda import load_panel, indicator_correlation

df = load_panel()
corr = indicator_correlation(df)
```

**Returns:**
- `pd.DataFrame`: Pearson correlation matrix

---

### `wdi_etl.eda.top_bottom()`

Get top and bottom countries by indicator.

```python
from wdi_etl.eda import load_panel, top_bottom

df = load_panel()
result = top_bottom(
    df,
    indicator="NY.GDP.PCAP.CD",
    n=10,
    year_range=(2014, 2023)
)

top_10 = result["top"]
bottom_10 = result["bottom"]
```

**Parameters:**
- `df` (pd.DataFrame): Panel DataFrame
- `indicator` (str): Indicator code to rank by
- `n` (int): Number of countries to return (default: 10)
- `year_range` (tuple | None): Optional (start, end) year filter

**Returns:**
- `dict[str, pd.DataFrame]`: Dict with "top" and "bottom" keys

---

### `wdi_etl.eda.time_series_data()`

Extract country-level time series for plotting.

```python
from wdi_etl.eda import load_panel, time_series_data

df = load_panel()
ts = time_series_data(df, iso3="USA", indicator="NY.GDP.PCAP.CD")
```

**Parameters:**
- `df` (pd.DataFrame): Panel DataFrame
- `iso3` (str): ISO 3166-1 alpha-3 country code
- `indicator` (str | None): Optional indicator filter

**Returns:**
- `pd.DataFrame`: Time series data for plotting

---

## Configuration

Access pipeline settings from `wdi_etl.core.config`:

```python
from wdi_etl.core.config import (
    INDICATORS,          # Dict of indicator codes and descriptions
    YEAR_START,          # Start year (2014)
    YEAR_END,            # End year (2023)
    MISSING_STRATEGY,    # Default missing value strategy
    OUTPUT_CSV,          # Default CSV output path
    OUTPUT_PARQUET,      # Default Parquet output path
    WB_API_BASE,         # World Bank API base URL
    COUNTRY_NAME_CORRECTIONS,  # Country name mappings
)
```

## CLI Commands

### Full Pipeline

```bash
# Run complete pipeline
python -m wdi_etl

# With options
python -m wdi_etl \
    --missing-strategy forward_fill \
    --partition-by year \
    --log-level INFO
```

### Available Options

| Option | Description | Default |
|--------|-------------|---------|
| `--missing-strategy` | Missing value handling | `keep` |
| `--skip-extract` | Use cached raw JSON | `False` |
| `--raw-dir` | Raw JSON cache directory | `data/raw` |
| `--interim-dir` | Intermediate files directory | `data/interim` |
| `--output-dir` | Output directory | `data/output` |
| `--partition-by` | Parquet partition column | `None` |
| `--skip-parquet` | Skip Parquet output | `False` |
| `--log-level` | Console log level | `INFO` |

### EDA Command

```bash
python -m wdi_etl.eda [path]
```

If path is omitted, uses `data/output/wdi_panel.csv`.

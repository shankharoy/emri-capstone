# API Reference

## Public API

### `wdi_etl.extract_all()`

Extract all configured indicators from the World Bank API.

```python
from wdi_etl import extract_all

raw_data = extract_all(raw_dir=Path("./data/raw"))
```

**Parameters:**
- `raw_dir` (Path | None): Directory for raw JSON cache

**Returns:**
- `dict[str, list[dict]]`: Mapping from indicator code to raw records

---

### `wdi_etl.transform_all()`

Transform raw data into a tidy panel DataFrame.

```python
from wdi_etl import transform_all

panel = transform_all(raw_data, missing_strategy="forward_fill")
```

**Parameters:**
- `raw_data` (dict): Raw API responses from `extract_all()`
- `missing_strategy` (str): One of "drop", "forward_fill", "backward_fill", "interpolate", "keep"

**Returns:**
- `pd.DataFrame`: Tidy panel with columns: country_iso3, country_name, year, value, indicator_code

---

### `wdi_etl.load_panel()`

Load the panel DataFrame to CSV and Parquet.

```python
from wdi_etl import load_panel

outputs = load_panel(
    panel,
    csv_path=Path("output.csv"),
    parquet_path=Path("output.parquet"),
    partition_by="year"  # Optional
)
```

**Parameters:**
- `df` (pd.DataFrame): Panel DataFrame
- `csv_path` (Path | str | None): CSV output path
- `parquet_path` (Path | str | None): Parquet output path
- `partition_by` (str | None): Column to partition Parquet on

**Returns:**
- `dict[str, Path]`: Mapping of format to output path

---

## EDA Functions

### `wdi_etl.eda.run_eda()`

Run complete exploratory data analysis.

```python
from wdi_etl.eda import run_eda

results = run_eda(path="./data/output/wdi_panel.csv")
```

**Returns:**
- `dict[str, pd.DataFrame]`: Analysis results including summary stats, missingness, coverage, correlation

---

## Configuration

All pipeline settings are in `wdi_etl.core.config`:

```python
from wdi_etl.core.config import (
    INDICATORS,      # Dict of indicator codes
    YEAR_START,      # Start year (2014)
    YEAR_END,        # End year (2023)
    MISSING_STRATEGY,# Default missing value strategy
)
```

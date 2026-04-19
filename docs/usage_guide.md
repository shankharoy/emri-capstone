# Usage Guide

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Running the Pipeline](#running-the-pipeline)
4. [Missing Value Handling](#missing-value-handling)
5. [Output Partitioning](#output-partitioning)
6. [Running EDA](#running-eda)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## Installation

### Requirements

- Python >= 3.10
- pip package manager

### Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd emri-capstone

# Create virtual environment (recommended)
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install production dependencies
pip install -r requirements.txt

# Or install in development mode (includes dev dependencies)
pip install -e ".[dev]"
```

### Verify Installation

```bash
python -m wdi_etl --help
```

---

## Quick Start

### Run Full Pipeline

The simplest way to run the complete pipeline:

```bash
python -m wdi_etl
```

This will:
1. Download all configured indicators from World Bank API
2. Clean and merge into a tidy panel DataFrame
3. Output to `data/output/wdi_panel.csv` and `data/output/wdi_panel.parquet`
4. Generate EDA visualizations in `data/output/`

Expected output:
```
============================================================
World Bank WDI ETL Pipeline — Shankha Roy
============================================================
Fetching NY.GDP.PCAP.CD
NY.GDP.PCAP.CD -> 2670 records -> NY.GDP.PCAP.CD.json
...
Done. Shape: (13350, 5) | Elapsed: 45.2s
Outputs: [WindowsPath('data/output/wdi_panel.csv'), WindowsPath('data/output/wdi_panel.parquet')]
```

---

## Running the Pipeline

### Skip Extraction

If you've already downloaded the data and want to re-run transformations:

```bash
python -m wdi_etl --skip-extract
```

This loads cached JSON from `data/raw/` instead of calling the API.

### Custom Directories

```bash
# Specify custom directories
python -m wdi_etl \
    --raw-dir ./my_data/raw \
    --output-dir ./my_data/output
```

### Skip Parquet Output

If you only need CSV output:

```bash
python -m wdi_etl --skip-parquet
```

### Debug Logging

For detailed logging during execution:

```bash
python -m wdi_etl --log-level DEBUG
```

---

## Missing Value Handling

Choose how to handle missing values during transformation:

### Available Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `keep` | Leave as NaN | When you want to handle missing values later |
| `drop` | Remove rows with missing values | When completeness is required |
| `forward_fill` | Carry last known value forward | For time series with intermittent gaps |
| `backward_fill` | Carry next known value backward | When recent data is more reliable |
| `interpolate` | Linear interpolation | For smoothly varying metrics |

### Examples

```bash
# Forward fill (recommended for time series)
python -m wdi_etl --missing-strategy forward_fill

# Linear interpolation
python -m wdi_etl --missing-strategy interpolate

# Drop incomplete rows
python -m wdi_etl --missing-strategy drop
```

### Programmatic Usage

```python
from wdi_etl import extract_all, transform_all, load_panel

raw_data = extract_all()

# Transform with different strategies
panel_ff = transform_all(raw_data, missing_strategy="forward_fill")
panel_interp = transform_all(raw_data, missing_strategy="interpolate")

# Compare
print(f"Forward fill: {panel_ff['value'].isna().sum()} missing")
print(f"Interpolate: {panel_interp['value'].isna().sum()} missing")
```

---

## Output Partitioning

For large datasets, partition the Parquet output by a column:

```bash
# Partition by year (creates year=2014/, year=2015/, etc.)
python -m wdi_etl --partition-by year
```

This creates a Hive-style partitioned directory structure:

```
data/output/
├── wdi_panel.csv
└── wdi_panel.parquet/
    ├── year=2014/
    │   └── part-0.parquet
    ├── year=2015/
    │   └── part-0.parquet
    └── ...
```

**Benefits:**
- Faster queries when filtering by partition column
- Smaller individual files
- Compatible with Spark, Hive, Presto, etc.

---

## Running EDA

### Command Line

```bash
# Run with default panel
python -m wdi_etl.eda

# Run with custom panel file
python -m wdi_etl.eda ./my_data/output/panel.csv
```

### Jupyter Notebook

Open the professional EDA notebook:

```bash
jupyter notebook notebooks/wdi_eda_professional.ipynb
```

### Programmatic Usage

```python
from wdi_etl.eda import run_eda, load_panel, summary_stats

# Run full EDA report
results = run_eda()

# Access individual results
print(results["summary_stats"])
print(results["correlation"])
print(results["top_gdp"])

# Or use individual functions
df = load_panel()
stats = summary_stats(df)
missing = missingness_report(df)
```

### EDA Outputs

The EDA generates:
- Summary statistics (count, mean, std, quartiles)
- Missingness report by indicator
- Coverage analysis by country and year
- Correlation matrix between indicators
- Distribution metrics (skewness, kurtosis)
- Top/bottom country rankings
- Saved visualizations in `data/output/`:
  - `eda_summary_bar.png`
  - `eda_timeseries.png`
  - `eda_gdp_flfpr.png`
  - `eda_gdp_ranking.png`
  - `eda_urban_internet.png`
  - `eda_corr_heatmap.png`
  - `eda_coverage_hist.png`
  - `eda_violin.png`
  - `eda_boxplot.png`

---

## Configuration

### Edit Configuration File

All settings are in `src/wdi_etl/core/config.py`:

```python
# Add new indicators
INDICATORS = {
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "IT.NET.USER.ZS": "Internet users (% of population)",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total)",
    "SL.TLF.CACT.FE.ZS": "Female labour force participation rate (%)",
    "NY.GNP.PCAP.CD": "GNI per capita, Atlas method (current US$)",
    "SE.XPD.TOTL.GD.ZS": "Government expenditure on education (% of GDP)",  # New
}

# Change year range
YEAR_START = 2010  # Changed from 2014
YEAR_END = 2023

# Change output paths
OUTPUT_CSV = OUTPUT_DIR / "my_analysis.csv"
OUTPUT_PARQUET = OUTPUT_DIR / "my_analysis.parquet"

# Update country name corrections
COUNTRY_NAME_CORRECTIONS = {
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Korea, Rep.": "South Korea",  # Changed
    # ...
}
```

### Environment Variables (Advanced)

For production deployments, modify config to use environment variables:

```python
import os

YEAR_START = int(os.getenv("WDI_YEAR_START", 2014))
YEAR_END = int(os.getenv("WDI_YEAR_END", 2023))
MISSING_STRATEGY = os.getenv("WDI_MISSING_STRATEGY", "keep")
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Unit Tests Only

```bash
pytest tests/unit/ -v
```

### Run Integration Tests

```bash
pytest tests/integration/ -v
```

### Run with Coverage

```bash
# Generate coverage report in terminal
pytest tests/ --cov=wdi_etl

# Generate HTML coverage report
pytest tests/ --cov=wdi_etl --cov-report=html

# Open HTML report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### Skip Slow Tests

```bash
pytest tests/ -v -m "not slow"
```

---

## Troubleshooting

### No JSON Files Error

**Problem:**
```
FileNotFoundError: No JSON files in data/raw. Run without --skip-extract.
```

**Solution:**
```bash
# First run to download data
python -m wdi_etl

# Then subsequent runs can use cached data
python -m wdi_etl --skip-extract
```

### API Rate Limiting

**Problem:**
```
RuntimeError: Failed to fetch 'NY.GDP.PCAP.CD' after 3 attempts
```

**Solution:**
The pipeline includes built-in rate limiting (250ms between requests) and retry logic with exponential backoff. If you consistently hit limits:

1. Wait a few minutes before retrying
2. Check your network connection
3. Verify the World Bank API is accessible

### Memory Issues

**Problem:** Process runs out of memory with large datasets.

**Solution:**
1. Use partitioned Parquet output:
   ```bash
   python -m wdi_etl --partition-by year
   ```
2. Process indicators individually instead of all at once
3. Increase available memory or use a machine with more RAM

### Module Not Found Error

**Problem:**
```
ModuleNotFoundError: No module named 'wdi_etl'
```

**Solution:**
```bash
# Install package in development mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"  # macOS/Linux
set PYTHONPATH=%PYTHONPATH%;%CD%\src        # Windows
```

### Permission Denied for Output

**Problem:**
```
PermissionError: [Errno 13] Permission denied: 'data/output/wdi_panel.csv'
```

**Solution:**
1. Check write permissions on the output directory
2. Run with appropriate permissions
3. Specify a different output directory:
   ```bash
   python -m wdi_etl --output-dir /path/with/permissions
   ```

### Panel File Not Found for EDA

**Problem:**
```
FileNotFoundError: Panel file not found: data/output/wdi_panel.csv
```

**Solution:**
```bash
# Run the pipeline first to generate the panel
python -m wdi_etl

# Then run EDA
python -m wdi_etl.eda
```

---

## Advanced Usage

### Custom Pipeline Script

Create a custom script that uses the pipeline programmatically:

```python
#!/usr/bin/env python
"""Custom pipeline execution."""
from pathlib import Path
from wdi_etl import extract_all, transform_all, load_panel

def run_custom_analysis():
    # Extract only specific indicators
    from wdi_etl.core.config import INDICATORS
    selected = {k: v for k, v in INDICATORS.items() if "GDP" in v}
    
    # Override config temporarily
    raw_data = extract_all()
    
    # Custom transformation
    panel = transform_all(raw_data, missing_strategy="interpolate")
    
    # Custom output
    outputs = load_panel(
        panel,
        csv_path=Path("custom_output.csv"),
        partition_by="year"
    )
    
    print(f"Saved to: {outputs}")

if __name__ == "__main__":
    run_custom_analysis()
```

### Batch Processing

Process multiple configurations:

```bash
#!/bin/bash
for strategy in drop forward_fill interpolate; do
    python -m wdi_etl \
        --missing-strategy $strategy \
        --output-dir "data/output_${strategy}"
done
```

# Usage Guide

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd wdi-etl

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

### Full Pipeline Run

```bash
python -m wdi_etl
```

This will:
1. Download all indicators from World Bank API
2. Clean and merge into a tidy panel
3. Output to CSV and Parquet

### Skip Extraction

If you've already downloaded the data:

```bash
python -m wdi_etl --skip-extract
```

### Missing Value Handling

Choose how to handle missing values:

```bash
# Forward fill (carry last known value forward)
python -m wdi_etl --missing-strategy forward_fill

# Linear interpolation
python -m wdi_etl --missing-strategy interpolate

# Drop rows with missing values
python -m wdi_etl --missing-strategy drop
```

### Partitioned Output

For large datasets, partition Parquet by year:

```bash
python -m wdi_etl --partition-by year
```

## Running EDA

```bash
python -m wdi_etl.eda
```

Or programmatically:

```python
from wdi_etl.eda import run_eda

results = run_eda()
print(results["summary_stats"])
print(results["correlation"])
```

## Configuration

Edit `src/wdi_etl/core/config.py` to customize:

- **Indicators**: Add new World Bank indicator codes
- **Year Range**: Change YEAR_START and YEAR_END
- **Output Paths**: Modify OUTPUT_CSV and OUTPUT_PARQUET
- **Country Names**: Update COUNTRY_NAME_CORRECTIONS

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=wdi_etl --cov-report=html
```

## Troubleshooting

### No JSON files error

If you get "No JSON files" when using `--skip-extract`, run without the flag first:

```bash
python -m wdi_etl  # Downloads data
python -m wdi_etl --skip-extract  # Uses cached data
```

### API Rate Limiting

The pipeline includes built-in rate limiting (250ms between requests). If you hit limits, the retry logic with exponential backoff will handle it automatically.

### Memory Issues

For very large datasets, use partitioned Parquet output:

```bash
python -m wdi_etl --partition-by year
```

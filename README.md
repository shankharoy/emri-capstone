# World Bank WDI ETL Pipeline

## Overview
Production ETL pipeline for extracting, transforming, validating, and loading World Bank WDI indicators (2014–2023).

## Project Structure
```
.
├── configs/                  # Environment-specific YAML configuration files
├── data/                    # Data directory (gitignored)
│   ├── raw/                 # Cached raw JSON from World Bank API
│   └── output/              # Final pipeline outputs (CSV + Parquet)
├── docs/                    # Project documentation
├── logs/                    # Pipeline run logs (gitignored)
├── notebooks/               # Jupyter notebooks (EDA, analysis)
├── references/              # API docs, data dictionaries
├── src/wdi_etl/            # Python package source
│   ├── __init__.py
│   ├── config.py            # All pipeline configuration
│   ├── extract.py           # World Bank API extraction
│   ├── transform.py         # Data cleaning & validation
│   ├── load.py              # CSV & Parquet output
│   ├── eda.py               # Exploratory Data Analysis module
│   ├── logger.py            # Centralised logging setup
│   └── __main__.py          # CLI entry point
└── tests/                   # Unit and integration tests
```

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline
python -m wdi_etl

# Re-run without re-downloading
python -m wdi_etl --skip-extract

# Run with forward-fill for missing values
python -m wdi_etl --missing-strategy forward_fill

# Partition Parquet output by year
python -m wdi_etl --partition-by year

# Run EDA
python -m wdi_etl.eda

# Show all options
python -m wdi_etl --help
```

## Indicators
| Code | Description |
|------|-------------|
| `NY.GDP.PCAP.CD` | GDP per capita (current US$) |
| `IT.NET.USER.ZS` | Internet users (% of population) |
| `SP.URB.TOTL.IN.ZS` | Urban population (% of total) |
| `SL.TLF.CACT.FE.ZS` | Female labour force participation rate (%) |
| `NY.GNP.PCAP.CD` | GNI per capita, Atlas method (US$) |

## Configuration
All settings are in `src/wdi_etl/config.py`. No hard-coded values elsewhere.

## Author
**Shankha Roy** — Senior Data Engineer

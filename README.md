# World Bank WDI ETL Pipeline

## Overview
Production ETL pipeline for extracting, transforming, validating, and loading World Bank WDI (World Development Indicators) data for the period 2014–2023.

## Features
- **Extract**: Fetches indicators from World Bank API with retry logic and rate limiting
- **Transform**: Cleans, validates, and creates a tidy panel dataset
- **Load**: Outputs to CSV and Parquet formats with optional partitioning
- **EDA**: Comprehensive exploratory data analysis with visualizations
- **CLI**: Command-line interface with flexible options

## Project Structure
```
.
├── configs/                  # Configuration folder (placeholder)
├── data/                    # Data directory
│   ├── raw/                 # Cached raw JSON from World Bank API
│   └── output/              # Final pipeline outputs (CSV + Parquet + visualizations)
├── docs/                    # Project documentation
│   ├── architecture.md      # Architecture documentation
│   ├── api_reference.md     # API reference guide
│   └── usage_guide.md       # Usage instructions
├── logs/                    # Pipeline run logs
├── notebooks/               # Jupyter notebooks (EDA, analysis)
│   ├── wdi_eda.ipynb        # Basic EDA notebook
│   └── wdi_eda_professional.ipynb  # Professional EDA notebook
├── references/              # API docs, data dictionaries
├── src/wdi_etl/            # Python package source
│   ├── __init__.py         # Package entry point
│   ├── __main__.py         # CLI entry point
│   ├── api/                # External API interaction
│   │   ├── __init__.py
│   │   └── client.py       # World Bank API client with retry logic
│   ├── cli/                # Command-line interface
│   │   ├── __init__.py
│   │   └── commands.py     # CLI commands and orchestration
│   ├── core/               # Business logic (ETL stages)
│   │   ├── __init__.py
│   │   ├── config.py       # Centralized configuration
│   │   ├── load.py         # CSV & Parquet output
│   │   └── transform.py    # Data cleaning & validation
│   ├── eda/                # Exploratory data analysis
│   │   ├── __init__.py
│   │   └── analysis.py     # Statistical functions and reports
│   └── utils/              # Shared utilities
│       ├── __init__.py
│       └── logging_config.py  # Logging setup
├── tests/                   # Unit and integration tests
│   ├── conftest.py         # Pytest fixtures
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── pyproject.toml          # Project metadata and dependencies
├── requirements.txt        # Production dependencies
└── README.md               # This file
```

## Quick Start

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd emri-capstone

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e ".[dev]"
```

### Run the Pipeline
```bash
# Run full pipeline
python -m wdi_etl

# Re-run without re-downloading
python -m wdi_etl --skip-extract

# Run with forward-fill for missing values
python -m wdi_etl --missing-strategy forward_fill

# Partition Parquet output by year
python -m wdi_etl --partition-by year

# Show all options
python -m wdi_etl --help
```

### Run EDA
```bash
# Run EDA from command line
python -m wdi_etl.eda

# Or open Jupyter notebooks
jupyter notebook notebooks/wdi_eda_professional.ipynb
```

## Indicators

| Code | Description |
|------|-------------|
| `NY.GDP.PCAP.CD` | GDP per capita (current US$) |
| `IT.NET.USER.ZS` | Internet users (% of population) |
| `SP.URB.TOTL.IN.ZS` | Urban population (% of total) |
| `SL.TLF.CACT.FE.ZS` | Female labour force participation rate (%) |
| `NY.GNP.PCAP.CD` | GNI per capita, Atlas method (current US$) |

## Architecture

The pipeline follows a modular, layered architecture:

- **API Layer** (`api/`): Handles external communication with World Bank API
- **Core Layer** (`core/`): Business logic for ETL operations
- **CLI Layer** (`cli/`): User-facing command interface
- **EDA Layer** (`eda/`): Analysis and visualization functions
- **Utils Layer** (`utils/`): Cross-cutting concerns like logging

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## Configuration

All pipeline settings are centralized in `src/wdi_etl/core/config.py`:

- **Indicators**: Configure which World Bank indicators to fetch
- **Year Range**: Set YEAR_START and YEAR_END (default: 2014-2023)
- **Missing Values**: Configure MISSING_STRATEGY (drop, forward_fill, backward_fill, interpolate, keep)
- **Output Paths**: Customize OUTPUT_CSV and OUTPUT_PARQUET
- **Country Names**: Update COUNTRY_NAME_CORRECTIONS for standardization

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=wdi_etl --cov-report=html
```

## Documentation

- [Architecture](docs/architecture.md) - System architecture and design principles
- [API Reference](docs/api_reference.md) - Python API documentation
- [Usage Guide](docs/usage_guide.md) - Detailed usage instructions

## Requirements

- Python >= 3.10
- See `requirements.txt` or `pyproject.toml` for full dependencies

## Author

**Shankha Roy**

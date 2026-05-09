# World Bank WDI ETL Pipeline

Production-grade ETL pipeline for extracting, transforming, validating, and loading World Bank World Development Indicators (WDI) data (2014–2023).

## Features

- **Extract**: Fetches indicators from World Bank API with retry logic, exponential backoff, and rate limiting
- **Transform**: Cleans, validates, and creates a tidy panel dataset with configurable missing value strategies
- **Load**: Outputs to CSV (UTF-8 with BOM) and Parquet formats with optional Hive-style partitioning
- **EDA**: Comprehensive exploratory data analysis module with statistical summaries and visualizations
- **CLI**: Full-featured command-line interface with flexible options
- **Tested**: Unit and integration tests with 80%+ coverage target

## Project Structure

```
emri-capstone/
├── configs/                      # Configuration folder (placeholder for env-specific configs)
├── data/                         # Legacy data directory
│   ├── raw/                      # Cached raw JSON from World Bank API
│   └── output/                   # Final outputs (CSV, Parquet, EDA visualizations)
├── data_raw/                     # Raw input data for analysis
├── data_processed/               # Processed CSV outputs (classifications, complete datasets)
├── figures/                      # Analysis visualizations and plots (PNG)
├── models/                       # Trained model files (pickled classifiers)
├── docs/
│   ├── architecture.md           # System architecture documentation
│   ├── api_reference.md          # Python API reference
│   └── usage_guide.md            # Detailed usage instructions
├── logs/                         # Pipeline execution logs (rotating)
├── notebooks/
│   ├── wdi_eda.ipynb            # Basic EDA notebook
│   └── wdi_eda_professional.ipynb  # Professional EDA notebook
├── references/                   # API docs, data dictionaries
├── src/wdi_etl/                 # Main Python package (src-layout)
│   ├── __init__.py              # Public API exports
│   ├── __main__.py              # CLI entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── client.py            # World Bank API client with retry logic
│   ├── cli/
│   │   ├── __init__.py
│   │   └── commands.py          # CLI argument parsing and orchestration
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Centralized configuration
│   │   ├── load.py              # CSV & Parquet output writers
│   │   └── transform.py         # Data cleaning & validation
│   ├── eda/
│   │   ├── __init__.py
│   │   └── analysis.py          # Statistical analysis & visualizations
│   └── utils/
│       ├── __init__.py
│       └── logging_config.py     # Centralized logging setup
├── tests/                        # Test suite
│   ├── conftest.py              # Pytest fixtures
│   ├── fixtures/                # Test data files
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_pipeline.py     # End-to-end pipeline tests
│   └── unit/
│       ├── test_api/            # API client unit tests
│       ├── test_cli/            # CLI unit tests
│       ├── test_core/           # Core (config, transform, load) tests
│       └── test_utils/          # Utilities tests
├── pyproject.toml               # Project metadata, dependencies, tool configs
├── requirements.txt             # Production dependencies
└── README.md                    # This file
```

## Quick Start

### Prerequisites

- Python >= 3.10
- pip package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/shankharoy/emri-capstone.git
cd emri-capstone

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install in development mode (includes dev dependencies)
pip install -e ".[dev]"
```

### Run the Pipeline

```bash
# Full pipeline: Extract -> Transform -> Load
python -m wdi_etl

# Re-run without re-downloading (use cached data)
python -m wdi_etl --skip-extract

# Apply forward-fill for missing values
python -m wdi_etl --missing-strategy forward_fill

# Partition Parquet output by year
python -m wdi_etl --partition-by year

# See all options
python -m wdi_etl --help
```

### Run EDA

```bash
# Command-line EDA
python -m wdi_etl.eda

# Or use Jupyter notebook
jupyter notebook notebooks/wdi_eda_professional.ipynb
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=wdi_etl --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

## Indicators

The pipeline extracts these World Bank indicators:

| Code | Description |
|------|-------------|
| `NY.GDP.PCAP.CD` | GDP per capita (current US$) |
| `IT.NET.USER.ZS` | Internet users (% of population) |
| `SP.URB.TOTL.IN.ZS` | Urban population (% of total) |
| `SL.TLF.CACT.FE.ZS` | Female labour force participation rate (%) |
| `NY.GNP.PCAP.CD` | GNI per capita, Atlas method (current US$) |

## Configuration

All settings are centralized in `src/wdi_etl/core/config.py`:

```python
# Add new indicators
INDICATORS = {
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    # Add more indicators here
}

# Change time range
YEAR_START = 2014
YEAR_END = 2023

# Configure missing value strategy
MISSING_STRATEGY = "keep"  # Options: drop, forward_fill, backward_fill, interpolate, keep

# Customize output paths
OUTPUT_CSV = OUTPUT_DIR / "wdi_panel.csv"
OUTPUT_PARQUET = OUTPUT_DIR / "wdi_panel.parquet"
```

## Architecture

The pipeline follows a modular, layered architecture:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Extract   │────▶│  Transform  │────▶│    Load     │
│  (api/)     │     │  (core/)    │     │  (core/)    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
   Raw JSON            Tidy Panel          CSV/Parquet
   Cache (data/raw)    DataFrame           Output
```

**Design Principles:**
- **Single Responsibility**: Each module has one reason to change
- **Configuration as Code**: All settings in `core/config.py`
- **Fail Fast**: Validation at stage boundaries
- **Type Safety**: Full type hints throughout codebase

See [docs/architecture.md](docs/architecture.md) for detailed documentation.

## API Reference

### Public API

```python
from wdi_etl import extract_all, transform_all, load_panel

# Extract from World Bank API
raw_data = extract_all()

# Transform to tidy panel
panel = transform_all(raw_data, missing_strategy="forward_fill")

# Load to CSV/Parquet
outputs = load_panel(panel, partition_by="year")
```

### EDA Module

```python
from wdi_etl.eda import run_eda, summary_stats, missingness_report

# Run complete analysis
results = run_eda()

# Access individual results
print(results["summary_stats"])
print(results["correlation"])
```

See [docs/api_reference.md](docs/api_reference.md) for complete documentation.

## CLI Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--missing-strategy` | Missing value handling: drop, forward_fill, backward_fill, interpolate, keep | `keep` |
| `--skip-extract` | Use cached raw JSON instead of API calls | `False` |
| `--raw-dir` | Raw JSON cache directory | `data/raw` |
| `--interim-dir` | Intermediate files directory | `data/interim` |
| `--output-dir` | Output directory | `data/output` |
| `--partition-by` | Parquet partition column (e.g., 'year') | `None` |
| `--skip-parquet` | Skip Parquet output | `False` |
| `--log-level` | Console log level: DEBUG, INFO, WARNING, ERROR | `INFO` |

## Documentation

- [Architecture](docs/architecture.md) - System architecture and design patterns
- [API Reference](docs/api_reference.md) - Complete Python API documentation
- [Usage Guide](docs/usage_guide.md) - Detailed usage instructions and troubleshooting

## Development

### Code Quality

- **Formatter**: Black (line length 100)
- **Import Sorting**: isort (black profile)
- **Type Checking**: mypy (strict mode)
- **Linting**: flake8
- **Testing**: pytest with coverage

### Pre-commit Checks

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type check
mypy src/wdi_etl

# Run tests
pytest tests/ --cov=wdi_etl --cov-report=term-missing
```

## Requirements

**Production:**
- pandas >= 2.0.0
- requests >= 2.31.0
- pyarrow >= 14.0.0
- matplotlib >= 3.7.0
- seaborn >= 0.12.0

**Development:**
- pytest >= 7.4.0
- pytest-cov >= 4.1.0
- black >= 23.0.0
- flake8 >= 6.1.0
- mypy >= 1.5.0
- isort >= 5.12.0

See `pyproject.toml` and `requirements.txt` for full details.

## License

MIT License

## Author

**Shankha Roy**

Senior Data Engineer

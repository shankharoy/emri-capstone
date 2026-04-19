# Architecture Documentation

## Overview

The World Bank WDI ETL Pipeline follows a modular, layered architecture designed for maintainability, testability, and scalability. The codebase uses a src-layout structure with clear separation of concerns.

## Package Structure

```
src/wdi_etl/
├── __init__.py              # Package exports (extract_all, transform_all, load_panel)
├── __main__.py              # CLI entry point
├── api/                     # External API interaction layer
│   ├── __init__.py
│   └── client.py            # World Bank API client with retry logic
├── cli/                     # Command-line interface layer
│   ├── __init__.py
│   └── commands.py          # Argument parsing and orchestration
├── core/                    # Core business logic (ETL stages)
│   ├── __init__.py
│   ├── config.py            # Centralized configuration
│   ├── load.py              # Output generation (CSV/Parquet)
│   └── transform.py         # Data cleaning and validation
├── eda/                     # Exploratory data analysis layer
│   ├── __init__.py
│   └── analysis.py          # Statistical functions and reports
└── utils/                   # Shared utilities
    ├── __init__.py
    └── logging_config.py    # Logging setup
```

## Layer Responsibilities

### API Layer (`api/`)

**Purpose**: Handle all external communication with the World Bank API.

**Key Module**: `client.py`
- `fetch_indicator()` - Downloads all observations for one indicator
- `extract_all()` - Orchestrates extraction of all configured indicators
- Implements retry logic with exponential backoff (2^attempt seconds)
- Rate limiting (250ms between pages)
- Session reuse for TCP connection pooling

**Design Patterns**:
- Retry Pattern: Automatic retry on transient failures
- Circuit Breaker: Exponential backoff prevents API overload

### Core Layer (`core/`)

**Purpose**: Business logic for ETL operations.

**Modules**:

1. **config.py** - Centralized configuration
   - Single source of truth for all pipeline parameters
   - Type-annotated values catch errors before runtime
   - Sensible defaults for immediate execution
   - Environment variable override support

2. **transform.py** - Data cleaning and validation
   - Converts raw JSON to tidy panel DataFrame
   - Handles missing values with configurable strategies
   - Country name standardization
   - Data validation at stage boundaries

3. **load.py** - Output generation
   - Writes CSV and Parquet formats
   - Supports Hive-style partitioning
   - Configurable output paths

**Design Patterns**:
- Configuration as Code: All settings in one file
- Fail Fast: Validation at stage boundaries
- Strategy Pattern: Configurable missing value handling

### CLI Layer (`cli/`)

**Purpose**: User-facing command interface.

**Module**: `commands.py`
- `parse_args()` - Argument parsing with argparse
- `run()` - Pipeline orchestration and execution
- Entry point via `__main__.py`

**Features**:
- Skip extraction (--skip-extract)
- Missing value strategy selection
- Partitioned output options
- Configurable log levels
- Customizable directories

### EDA Layer (`eda/`)

**Purpose**: Analysis and visualization.

**Module**: `analysis.py`
- `run_eda()` - Complete exploratory analysis
- `summary_stats()` - Descriptive statistics
- `missingness_report()` - Data completeness analysis
- `coverage_by_country()` - Per-country data coverage
- `indicator_correlation()` - Cross-indicator correlation
- `top_bottom()` - Ranking functions

### Utils Layer (`utils/`)

**Purpose**: Cross-cutting concerns.

**Module**: `logging_config.py`
- Centralized logging setup
- Structured JSON logging
- File and console handlers
- Configurable log levels

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              ETL Pipeline                               │
└─────────────────────────────────────────────────────────────────────────┘

   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │   Extract   │────▶│  Transform  │────▶│    Load     │
   │  (api/)     │     │  (core/)    │     │  (core/)    │
   └─────────────┘     └─────────────┘     └─────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
     Raw JSON            Tidy Panel          CSV/Parquet
     Cache (data/raw)    DataFrame           Output
                                                (data/output)
```

## Detailed Flow

1. **Extract Phase**:
   - CLI parses arguments and calls `extract_all()`
   - For each indicator, `fetch_indicator()` paginates through API
   - Raw JSON cached to `data/raw/{indicator}.json`
   - Returns dict mapping indicator to records

2. **Transform Phase**:
   - `transform_all()` receives raw data dict
   - Normalizes records into tidy DataFrame
   - Applies country name corrections
   - Handles missing values per strategy
   - Validates data completeness
   - Returns panel DataFrame

3. **Load Phase**:
   - `load_panel()` receives panel DataFrame
   - Writes to CSV: `data/output/wdi_panel.csv`
   - Writes to Parquet: `data/output/wdi_panel.parquet`
   - Optional: Hive partitioning by column
   - Returns mapping of format to path

4. **EDA Phase** (optional):
   - `run_eda()` loads panel from disk
   - Generates statistical summaries
   - Creates visualizations
   - Outputs to console and saves plots

## Configuration System

All configuration is centralized in `core/config.py`:

```python
# Project paths
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
OUTPUT_DIR: Path = DATA_DIR / "output"
RAW_DIR: Path = DATA_DIR / "raw"

# API settings
WB_API_BASE: str = "https://api.worldbank.org/v2"
WB_PER_PAGE: int = 10_000

# Indicators to fetch
INDICATORS: dict[str, str] = {...}

# Time range
YEAR_START: int = 2014
YEAR_END: int = 2023

# Processing
MISSING_STRATEGY: Literal[...] = "keep"
MIN_COMPLETENESS_RATIO: float = 0.5
```

## Design Principles

1. **Single Responsibility**: Each module has one reason to change
2. **Dependency Inversion**: Higher layers depend on abstractions
3. **Configuration as Code**: All settings in `core/config.py`
4. **Fail Fast**: Validation at stage boundaries
5. **Immutability**: DataFrames not modified in place
6. **Explicit is Better than Implicit**: Clear function names, type hints

## Data Validation

Validation occurs at multiple points:

- **Extract**: Validate API response shape, check for required fields
- **Transform**: Validate completeness ratio, minimum countries
- **Load**: Validate output paths, check write permissions
- **EDA**: Validate file existence, data shape

## Error Handling

- **Retry Logic**: API calls retry 3x with exponential backoff
- **Graceful Degradation**: Optional features can be skipped
- **Informative Messages**: Clear error messages with context
- **Logging**: Full stack traces logged to file

## Testing Strategy

- **Unit Tests**: Individual functions in isolation
- **Integration Tests**: Full pipeline with mocked API
- **Test Data**: Fixtures in `conftest.py`
- **Coverage**: Minimum 80% code coverage

## Extension Points

To add new functionality:

1. **New Indicator**: Add to `INDICATORS` in `core/config.py`
2. **New Transform**: Add function to `core/transform.py`
3. **New Output Format**: Add to `core/load.py`
4. **New CLI Option**: Add to `cli/commands.py`
5. **New Analysis**: Add to `eda/analysis.py`

## Performance Considerations

- **Session Reuse**: API client reuses TCP connections
- **Streaming**: Large datasets processed in chunks
- **Caching**: Raw JSON cached to avoid re-downloads
- **Partitioning**: Parquet partitioned for efficient queries
- **Vectorization**: Pandas operations use vectorized numpy

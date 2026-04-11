# Architecture Documentation

## Overview

The World Bank WDI ETL Pipeline follows a modular, layered architecture designed for maintainability, testability, and scalability.

## Package Structure

```
src/wdi_etl/
├── api/            # External API interaction
├── core/           # Business logic (ETL stages)
├── cli/            # Command-line interface
├── eda/            # Exploratory data analysis
└── utils/          # Shared utilities
```

## Layer Responsibilities

### API Layer (`api/`)
- **Purpose**: Handle all external communication
- **Key Module**: `client.py` - World Bank API client with retry logic
- **Exports**: `extract_all()`, `fetch_indicator()`

### Core Layer (`core/`)
- **Purpose**: Business logic for ETL operations
- **Modules**:
  - `config.py` - Centralized configuration
  - `transform.py` - Data cleaning and validation
  - `load.py` - Output generation (CSV/Parquet)

### CLI Layer (`cli/`)
- **Purpose**: User-facing command interface
- **Module**: `commands.py` - Argument parsing and orchestration
- **Entry Point**: `__main__.py`

### EDA Layer (`eda/`)
- **Purpose**: Analysis and visualization
- **Module**: `analysis.py` - Statistical functions and reports

### Utils Layer (`utils/`)
- **Purpose**: Cross-cutting concerns
- **Module**: `logging_config.py` - Logging setup

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Extract   │────▶│  Transform  │────▶│    Load     │
│  (api/)     │     │  (core/)    │     │  (core/)    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
   Raw JSON            Tidy Panel          CSV/Parquet
   Cache               DataFrame           Output
```

## Design Principles

1. **Single Responsibility**: Each module has one reason to change
2. **Dependency Inversion**: Core logic depends on abstractions
3. **Configuration as Code**: All settings in `core/config.py`
4. **Fail Fast**: Validation at stage boundaries

## Backward Compatibility

Old import paths are preserved via deprecation shims:
- `wdi_etl.config` → `wdi_etl.core.config`
- `wdi_etl.extract` → `wdi_etl.api.client`
- etc.

"""
DEPRECATED: Configuration module re-export.
Use wdi_etl.core.config instead.
"""
import warnings

warnings.warn(
    "wdi_etl.config is deprecated. Use wdi_etl.core.config instead.",
    DeprecationWarning,
    stacklevel=2
)

from wdi_etl.core.config import *  # noqa: F401,F403

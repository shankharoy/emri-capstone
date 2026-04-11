"""
DEPRECATED: Logger module re-export.
Use wdi_etl.utils.logging_config instead.
"""
import warnings

warnings.warn(
    "wdi_etl.logger is deprecated. Use wdi_etl.utils.logging_config instead.",
    DeprecationWarning,
    stacklevel=2
)

from wdi_etl.utils.logging_config import *  # noqa: F401,F403

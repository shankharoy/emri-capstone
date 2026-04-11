"""
DEPRECATED: Load module re-export.
Use wdi_etl.core.load instead.
"""
import warnings

warnings.warn(
    "wdi_etl.load is deprecated. Use wdi_etl.core.load instead.",
    DeprecationWarning,
    stacklevel=2
)

from wdi_etl.core.load import *  # noqa: F401,F403

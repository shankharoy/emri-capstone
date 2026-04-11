"""
DEPRECATED: Extract module re-export.
Use wdi_etl.api.client instead.
"""
import warnings

warnings.warn(
    "wdi_etl.extract is deprecated. Use wdi_etl.api.client instead.",
    DeprecationWarning,
    stacklevel=2
)

from wdi_etl.api.client import *  # noqa: F401,F403

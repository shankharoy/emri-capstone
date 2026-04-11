"""
DEPRECATED: Transform module re-export.
Use wdi_etl.core.transform instead.
"""
import warnings

warnings.warn(
    "wdi_etl.transform is deprecated. Use wdi_etl.core.transform instead.",
    DeprecationWarning,
    stacklevel=2
)

from wdi_etl.core.transform import *  # noqa: F401,F403

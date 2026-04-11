"""
DEPRECATED: EDA module re-export.
Use wdi_etl.eda.analysis instead.
"""
import warnings

warnings.warn(
    "wdi_etl.eda is deprecated. Use wdi_etl.eda.analysis instead.",
    DeprecationWarning,
    stacklevel=2
)

from wdi_etl.eda.analysis import *  # noqa: F401,F403

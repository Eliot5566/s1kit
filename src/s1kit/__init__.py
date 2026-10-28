"""Test, calibrate and route System One decision models (any /v1/systemone endpoint)."""

__version__ = "0.2.0"

from .router import Router, RouterResult  # noqa: E402

__all__ = ["Router", "RouterResult", "__version__"]

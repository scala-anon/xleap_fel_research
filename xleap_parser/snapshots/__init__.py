"""Fetch binned PV snapshots over a time window via the MEME archive service.

Public API::

    from snapshots import RunConfig, fetch_pv

Run as a CLI::

    python -m snapshots --pvs pvs.csv --out snapshots.csv
"""
from __future__ import annotations

from .archive import fetch_pv, iso_utc, window_epoch
from .config import RunConfig

__all__ = ["RunConfig", "fetch_pv", "iso_utc", "window_epoch"]

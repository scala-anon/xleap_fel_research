"""Invariants for the XLEAP taper analysis.

Physics constants + the I/O contract. The undulator-line switch (HXR vs SXR)
lives in the top-level :mod:`beamlines` module -- the ONE knob shared with the
fetch side so the two can never disagree -- and is re-exported here so existing
imports (``from taper import DEFAULT_LINE`` / ``HXR`` / ``Beamline``) keep working.
"""
from __future__ import annotations

import re
from typing import Final

from beamlines import DEFAULT_LINE, HXR, SXR, Beamline  # noqa: F401 -- re-exported

# --- Physics -----------------------------------------------------------------
SPEED_OF_LIGHT_M_PER_S: Final[float] = 299_792_458.0  # c
ELECTRON_REST_ENERGY_MEV: Final[float] = 0.510_998_950_0  # m_e c^2
UNDULATOR_LENGTH_M: Final[float] = 3.4  # L_u, one undulator segment (HXR & SXR)

# Back-compat module aliases -- track the active line (beamlines.DEFAULT_LINE), so
# `from taper import KACT_PV_PATTERN` matches the same line the fetch/analysis uses.
KACT_PV_PATTERN: Final[re.Pattern[str]] = DEFAULT_LINE.kact_pattern
BEAM_MOMENTUM_PV: Final[str] = DEFAULT_LINE.momentum_pv

# --- I/O ---------------------------------------------------------------------
# Long-form snapshot CSV produced by ``python -m snapshots`` (columns:
# nominal_time, pv, timestamp, value). This is our data source of record.
DEFAULT_SNAPSHOT_CSV: Final[str] = "snapshots.csv"
SNAPSHOT_COLUMNS: Final[tuple[str, ...]] = ("nominal_time", "pv", "timestamp", "value")

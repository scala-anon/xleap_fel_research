"""Invariants for the snapshot fetcher.

The C analog of a ``config.h`` of ``#define``s -- but ONLY for things that never
change run-to-run. Anything you'd edit between runs (time window, operator,
protocol, jobs) is *configuration*, not a constant, and lives in
:mod:`snapshots.config` instead.
"""
from __future__ import annotations

from beamlines import DEFAULT_LINE

# Output CSV schema. These column names are the contract downstream
# `taper.SnapshotStore.from_csv` reads by name.
OUTPUT_HEADER = ["nominal_time", "pv", "timestamp", "value", "moved"]

# Default PV list follows the ONE line switch in beamlines.py, so the fetch can
# never disagree with the analysis: flip beamlines.DEFAULT_LINE and this tracks it
# (pvs_hxr.csv / pvs_sxr.csv). Override per run with `--pvs` if needed.
DEFAULT_PVS_CSV = DEFAULT_LINE.pvs_csv
DEFAULT_OUT_CSV = "snapshots.csv"

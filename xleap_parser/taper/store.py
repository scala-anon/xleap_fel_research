"""Load snapshot data into tidy pandas frames.

This is our replacement for the sparklines wide-SQLite store. That store kept a
long table AND a wide table with one ``ALTER TABLE ADD COLUMN`` per PV (~370
columns) plus a per-(row, PV) UPDATE on ingest -- schema-as-data, and slow. The
analysis only ever needs a ``time x undulator`` matrix and one gamma series, and
pandas pivots that from long form in one call. So we keep exactly one long,
normalized representation and pivot on demand:

    long snapshots.csv  ->  SnapshotStore  ->  .wide_values(pattern) / .series(pv)

``from_csv`` reads the CSV that ``python -m snapshots`` emits directly; the
optional SQLite path uses a single normalized table (no wide mirror).
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .constants import DEFAULT_SNAPSHOT_CSV, SNAPSHOT_COLUMNS

__all__ = ["SnapshotStore"]

_SQLITE_TABLE = "snapshots"
_MOVED = "moved"
_SPREAD = "spread"


def _sort_key(label: str) -> tuple[int, object]:
    """Order columns numerically when labels are ints, else lexically."""
    return (0, int(label)) if label.isdigit() else (1, label)


def _finalize(frame: pd.DataFrame) -> pd.DataFrame:
    """Coerce dtypes and guarantee ``moved`` (bool) and ``spread`` (float) columns.

    Both are optional add-ons from the snapshots probe pass: legacy CSV/SQLite
    predating them default to ``False`` / ``NaN``. Bool-from-text is parsed
    leniently so ``"True"``/``"False"``/``1``/``0`` all round-trip through a CSV;
    ``NaN`` spread means 'unknown', so the energy-stability gate simply won't fire.
    """
    frame["nominal_time"] = pd.to_datetime(frame["nominal_time"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame["value"] = frame["value"].astype(float)
    if _MOVED in frame.columns:
        frame[_MOVED] = (
            frame[_MOVED].astype(str).str.strip().str.lower().isin(("true", "1"))
        )
    else:
        frame[_MOVED] = False
    if _SPREAD in frame.columns:
        frame[_SPREAD] = pd.to_numeric(frame[_SPREAD], errors="coerce")
    else:
        frame[_SPREAD] = float("nan")
    return frame.loc[:, [*SNAPSHOT_COLUMNS, _MOVED, _SPREAD]]


@dataclass(frozen=True)
class SnapshotStore:
    """Long-form snapshots: one row per (nominal_time, pv).

    ``frame`` columns: ``nominal_time`` (datetime64), ``pv`` (str),
    ``timestamp`` (datetime64, when the sample was actually taken), ``value``
    (float). Build with :meth:`from_csv`; reshape with :meth:`wide_values` /
    :meth:`series`.
    """

    frame: pd.DataFrame

    # --- constructors --------------------------------------------------------
    @classmethod
    def from_csv(cls, path: str | Path = DEFAULT_SNAPSHOT_CSV) -> "SnapshotStore":
        """Read the long snapshot CSV produced by ``python -m snapshots``."""
        frame = pd.read_csv(path)
        missing = set(SNAPSHOT_COLUMNS) - set(frame.columns)
        if missing:
            raise ValueError(f"{path} missing columns {sorted(missing)}")
        return cls(_finalize(frame))

    @classmethod
    def from_sqlite(
        cls, path: str | Path, *, table: str = _SQLITE_TABLE
    ) -> "SnapshotStore":
        """Read the normalized single-table SQLite written by :meth:`write_sqlite`."""
        with sqlite3.connect(path) as connection:
            frame = pd.read_sql_query(f"SELECT * FROM {table}", connection)
        return cls(_finalize(frame))

    # --- reshaping -----------------------------------------------------------
    def _pivot(self, field: str) -> pd.DataFrame:
        wide = self.frame.pivot_table(
            index="nominal_time", columns="pv", values=field, aggfunc="first"
        )
        return wide.sort_index()

    def wide_values(
        self, pattern: re.Pattern[str], *, by_group: bool = True
    ) -> pd.DataFrame:
        """Pivot to a ``time x column`` matrix of matched-PV values.

        Only PVs fully matching ``pattern`` are kept. With ``by_group`` the
        column label is the pattern's first capture group (e.g. the undulator
        number); otherwise it is the full PV name. Columns sort naturally.
        """
        return self._reshape(self._pivot("value"), pattern, by_group)

    def wide_timestamps(
        self, pattern: re.Pattern[str], *, by_group: bool = True
    ) -> pd.DataFrame:
        """Same shape as :meth:`wide_values`, holding each sample's real time."""
        return self._reshape(self._pivot("timestamp"), pattern, by_group)

    def wide_moved(
        self, pattern: re.Pattern[str], *, by_group: bool = True
    ) -> pd.DataFrame:
        """Boolean ``time x column`` frame: True where that PV moved in-window.

        Same shape/labelling as :meth:`wide_values`. Aggregates with ``max`` (any
        moving sample in a bin marks it moving) over an int view -- pandas
        ``pivot_table`` silently drops raw bool value columns. Missing cells
        default to ``False`` (a PV absent at a time was not observed moving).
        """
        ints = self.frame.assign(**{_MOVED: self.frame[_MOVED].astype(int)})
        wide = ints.pivot_table(
            index="nominal_time", columns="pv", values=_MOVED, aggfunc="max"
        ).sort_index()
        return self._reshape(wide, pattern, by_group).fillna(0).astype(bool)

    @staticmethod
    def _reshape(
        wide: pd.DataFrame, pattern: re.Pattern[str], by_group: bool
    ) -> pd.DataFrame:
        labels: dict[str, str] = {}
        for pv in wide.columns:
            match = pattern.fullmatch(pv)
            if match is None:
                continue
            labels[pv] = match.group(1) if by_group else pv
        selected = wide.loc[:, list(labels)].rename(columns=labels)
        selected = selected.loc[:, sorted(selected.columns, key=_sort_key)]
        selected.columns.name = "Undulator" if by_group else "PV"
        selected.index.name = "nominal_time"
        return selected

    def series(self, pv: str) -> pd.Series:
        """Value time series for a single PV, indexed by nominal time."""
        rows = self.frame.loc[self.frame["pv"] == pv, ["nominal_time", "value"]]
        return rows.set_index("nominal_time")["value"].sort_index()

    def spread_series(self, pv: str) -> pd.Series:
        """Intra-bin fractional spread for a single PV, indexed by nominal time.

        ``NaN`` where unavailable (legacy data without a ``spread`` column) --
        callers treat ``NaN`` as 'unknown', so the energy-stability gate does not
        fire on data fetched before spread was recorded.
        """
        rows = self.frame.loc[self.frame["pv"] == pv, ["nominal_time", _SPREAD]]
        return rows.set_index("nominal_time")[_SPREAD].sort_index()

    # --- persistence ---------------------------------------------------------
    def write_sqlite(self, path: str | Path, *, table: str = _SQLITE_TABLE) -> int:
        """Write one normalized long table (no wide mirror). Returns row count."""
        with sqlite3.connect(path) as connection:
            out = self.frame.copy()
            out["nominal_time"] = out["nominal_time"].astype(str)
            out["timestamp"] = out["timestamp"].astype(str)
            out.to_sql(table, connection, if_exists="replace", index=False)
            connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_pv_time "
                f"ON {table} (pv, nominal_time)"
            )
        return len(self.frame)

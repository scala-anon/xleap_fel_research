"""Assemble the XLEAP timeline -- the notebook's ``get_xleap_data``, as an API.

For each nominal time in the store this reports whether XLEAP is on, which
undulators lase, and the taper of the first (most-upstream) lasing group. The
heavy lifting lives in :mod:`taper.detect` and :mod:`taper.physics`; this module
only wires the wide K matrix and the gamma series together per time point.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from .constants import DEFAULT_LINE, Beamline
from .detect import DetectionParams, first_group, lasing_kvals
from .physics import gamma_from_momentum_gev, taper_mev_per_fs
from .store import SnapshotStore

__all__ = ["XleapPoint", "xleap_timeline", "timeline_frame"]


@dataclass(frozen=True)
class XleapPoint:
    """One nominal time's XLEAP verdict.

    ``taper`` is the first lasing group's taper in MeV/fs (NaN when off or when
    gamma is unavailable). ``k_lasing`` maps undulator number -> K over every
    lasing undulator at this time. ``moving`` is True when an undulator was being
    moved in this window; such a point is force-cleared (no taper, no XLEAP) but
    kept visible rather than silently dropped.
    """

    datetime: datetime
    xleap_on: bool
    k_lasing: dict[str, float]
    n_und: int
    taper: float
    moving: bool = False

    def as_dict(self) -> dict[str, Any]:
        """The notebook's documented data object (``K_lasing`` spelling kept)."""
        return {
            "datetime": self.datetime,
            "xleap_on": self.xleap_on,
            "K_lasing": self.k_lasing,
            "n_und": self.n_und,
            "taper": self.taper,
            "moving": self.moving,
        }


def _group_taper(group: pd.Series, gamma: float) -> float:
    """Median-dK taper of one lasing group at beam energy ``gamma``."""
    if len(group) < 2 or not np.isfinite(gamma):
        return float("nan")
    dK = group.diff().dropna().median()
    K = float(group.iloc[0])
    if not np.isfinite(dK):
        return float("nan")
    return float(taper_mev_per_fs(dK, K, gamma))


def xleap_timeline(
    store: SnapshotStore,
    *,
    line: Beamline = DEFAULT_LINE,
    params: DetectionParams = DetectionParams(),
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[XleapPoint]:
    """XLEAP verdict per nominal time in ``store`` (optionally clipped to a window).

    ``line`` selects the undulator line's PV naming (``HXR`` or ``SXR``).
    """
    kvals = store.wide_values(line.kact_pattern)
    if start is not None:
        kvals = kvals.loc[kvals.index >= pd.Timestamp(start)]
    if end is not None:
        kvals = kvals.loc[kvals.index <= pd.Timestamp(end)]

    momentum = store.series(line.momentum_pv).reindex(kvals.index)
    gamma = pd.Series(gamma_from_momentum_gev(momentum.to_numpy()), index=kvals.index)

    masked = lasing_kvals(kvals, params)
    moved = store.wide_moved(line.kact_pattern)
    moving_any = moved.any(axis=1).reindex(kvals.index, fill_value=False)

    points: list[XleapPoint] = []
    for time, row in masked.iterrows():
        if bool(moving_any.loc[time]):
            # Undulators were moving in this window: don't trust a taper here
            # (Aaron). Force-clear but keep the point flagged, not dropped.
            points.append(
                XleapPoint(
                    datetime=time.to_pydatetime(),
                    xleap_on=False,
                    k_lasing={},
                    n_und=0,
                    taper=float("nan"),
                    moving=True,
                )
            )
            continue
        lasing = row.dropna()
        k_lasing = {str(und): float(k) for und, k in lasing.items()}
        taper = _group_taper(first_group(row), float(gamma.loc[time]))
        points.append(
            XleapPoint(
                datetime=time.to_pydatetime(),
                xleap_on=bool(k_lasing),
                k_lasing=k_lasing,
                n_und=len(k_lasing),
                taper=taper,
                moving=False,
            )
        )
    return points


def timeline_frame(points: list[XleapPoint]) -> pd.DataFrame:
    """Tabulate a timeline for plotting: index = datetime, sorted ascending."""
    frame = pd.DataFrame(
        {
            "xleap_on": [p.xleap_on for p in points],
            "n_und": [p.n_und for p in points],
            "taper": [p.taper for p in points],
            "moving": [p.moving for p in points],
        },
        index=pd.DatetimeIndex([p.datetime for p in points], name="datetime"),
    )
    return frame.sort_index()

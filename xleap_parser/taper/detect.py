"""Detect lasing (tapered) undulator groups from a wide K matrix.

XLEAP shows up as a "hockey stick": a run of >= ``min_group`` undulators whose K
climbs by at least ``rho * rho_scale`` from one to the next. We build a boolean
"is this step big enough" mask along the undulator axis, then use binary erosion
+ dilation to keep only runs of the required length -- morphological opening,
the vectorized way to say "at least N in a row".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.ndimage import binary_dilation, binary_erosion

__all__ = ["DetectionParams", "lasing_mask", "lasing_kvals", "first_group"]


@dataclass(frozen=True)
class DetectionParams:
    """Thresholds for the hockey-stick search (immutable; pass one around).

    ``rho`` is the FEL Pierce parameter (~1e-3); a real taper steps K by several
    ``rho`` per undulator, so the step threshold is ``rho * rho_scale``.
    """

    rho: float = 1.0e-3
    rho_scale: float = 4.0
    min_group: int = 4

    @property
    def dk_threshold(self) -> float:
        """Minimum per-undulator K increase counted as tapered."""
        return self.rho * self.rho_scale


def _keep_long_runs(row: NDArray[np.bool_], min_len: int) -> NDArray[np.bool_]:
    """Morphological opening: keep only True runs of length >= ``min_len``."""
    structure = np.ones(min_len, dtype=bool)
    return binary_dilation(
        binary_erosion(row, structure=structure), structure=structure
    )


def lasing_mask(
    kvals: pd.DataFrame, params: DetectionParams = DetectionParams()
) -> pd.DataFrame:
    """Boolean frame (time x undulator): True where an undulator is lasing.

    ``kvals`` is indexed by nominal time with one column per undulator, ordered
    upstream -> downstream. The returned mask marks every undulator in a lasing
    group, including the base undulator just before the first big step (the K
    step ``dK[i]`` describes the rise from undulator ``i-1`` to ``i``, so the
    group of K values owns one more undulator on its upstream edge).
    """
    steps = kvals.diff(axis=1)  # dK[i] = K[i] - K[i-1] along undulators
    big_step = (steps >= params.dk_threshold).fillna(False)

    dk_runs = big_step.apply(
        lambda row: _keep_long_runs(row.to_numpy(dtype=bool), params.min_group),
        axis=1,
        result_type="expand",
    )
    dk_runs.index, dk_runs.columns = kvals.index, kvals.columns

    left_edges = dk_runs & ~dk_runs.shift(1, axis=1, fill_value=False)
    return dk_runs | left_edges.shift(-1, axis=1, fill_value=False)


def lasing_kvals(
    kvals: pd.DataFrame, params: DetectionParams = DetectionParams()
) -> pd.DataFrame:
    """``kvals`` with non-lasing entries blanked to NaN."""
    return kvals.where(lasing_mask(kvals, params))


def first_group(row: pd.Series) -> pd.Series:
    """Most-upstream contiguous run of non-NaN K in one masked time row.

    Returns an empty Series (preserving dtype) when nothing is lasing.
    """
    present = row.notna()
    if not present.any():
        return row.iloc[:0]
    group_id = present.ne(present.shift(fill_value=False)).cumsum()
    first_id = group_id[present].iloc[0]
    return row[present & (group_id == first_id)]

"""THE undulator-line switch -- the single knob to flip (HXR <-> SXR).

Both sides of the tool read ``DEFAULT_LINE`` from here, so the fetched PV list and
the analysis' PV parsing can never disagree:

    * fetch    -- ``snapshots.constants.DEFAULT_PVS_CSV`` = ``DEFAULT_LINE.pvs_csv``
    * analysis -- ``taper.xleap_timeline(..., line=DEFAULT_LINE)`` (notebook default)

To switch lines: set ``DEFAULT_LINE`` at the bottom to ``HXR`` or ``SXR``, then
re-fetch and re-run. Nothing else needs editing.

Kept dependency-free (stdlib only) on purpose, so the light ``snapshots`` fetcher
can import it without pulling in numpy/pandas/scipy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Beamline:
    """Line-specific PV naming for one undulator line (HXR vs SXR).

    ``kact_pattern``'s first capture group is the undulator number. ``momentum_pv``
    is the dump-magnet momentum in GeV/c that gives gamma (DMPH = hard line,
    DMPS = soft line).
    """

    name: str
    kact_pattern: re.Pattern[str]
    momentum_pv: str

    @property
    def pvs_csv(self) -> str:
        """Fetch PV-list filename for this line (``pvs_hxr.csv`` / ``pvs_sxr.csv``)."""
        return f"pvs_{self.name.lower()}.csv"


HXR: Final[Beamline] = Beamline(
    name="HXR",
    kact_pattern=re.compile(r"USEG:UNDH:(\d+):KAct"),
    momentum_pv="BEND:DMPH:400:BACT",
)
SXR: Final[Beamline] = Beamline(
    name="SXR",
    kact_pattern=re.compile(r"USEG:UNDS:(\d+):KAct"),
    momentum_pv="BEND:DMPS:400:BACT",
)

# ============================================================================
#  THE ONE SWITCH  --  set to HXR or SXR, then re-fetch and re-run. Nothing else.
# ============================================================================
DEFAULT_LINE: Final[Beamline] = SXR

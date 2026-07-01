"""Run parameters for a fetch -- the values you tweak per run.

A frozen dataclass is the Pythonic ``config.h``: the config is a *value you pass
around*, not module-global state (which is the import-time-coupling trap a
shared "globals module" would reintroduce). ``fetch_pv`` takes a ``RunConfig``;
nothing mutates a global.

Precedence, low -> high: dataclass defaults -> optional TOML file -> CLI flags.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace


@dataclass(frozen=True)
class RunConfig:
    """One fetch's parameters. Defaults reproduce the original script's window."""

    from_time: str = "2018-01-10T22:00:00.000Z"  # ISO8601 UTC (Zulu)
    to_time: str = "2018-01-11T08:00:00.000Z"
    bin_seconds: int = 900  # 15-min nominal grid
    operator: str = "firstSample_900"  # server-side bin op; "" => raw samples
    protocol: str = "PVA"  # MEME transport: "PVA" (EPICS v4) or "HTTP" (appliance)
    timeout: float = 60.0
    snapshot_delta_s: float = 5.0  # motion window after each nominal time (s); <=0 disables
    motion_threshold: float = 1.0e-3  # fractional (max-min)/median over the window => "moved" //TODO make this either 1.0e-3 or 1.0-4

    def merged(self, **overrides) -> "RunConfig":
        """Return a copy with the non-``None`` overrides applied.

        ``None`` means "not specified at this layer" so CLI flags that default to
        ``None`` fall through to the TOML/dataclass value cleanly.
        """
        clean = {key: val for key, val in overrides.items() if val is not None}
        return replace(self, **clean)


def load_toml(path: str) -> dict:
    """Load a TOML file into a dict of ``RunConfig`` overrides.

    Validates keys against the dataclass so a typo'd key fails loudly instead of
    being silently ignored.
    """
    try:
        import tomllib
    except ModuleNotFoundError as exc:  # Python < 3.11
        raise RuntimeError(
            "TOML config needs Python 3.11+ (tomllib); pass flags directly instead"
        ) from exc

    with open(path, "rb") as fh:
        table = tomllib.load(fh)

    known = {f.name for f in fields(RunConfig)}
    unknown = set(table) - known
    if unknown:
        raise ValueError(f"unknown config keys in {path}: {sorted(unknown)}")
    return table

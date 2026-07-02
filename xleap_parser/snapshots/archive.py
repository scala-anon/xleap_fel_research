"""Fetch + bin PV history via the MEME archive service.

The pure-logic "library" layer (the analog of a C translation unit): it takes a
:class:`~snapshots.config.RunConfig` and returns rows. No argv parsing, no
``print``, no file writes -- those belong to :mod:`snapshots.__main__`. That
separation is what makes this unit-testable.
"""
from __future__ import annotations

import calendar
import math
import statistics
import time
from datetime import datetime, timezone

from .config import RunConfig


def iso_utc(secs: int) -> str:
    """UTC wall-clock ISO (naive, no tz suffix) for an epoch-seconds value."""
    return (
        datetime.fromtimestamp(secs, tz=timezone.utc).replace(tzinfo=None).isoformat()
    )


def window_epoch(from_time: str) -> int:
    """Epoch seconds of the window start.

    The archiver prepends one at-or-before boundary sample (~1s before the start)
    that we drop so it doesn't make a pre-window row.
    """
    return calendar.timegm(time.strptime(from_time[:19], "%Y-%m-%dT%H:%M:%S"))


def utc_datetime(iso_zulu: str) -> datetime:
    """Parse an ISO8601 Zulu string to a UTC-*aware* datetime.

    We hand meme.archive.get a datetime whose ``tzname()`` is ``"UTC"`` rather
    than the raw string. meme parses strings with ``dateparser``, which yields an
    aware datetime whose tzname is not literally ``"UTC"``; that trips meme's
    guard into ``convert_datetime_to_UTC`` on an already-aware value and raises
    "Not naive datetime (tzinfo is already set)". A ``timezone.utc`` datetime
    satisfies meme's UTC/GMT check, so it skips that broken path.
    """
    return datetime.strptime(iso_zulu[:19], "%Y-%m-%dT%H:%M:%S").replace(
        tzinfo=timezone.utc
    )


def _series(data) -> tuple:
    """Normalize a single-PV ``meme.archive.get`` payload to (secs, values).

    Unwraps the nested ``value`` layers that differ between the HTTP and PVA
    transports until the leaf columns are found.
    """
    node = data
    for _ in range(4):
        if isinstance(node, dict) and "secondsPastEpoch" in node and "values" in node:
            return node["secondsPastEpoch"], node["values"]
        if isinstance(node, dict) and "value" in node:
            node = node["value"]
        else:
            break
    shape = list(data) if isinstance(data, dict) else type(data).__name__
    raise ValueError(f"unrecognized archive payload shape: {shape}")


def _get_series(query: str, cfg: RunConfig) -> tuple:
    """Run one ``meme.archive.get`` and normalize it to ``(secs, values)``.

    ``meme.archive`` is imported lazily so the pure motion helpers below (and
    their tests) do not need the archive client installed.
    """
    import meme.archive

    data = meme.archive.get(
        query,
        from_time=utc_datetime(cfg.from_time),
        to_time=utc_datetime(cfg.to_time),
        timeout=cfg.timeout,
        protocol=cfg.protocol,
    )
    return _series(data)


def _window_moved(values: list[float], threshold: float) -> bool:
    """Did a PV move within one snapshot window?

    ``moved`` when the fractional spread ``(max - min) / |median|`` over the
    window's raw samples exceeds ``threshold``. A window with <= 1 sample cannot
    show a spread, so it is stationary (Aaron: a unique value in the interval =>
    stationary / thermal noise, regardless of archive cadence).
    """
    if len(values) <= 1:
        return False
    median = statistics.median(values)
    spread = max(values) - min(values)
    if median == 0.0:  # guard the (physically impossible for K) zero-median case
        return spread > threshold
    return spread / abs(median) > threshold


def _motion_by_bucket(secs_arr, vals_arr, cfg: RunConfig) -> dict[int, bool]:
    """Map each bin's start epoch -> whether the PV moved within ``[t, t+delta]``.

    ``secs_arr``/``vals_arr`` are the RAW (unbinned) samples for one PV over the
    whole window. Each sample is assigned to its bin, but only samples landing
    within ``snapshot_delta_s`` of the bin start count toward that bin's motion
    window -- equivalent to a per-nominal-time raw fetch over ``[t, t+delta]``,
    done as one stream so we pay one round-trip per PV instead of one per bin.
    """
    from_epoch = window_epoch(cfg.from_time)
    windows: dict[int, list[float]] = {}
    for secs, val in zip(secs_arr, vals_arr):
        if val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        s = int(secs)
        if s < from_epoch:  # drop the prepended pre-window boundary sample
            continue
        bucket = (s // cfg.bin_seconds) * cfg.bin_seconds
        if s - bucket <= cfg.snapshot_delta_s:
            windows.setdefault(bucket, []).append(float(val))
    return {
        bucket: _window_moved(vals, cfg.motion_threshold)
        for bucket, vals in windows.items()
    }


def _fetch_motion(pv: str, cfg: RunConfig) -> dict[int, bool]:
    """Per-bin motion map for ``pv`` from a raw (no-operator) fetch.

    Returns an empty map (all stationary) when motion is disabled or the raw
    fetch fails -- a motion probe must never drop or mask a value row.
    """
    if cfg.snapshot_delta_s <= 0:
        return {}
    try:
        secs_arr, vals_arr = _get_series(pv, cfg)  # bare PV name => raw samples
    except Exception:  # noqa: BLE001 - a motion-probe failure just means "unknown"
        return {}
    if secs_arr is None or len(secs_arr) == 0:
        return {}
    return _motion_by_bucket(secs_arr, vals_arr, cfg)


def fetch_pv(pv: str, cfg: RunConfig) -> tuple[str, list, str]:
    """Fetch one PV -> ``(nominal_time, pv, timestamp, value, moved)`` rows.

    The value pass bins the operator-reduced samples (first sample per bin); the
    motion pass flags each bin whose PV moved within ``snapshot_delta_s`` of the
    nominal time (Aaron's rule: motion => don't trust a taper there). Returns
    ``(pv, rows, status)``; status is 'ok', 'empty', or 'error: ...'.
    """
    from_epoch = window_epoch(cfg.from_time)
    query = f"{cfg.bin_operator}({pv})" if cfg.bin_operator else pv
    try:
        secs_arr, vals_arr = _get_series(query, cfg)
    except Exception as exc:  # noqa: BLE001 - report any I/O/parse failure per PV
        return pv, [], f"error: {exc}"

    if secs_arr is None or len(secs_arr) == 0:
        return pv, [], "empty"

    # Keep the FIRST sample per bucket = value as of the bin's nominal time.
    by_bucket: dict[int, tuple[int, float]] = {}
    for secs, val in zip(secs_arr, vals_arr):
        if val is None or (isinstance(val, float) and math.isnan(val)):
            continue
        s = int(secs)
        if s < from_epoch:  # drop the prepended pre-window boundary sample
            continue
        bucket = (s // cfg.bin_seconds) * cfg.bin_seconds
        if bucket not in by_bucket:  # data is time-ordered; first wins
            by_bucket[bucket] = (s, val)

    moved_by_bucket = _fetch_motion(pv, cfg)
    rows = [
        (iso_utc(bucket), pv, iso_utc(s), float(val), moved_by_bucket.get(bucket, False))
        for bucket, (s, val) in sorted(by_bucket.items())
    ]
    return pv, rows, "ok" if rows else "empty"

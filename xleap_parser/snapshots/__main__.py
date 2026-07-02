"""CLI entrypoint: ``python -m snapshots``.

The analog of a C ``main.c``: owns argv parsing, CSV read/write, the threadpool,
and progress output. All archive logic lives in :mod:`snapshots.archive`.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import constants
from .archive import fetch_pv
from .config import RunConfig, load_toml


def read_pvs(path: str) -> list[str]:
    """Read PV names from a CSV. Skips blanks and a leading `PV` header row."""
    pvs: list[str] = []
    with open(path, newline="") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            name = row[0].strip()
            if not name or name.upper() == "PV":  # skip header / blank lines
                continue
            pvs.append(name)
    return pvs


def build_config(args: argparse.Namespace) -> RunConfig:
    """Layer config: dataclass defaults -> TOML file -> CLI flags."""
    cfg = RunConfig()
    if args.config:
        cfg = cfg.merged(**load_toml(args.config))
    return cfg.merged(
        from_time=args.from_time,
        to_time=args.to_time,
        operator=args.operator,
        protocol=args.protocol,
        bin_seconds=args.bin_seconds,
        timeout=args.timeout,
    )


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m snapshots",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # I/O plumbing
    p.add_argument(
        "-p", "--pvs", default=constants.DEFAULT_PVS_CSV,
        help=f"input CSV of PV names (default: {constants.DEFAULT_PVS_CSV})",
    )
    p.add_argument(
        "-o", "--out", default=constants.DEFAULT_OUT_CSV,
        help=f"output CSV (default: {constants.DEFAULT_OUT_CSV})",
    )
    p.add_argument(
        "-c", "--config", default=None,
        help="optional TOML file of run parameters (overridden by flags below)",
    )
    p.add_argument(
        "-j", "--jobs", type=int,
        default=int(os.environ["JOBS"]) if os.environ.get("JOBS") else 16,
        help="concurrent requests (default: 16 or $JOBS)",
    )
    # RunConfig overrides; default None so they fall through to TOML/dataclass.
    p.add_argument("--from", dest="from_time", default=None, help="window start, ISO8601 UTC")
    p.add_argument("--to", dest="to_time", default=None, help="window end, ISO8601 UTC")
    p.add_argument("--operator", default=None, help='bin-reduction fn (binned at --bin-seconds), or "" for raw')
    p.add_argument("--protocol", default=None, choices=["PVA", "HTTP"], help="MEME transport")
    p.add_argument("--bin-seconds", type=int, default=None, help="bin width in seconds")
    p.add_argument("--timeout", type=float, default=None, help="per-request timeout (s)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = build_config(args)

    pvs = read_pvs(args.pvs)
    print(
        f"Fetching {len(pvs)} PVs from {args.pvs}  [{cfg.from_time} .. {cfg.to_time}]  "
        f"op={cfg.bin_operator or 'raw'}  proto={cfg.protocol}  jobs={args.jobs}"
    )

    all_rows: list[tuple] = []
    n_empty = n_err = 0
    done = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(fetch_pv, pv, cfg): pv for pv in pvs}
        for fut in as_completed(futures):
            pv, rows, status = fut.result()
            done += 1
            if status == "ok":
                all_rows.extend(rows)
            elif status == "empty":
                n_empty += 1
            else:
                n_err += 1
                print(f"  [{done}/{len(pvs)}] {pv:30s} {status}", file=sys.stderr)
            if done % 50 == 0 or done == len(pvs):
                print(f"  ...{done}/{len(pvs)} done")

    all_rows.sort(key=lambda r: (r[0], r[1]))  # (nominal_time, pv) -> deterministic
    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(constants.OUTPUT_HEADER)
        w.writerows(all_rows)

    print(
        f"\nDone. rows={len(all_rows)}  empty_pvs={n_empty}  errors={n_err}  -> {args.out}"
    )
    return 1 if n_err else 0


if __name__ == "__main__":
    raise SystemExit(main())

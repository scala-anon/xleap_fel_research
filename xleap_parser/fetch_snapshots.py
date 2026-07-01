#!/usr/bin/env python3
"""Backwards-compatible shim -- the implementation now lives in the `snapshots`
package. Prefer `python -m snapshots`; this keeps `python fetch_snapshots.py`
(and existing scripts) working.
"""
from snapshots.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())

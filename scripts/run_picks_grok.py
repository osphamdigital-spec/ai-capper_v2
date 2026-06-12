#!/usr/bin/env python
"""
scripts/run_picks_grok.py

Wrapper that runs the full picks pipeline for Grok on today's MLB slate:
  1. query_model.py  -- sends the prompt to the Grok API, saves raw response
  2. log_picks.py    -- parses the raw response into structured JSON

Usage:
    python scripts/run_picks_grok.py
    python scripts/run_picks_grok.py --date 2026-06-09

Arguments:
    --date   Override slate date (YYYY-MM-DD). Default: today in US Eastern Time.
    --sport  Sport code (default: mlb).

The script stops and prints an error if either step fails.
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

SCRIPTS_DIR  = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent

# Must match the Python install used by run_daily.py and query_model.py
PYTHON = r"C:\Users\marko\AppData\Local\Programs\Python\Python312\python.exe"

MODEL = "grok"


# ─────────────────────────────────────────────────────────────────────────────
# DATE HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from tz_util import ET
        return datetime.now(ET).strftime("%Y-%m-%d")
    except ImportError:
        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")
        return datetime.now(et).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# STEP RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_step(label: str, cmd: list) -> tuple[bool, float]:
    """
    Run a subprocess command, stream output to the terminal, and return
    (success, elapsed_seconds). Stops the pipeline on failure.
    """
    print(f"\n{'-' * 55}")
    print(f"  {label}")
    print(f"{'-' * 55}")

    t0     = time.time()
    result = subprocess.run(cmd)
    elapsed = time.time() - t0

    ok = result.returncode == 0
    if not ok:
        print(f"\n  FAILED (exit code {result.returncode})")
    return ok, elapsed


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run Grok picks query then log_picks for today's MLB slate."
    )
    parser.add_argument("--date",  default=None,
                        help="Slate date YYYY-MM-DD (default: today in US Eastern Time)")
    parser.add_argument("--sport", default="mlb",
                        help="Sport code (default: mlb)")
    args   = parser.parse_args()
    date   = args.date or _today_et()
    sport  = args.sport

    raw_path = PROJECT_ROOT / "picks" / sport / date / f"{MODEL}_raw.txt"

    print(f"\n{'=' * 55}")
    print(f"  GROK PICKS PIPELINE  {sport.upper()}  {date}")
    print(f"{'=' * 55}")

    wall_start = time.time()

    # ── Step 1: query_model.py ────────────────────────────────────────────
    ok, t1 = run_step(
        f"STEP 1: Query Grok API  ({date})",
        [
            PYTHON, str(SCRIPTS_DIR / "query_model.py"),
            "--model", MODEL,
            "--sport", sport,
            "--date",  date,
        ]
    )
    if not ok:
        print(f"\n  Pipeline stopped at Step 1.")
        print(f"  Check the error above, fix it, then re-run:")
        print(f'    python scripts/run_picks_grok.py --date {date}')
        sys.exit(1)

    # ── Step 2: log_picks.py ──────────────────────────────────────────────
    ok, t2 = run_step(
        f"STEP 2: Parse and log picks  ({date})",
        [
            PYTHON, str(SCRIPTS_DIR / "log_picks.py"),
            "--model", MODEL,
            "--sport", sport,
            "--date",  date,
            "--input", str(raw_path),
        ]
    )
    if not ok:
        print(f"\n  Pipeline stopped at Step 2.")
        print(f"  The raw response was saved to: {raw_path}")
        print(f"  Fix the parser error above, then run log_picks.py manually:")
        print(f'    python scripts/log_picks.py --model {MODEL} --sport {sport} --date {date} --input "{raw_path}"')
        sys.exit(1)

    # ── Summary ───────────────────────────────────────────────────────────
    total = time.time() - wall_start
    json_path = PROJECT_ROOT / "picks" / sport / date / f"{MODEL}.json"

    print(f"\n{'=' * 55}")
    print(f"  GROK PICKS PIPELINE  COMPLETE")
    print(f"{'=' * 55}")
    print(f"  Step 1 (query)  : {t1:.1f}s  -- {raw_path.name}")
    print(f"  Step 2 (log)    : {t2:.1f}s  -- {json_path.name}")
    print(f"  Total           : {total:.0f}s")
    print()
    if json_path.exists():
        print(f"  Structured picks: {json_path}")
    print(f"  Raw response    : {raw_path}")
    print(f"\n{'=' * 55}\n")


if __name__ == "__main__":
    main()

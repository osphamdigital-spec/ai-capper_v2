#!/usr/bin/env python
"""
scripts/run_picks_all.py

Run picks queries for all 6 API-connected models for a given slate date.
Calls query_model.py for each model in sequence and prints a summary.

Usage:
    python scripts/run_picks_all.py --date 2026-06-10
    python scripts/run_picks_all.py          # uses today's date in US Eastern Time

Connected models (in run order):
    grok, chatgpt, deepseek, kimi, qwen, gemini

Manual models (not run here -- paste into claude.ai):
    opus, sonnet

Output for each model: picks/{sport}/{date}/{model}_raw.txt

Notes:
  - If a model fails with a transient error (5xx), it is retried once after 90s.
  - Already-completed models (output file already exists with content) are skipped.
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Always use the system Python 3.12 install so all packages (openai, etc.) are available.
PYTHON = r"C:\Users\marko\AppData\Local\Programs\Python\Python312\python.exe"

SCRIPTS_DIR  = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent

# Models with confirmed API connections -- run in this order.
# Keep sequential to avoid rate limit collisions between providers.
AUTOMATED_MODELS = ["grok", "chatgpt", "deepseek", "kimi", "qwen", "gemini", "opus", "sonnet"]

# Seconds to wait before retrying a failed model.
RETRY_DELAY = 90

# Minimum bytes a valid picks output file must contain.
MIN_OUTPUT_BYTES = 300


def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from tz_util import ET
        return datetime.now(ET).strftime("%Y-%m-%d")
    except ImportError:
        from datetime import timezone, timedelta
        et = timezone(timedelta(hours=-4))
        return datetime.now(et).strftime("%Y-%m-%d")


def model_already_done(model: str, date: str, sport: str) -> bool:
    """
    Return True if this model's output file already exists with content.
    Prevents re-running a model that completed in a previous run.
    """
    out_path = PROJECT_ROOT / "picks" / sport / date / f"{model}_raw.txt"
    return out_path.exists() and out_path.stat().st_size >= MIN_OUTPUT_BYTES


def run_model(model: str, date: str, sport: str) -> tuple[bool, float, str]:
    """
    Run query_model.py for a single model, with one auto-retry on failure
    after RETRY_DELAY seconds.

    Returns (success, elapsed_seconds, detail_message).
    """
    cmd = [
        PYTHON,
        str(SCRIPTS_DIR / "query_model.py"),
        "--model", model,
        "--date", date,
        "--sport", sport,
    ]

    print(f"\n{'=' * 55}")
    print(f"  MODEL: {model.upper()}  ({date})")
    print(f"{'=' * 55}")
    print(f"  Command: {' '.join(cmd[2:])}")
    print()

    t0      = time.time()
    result  = subprocess.run(cmd)  # streams stdout/stderr to terminal in real time
    elapsed = time.time() - t0

    if result.returncode != 0:
        # First attempt failed -- wait and retry once.
        print(f"\n  WARNING: {model} failed (exit {result.returncode}). "
              f"Retrying in {RETRY_DELAY}s...")
        time.sleep(RETRY_DELAY)
        print(f"  Retrying {model}...")
        print()
        result  = subprocess.run(cmd)
        elapsed = time.time() - t0

    if result.returncode != 0:
        return False, elapsed, f"failed after retry (exit {result.returncode})"

    # Integrity check: output file must exist and have content.
    out_path = PROJECT_ROOT / "picks" / sport / date / f"{model}_raw.txt"
    if not out_path.exists():
        return False, elapsed, "output file not created"
    size = out_path.stat().st_size
    if size < MIN_OUTPUT_BYTES:
        return False, elapsed, f"output file too small ({size} bytes -- may be empty or truncated)"

    return True, elapsed, f"{size:,} bytes -> picks/{sport}/{date}/{model}_raw.txt"


def print_summary(results: list, total_elapsed: float, date: str, sport: str):
    """Print a clear pass/fail summary table after all models have run."""
    print(f"\n{'=' * 55}")
    print(f"  PICKS SUMMARY  {sport.upper()}  {date}")
    print(f"{'=' * 55}")
    print()

    succeeded = [r for r in results if r[1]]
    failed    = [r for r in results if not r[1]]
    skipped   = [r for r in results if r[3] == "skipped"]

    print(f"  {'Model':<12}  {'Status':<8}  {'Time':>6}  Detail")
    print(f"  {'-' * 12}  {'-' * 8}  {'-' * 6}  {'-' * 30}")

    for model, ok, elapsed, detail in results:
        if detail == "skipped":
            status   = "SKIPPED"
            time_str = "  -"
        else:
            status   = "OK" if ok else "FAILED"
            time_str = f"{elapsed:>5.1f}s"
        print(f"  {model:<12}  {status:<8}  {time_str}  {detail}")

    print()
    print(f"  Succeeded : {len(succeeded)}")
    print(f"  Skipped   : {len(skipped)}  (output file already exists)")
    if failed:
        print(f"  Failed    : {len(failed)}")
    print(f"  Total time: {total_elapsed:.0f}s")
    print()

    if failed:
        print("  To retry failed models:")
        for model, _ok, _elapsed, _detail in failed:
            print(f"    python scripts/query_model.py --model {model} --date {date}")

    print(f"\n  Manual models (opus, sonnet): paste prompt into claude.ai")
    print(f"  Prompt files: daily/{sport}/{date}/prompt_opus.md")
    print(f"                daily/{sport}/{date}/prompt_sonnet.md")
    print(f"\n{'=' * 55}\n")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run picks queries for all 6 API-connected models. "
            "Models run sequentially to avoid rate limit issues. "
            "Failed models are retried once after 90s. "
            "Models with an existing output file are skipped. "
            "Manual models (opus, sonnet) are not included."
        )
    )
    parser.add_argument(
        "--date", default=None,
        help="Slate date YYYY-MM-DD. Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--sport", default="mlb",
        help="Sport code (default: mlb)."
    )
    args = parser.parse_args()

    date  = args.date or today_et()
    sport = args.sport

    print(f"\n{'=' * 55}")
    print(f"  RUN PICKS ALL  {sport.upper()}  {date}")
    print(f"  Models: {', '.join(AUTOMATED_MODELS)}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 55}")

    wall_start = time.time()
    results    = []  # list of (model, ok, elapsed, detail)

    for model in AUTOMATED_MODELS:
        # Skip if output file already exists with content.
        if model_already_done(model, date, sport):
            out_path = PROJECT_ROOT / "picks" / sport / date / f"{model}_raw.txt"
            size = out_path.stat().st_size
            print(f"\n  SKIP {model.upper()}: output file already exists ({size:,} bytes).")
            results.append((model, True, 0.0, "skipped"))
            continue

        ok, elapsed, detail = run_model(model, date, sport)
        results.append((model, ok, elapsed, detail))
        # Always continue -- one failure does not abort the rest.

    total_elapsed = time.time() - wall_start
    print_summary(results, total_elapsed, date, sport)

    failed_count = sum(1 for r in results if not r[1])
    sys.exit(failed_count)


if __name__ == "__main__":
    main()

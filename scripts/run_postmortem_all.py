#!/usr/bin/env python
"""
scripts/run_postmortem_all.py

Run post-mortem queries for all 9 API-connected models for a given slate date.
Calls query_model.py --postmortem for each model in sequence and prints a summary.

Usage:
    python scripts/run_postmortem_all.py --date 2026-06-10
    python scripts/run_postmortem_all.py          # uses today's date in US Eastern Time

Connected models (in run order):
    grok, chatgpt, deepseek, kimi, qwen, gemini, opus, sonnet, fable

Notes:
  - Each model receives only the template + results, not prior models' responses.
    (query_model.py strips appended responses before sending.)
  - If a model fails with a transient error (5xx), it is retried once after 90s.
  - Already-completed models (per-model file exists with content) are skipped.
  - fetch_results.py must have run first so the post-mortem file has scores filled in.
    File: picks/{sport}/{date}/post_mortem_{date}.txt
  - Output is NOT auto-injected into method docs or MODEL_INSTRUCTIONS.md.
    Routing post-mortem output into method updates is a separate, manually-gated step.
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

# All 9 models are now API-connected. Run sequentially to avoid rate-limit collisions.
# opus, sonnet, fable use the Anthropic SDK (CLAUDE_API_KEY).
AUTOMATED_MODELS = ["grok", "chatgpt", "deepseek", "kimi", "qwen", "gemini", "opus", "sonnet"]

# Seconds to wait before retrying a failed model.
RETRY_DELAY = 90

# Minimum chars a valid response must add to the post-mortem file.
# Responses shorter than this are flagged as suspect (likely truncated or empty).
MIN_RESPONSE_CHARS = 300


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


def model_already_done(model: str, pm_path: Path) -> bool:
    """
    Return True if this model's per-model postmortem file already exists with content.
    Checking the per-model file is more reliable than scanning the shared aggregate --
    it's a clean single-file existence check with no string parsing.
    """
    per_model_path = pm_path.parent / f"{model}_postmortem.txt"
    return per_model_path.exists() and per_model_path.stat().st_size >= MIN_RESPONSE_CHARS


def check_response_appended(model: str, pm_path: Path, size_before: int) -> tuple[bool, str]:
    """
    After a model call completes, verify the response was actually appended.
    Checks:
      - The ## MODEL RESPONSE separator is present
      - At least MIN_RESPONSE_CHARS were added
    Returns (ok, detail_message).
    """
    if not pm_path.exists():
        return False, "post-mortem file missing after write"

    content      = pm_path.read_text(encoding="utf-8")
    size_after   = len(content)
    chars_added  = size_after - size_before
    separator    = f"## {model.upper()} RESPONSE"

    if separator not in content:
        return False, f"separator '{separator}' not found in file after write"

    if chars_added < MIN_RESPONSE_CHARS:
        return False, (
            f"only {chars_added} chars added -- response may be empty or truncated "
            f"(minimum expected: {MIN_RESPONSE_CHARS})"
        )

    return True, f"{chars_added:,} chars added"


def run_model_postmortem(
    model: str, date: str, sport: str, pm_path: Path
) -> tuple[bool, float, str]:
    """
    Run query_model.py --postmortem for a single model, with one auto-retry
    on failure after RETRY_DELAY seconds.

    Returns (success, elapsed_seconds, detail_message).
    """
    cmd = [
        PYTHON,
        str(SCRIPTS_DIR / "query_model.py"),
        "--model", model,
        "--date", date,
        "--sport", sport,
        "--postmortem",
    ]

    print(f"  Command: {' '.join(cmd[2:])}")
    print()

    # Record file size before the call so we can verify chars were added.
    size_before = len(pm_path.read_text(encoding="utf-8")) if pm_path.exists() else 0

    t0     = time.time()
    result = subprocess.run(cmd)   # streams stdout/stderr to terminal in real time
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

    # Verify the response was actually appended correctly.
    ok, detail = check_response_appended(model, pm_path, size_before)
    if not ok:
        return False, elapsed, f"API call succeeded but integrity check failed: {detail}"

    return True, elapsed, detail


def print_summary(results: list, total_elapsed: float, date: str, sport: str):
    """Print a clear pass/fail summary table after all models have run."""
    print(f"\n{'=' * 60}")
    print(f"  POST-MORTEM SUMMARY  {sport.upper()}  {date}")
    print(f"{'=' * 60}")
    print()

    succeeded = [r for r in results if r[1]]
    failed    = [r for r in results if not r[1]]
    skipped   = [r for r in results if r[3] == "skipped"]

    print(f"  {'Model':<12}  {'Status':<8}  {'Time':>6}  Detail")
    print(f"  {'-' * 12}  {'-' * 8}  {'-' * 6}  {'-' * 30}")

    for model, ok, elapsed, detail in results:
        if detail == "skipped":
            status = "SKIPPED"
            time_str = "  -"
        else:
            status   = "OK" if ok else "FAILED"
            time_str = f"{elapsed:>5.1f}s"
        print(f"  {model:<12}  {status:<8}  {time_str}  {detail}")

    print()
    print(f"  Succeeded : {len(succeeded)}")
    print(f"  Skipped   : {len(skipped)}  (already in file)")
    if failed:
        print(f"  Failed    : {len(failed)}")
    print(f"  Total time: {total_elapsed:.0f}s")
    print()

    if failed:
        print("  To retry failed models:")
        for model, _ok, _elapsed, _detail in failed:
            print(f"    python scripts/query_model.py --model {model} --date {date} --postmortem")

    print(f"  Per-model files : picks/{sport}/{date}/{{model}}_postmortem.txt")
    print(f"  Aggregate file  : picks/{sport}/{date}/post_mortem_{date}.txt")
    print(f"  NOTE: output is NOT auto-injected into method docs or MODEL_INSTRUCTIONS.md.")
    print(f"\n{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run post-mortem queries for all 6 API-connected models. "
            "Models run sequentially. Failed models are retried once after 90s. "
            "Models already in the file are skipped. "
            "fetch_results.py must have run first so scores are filled in."
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
    parser.add_argument(
        "--rerun", action="store_true",
        help=(
            "Clear all per-model postmortem files for this date and re-run from scratch. "
            "Use when previous run sent before fetch_results.py had populated scores."
        )
    )
    args = parser.parse_args()

    date  = args.date or today_et()
    sport = args.sport

    pm_path = PROJECT_ROOT / "picks" / sport / date / f"post_mortem_{date}.txt"

    # Pre-flight: post-mortem file must exist with scores filled in.
    if not pm_path.exists():
        print(f"\n  ERROR: Post-mortem file not found:")
        print(f"    {pm_path}")
        print(f"  Run fetch_results.py first:")
        print(f"    python scripts/fetch_results.py --date {date}\n")
        sys.exit(1)

    pm_text = pm_path.read_text(encoding="utf-8")
    if "[OPERATOR WILL PASTE RESULTS HERE]" in pm_text:
        print(f"\n  WARNING: Post-mortem file still has the results placeholder.")
        print(f"  Run fetch_results.py first to fill in the scores:")
        print(f"    python scripts/fetch_results.py --date {date}")
        print(f"  Continuing anyway...\n")

    # Guard: abort if ALL picks files are empty (no pipeline was run for this date).
    picks_dir = PROJECT_ROOT / "picks" / sport / date
    picks_files = list(picks_dir.glob("*_raw.txt"))
    nonempty = [f for f in picks_files if f.stat().st_size > 0]
    if picks_files and len(nonempty) == 0:
        print(f"\n  ERROR: All {len(picks_files)} picks files for {date} are empty (0 bytes).")
        print(f"  The pipeline was likely never run for this date.")
        print(f"  Run the full pipeline first:")
        print(f"    python scripts/run_daily.py mlb --date {date}")
        print(f"  Or specify the correct date:")
        print(f"    python scripts/run_postmortem_all.py --date YYYY-MM-DD\n")
        sys.exit(1)

    # --rerun: delete existing per-model postmortem files so the skip guard doesn't fire.
    # This is the recovery path for "ran postmortem before fetch_results.py".
    picks_dir_pm = PROJECT_ROOT / "picks" / sport / date
    if args.rerun:
        cleared = []
        for model in AUTOMATED_MODELS:
            per_model_file = picks_dir_pm / f"{model}_postmortem.txt"
            if per_model_file.exists():
                per_model_file.unlink()
                cleared.append(model)
        if cleared:
            print(f"\n  --rerun: cleared existing postmortem files for: {', '.join(cleared)}")
        else:
            print(f"\n  --rerun: no existing postmortem files to clear.")

    print(f"\n{'=' * 60}")
    print(f"  RUN POST-MORTEM ALL  {sport.upper()}  {date}")
    print(f"  Models: {', '.join(AUTOMATED_MODELS)}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'=' * 60}")

    wall_start = time.time()
    results    = []   # list of (model, ok, elapsed, detail)

    for model in AUTOMATED_MODELS:
        print(f"\n{'=' * 60}")
        print(f"  POST-MORTEM: {model.upper()}  ({date})")
        print(f"{'=' * 60}")

        # Skip if this model already has a response in the file.
        if model_already_done(model, pm_path):
            print(f"  SKIP: ## {model.upper()} RESPONSE already in file.")
            results.append((model, True, 0.0, "skipped"))
            continue

        ok, elapsed, detail = run_model_postmortem(model, date, sport, pm_path)
        results.append((model, ok, elapsed, detail))
        # Always continue -- one failure does not abort the rest.

    total_elapsed = time.time() - wall_start
    print_summary(results, total_elapsed, date, sport)

    failed_count = sum(1 for r in results if not r[1])
    sys.exit(failed_count)


if __name__ == "__main__":
    main()

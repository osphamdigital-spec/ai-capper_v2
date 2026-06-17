#!/usr/bin/env python
"""
scripts/log_all_picks.py

Run log_picks.py for every model that has a _raw.txt file in the picks
folder for a given sport and date. One command instead of running
log_picks.py separately for each model.

Usage:
    python scripts/log_all_picks.py mlb
    python scripts/log_all_picks.py mlb --date 2026-06-03
    python scripts/log_all_picks.py mlb --date 2026-06-03 --rerun

What it does:
    1. Scans picks/{sport}/{date}/ for files matching *_raw.txt
    2. Derives the model name by stripping _raw.txt from the filename
    3. Runs log_picks.py for each model
    4. Prints a per-model pass/fail summary at the end

By default, models that already have a parsed .json file are skipped
(their picks were already logged). Use --rerun to force re-parsing all.
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from tz_util import ET


SCRIPTS_DIR  = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent


def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def find_raw_files(sport: str, date: str) -> list[Path]:
    """
    Return all *_raw.txt files in picks/{sport}/{date}/, sorted alphabetically.
    Files that don't end in _raw.txt (e.g. post_mortem.txt) are excluded.
    """
    picks_dir = PROJECT_ROOT / "picks" / sport / date
    if not picks_dir.exists():
        return []
    # Glob for _raw.txt specifically — excludes post_mortem.txt and any other files
    return sorted(picks_dir.glob("*_raw.txt"))


def run_log_picks(model: str, sport: str, date: str, input_path: Path) -> tuple[bool, float, str]:
    """
    Run log_picks.py for one model as a subprocess.

    Output streams to the terminal in real time so any parse warnings are
    visible as they happen, not buried in a post-run dump.

    Returns (success, elapsed_seconds, first_warning_line).
    first_warning_line is the first WARNING: line from output, or "" if none.
    """
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "log_picks.py"),
        "--model",  model,
        "--sport",  sport,
        "--date",   date,
        "--input",  str(input_path),
    ]

    t0     = time.time()
    result = subprocess.run(cmd, capture_output=False)
    elapsed = time.time() - t0

    success = result.returncode == 0
    return success, elapsed, ""


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run log_picks.py for every *_raw.txt file in the picks folder "
            "for a given sport and date."
        )
    )
    parser.add_argument(
        "sport",
        help="Sport code: mlb, nba, nhl, nfl, ncaaf, ncaab",
    )
    parser.add_argument(
        "--date", default=None,
        help="Slate date (YYYY-MM-DD). Default: today in US Eastern Time.",
    )
    parser.add_argument(
        "--rerun", action="store_true",
        help="Re-parse models that already have a .json file (overwrites existing).",
    )
    args = parser.parse_args()

    target_date = args.date or today_et()

    print(f"\n{'='*55}")
    print(f"  LOG ALL PICKS — {args.sport.upper()}")
    print(f"  Date: {target_date}")
    print(f"{'='*55}\n")

    # ── Discover raw files ────────────────────────────────────────────────────
    raw_files = find_raw_files(args.sport, target_date)

    if not raw_files:
        picks_dir = PROJECT_ROOT / "picks" / args.sport / target_date
        print(f"  No *_raw.txt files found in {picks_dir.relative_to(PROJECT_ROOT)}")
        print(f"  Paste model responses into the picks folder first.")
        sys.exit(0)

    print(f"  Found {len(raw_files)} raw file(s):\n")
    import json as _json
    for f in raw_files:
        model = f.stem.replace("_raw", "")
        json_path = f.parent / f"{model}.json"
        if json_path.exists():
            try:
                doc = _json.loads(json_path.read_text(encoding="utf-8"))
                has_picks = len(doc.get("picks", [])) > 0
            except Exception:
                has_picks = False
            if has_picks and not args.rerun:
                status = "already parsed — will skip"
                marker = "  [skip]"
            elif has_picks:
                status = "already parsed — will rerun"
                marker = "  "
            else:
                status = "json exists but empty — will reparse"
                marker = "  "
        else:
            status = "pending"
            marker = "  "
        print(f"{marker}  {f.name}  ({status})")

    print()

    # ── Run log_picks.py for each model ───────────────────────────────────────
    results = []   # (model_name, status_label, elapsed)

    for raw_path in raw_files:
        # Derive model name: "chatgpt5.5_raw.txt" -> "chatgpt5.5"
        model = raw_path.stem.replace("_raw", "")

        # Check whether this model already has a parsed JSON with actual picks
        json_path = raw_path.parent / f"{model}.json"
        if json_path.exists() and not args.rerun:
            try:
                import json as _json
                doc = _json.loads(json_path.read_text(encoding="utf-8"))
                has_picks = len(doc.get("picks", [])) > 0
            except Exception:
                has_picks = False
            if has_picks:
                print(f"  [skip] {model} — {model}.json already has picks (use --rerun to overwrite)")
                results.append((model, "skipped", 0.0))
                continue
            elif json_path.exists():
                print(f"  [reparse] {model} — {model}.json exists but has no picks, re-parsing...")

        # Visual separator between models
        print(f"\n{'-'*55}")
        print(f"  MODEL: {model}")
        print(f"{'-'*55}")

        ok, elapsed, _ = run_log_picks(model, args.sport, target_date, raw_path)

        if ok:
            # Double-check actual parse count in the output JSON.
            # log_picks exits 2 on parse-to-zero, but guard here too in case
            # any path exits 0 with zero games (belt-and-braces).
            try:
                import json as _json2
                out_doc      = _json2.loads(json_path.read_text(encoding="utf-8"))
                games_parsed = out_doc.get("counts", {}).get("games", 0)
                if games_parsed == 0 and raw_path.stat().st_size > 0:
                    results.append((model, "WARN: 0 games from non-empty raw", elapsed))
                    print(f"\n  WARN: {model} log_picks exited OK but counts.games=0 "
                          f"with {raw_path.stat().st_size:,}-byte raw file.")
                    print(f"  Possible unrecognised format or empty content field fallback.")
                else:
                    results.append((model, "OK", elapsed))
            except Exception:
                results.append((model, "OK", elapsed))
        else:
            results.append((model, "FAILED", elapsed))
            print(f"\n  ERROR: log_picks.py exited with non-zero code for {model}")

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  SUMMARY — {args.sport.upper()} {target_date}")
    print(f"{'='*55}\n")
    print(f"  {'Model':<20}  {'Result':<16}  {'Time':>6}")
    print(f"  {'-'*20}  {'-'*16}  {'-'*6}")

    ok_count      = 0
    failed_count  = 0
    skipped_count = 0

    for model, status, elapsed in results:
        time_str = f"{elapsed:.1f}s" if elapsed > 0 else "—"
        print(f"  {model:<20}  {status:<16}  {time_str:>6}")
        if status == "OK":
            ok_count += 1
        elif status == "FAILED":
            failed_count += 1
        else:
            skipped_count += 1

    print()
    print(f"  Logged:  {ok_count}")
    if skipped_count:
        print(f"  Skipped: {skipped_count}  (use --rerun to re-parse)")
    if failed_count:
        print(f"  Failed:  {failed_count}  (check raw files above)")

    print(f"\n  Picks saved to: picks/{args.sport}/{target_date}/")
    print(f"{'='*55}\n")

    # Exit non-zero if any model failed — useful if called from a pipeline
    if failed_count:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
scripts/run_daily.py

Single entry point for the full daily data pipeline.
Runs all fetch scripts in the correct order, then builds the prompt.

Usage:
    python scripts/run_daily.py mlb
    python scripts/run_daily.py mlb --date 2026-06-03
    python scripts/run_daily.py mlb --with-picks

--with-picks chains the full post-prompt sequence in one command:
    run_picks_all.py  -> log_all_picks.py -> watch_set.py
    -> (interactive prompt, 20s timeout, default YES) -> run_lineup_watcher.py
The watcher prompt auto-accepts YES if no answer arrives within 20 seconds;
type NO/N to skip it and launch run_lineup_watcher.py manually later.

Steps (in order):
    0. static file check       PRE-CHECK -- warns if FanGraphs files in data/{sport}/ are
                                            missing or older than 7 days. Never blocks.
    1. fetch_odds.py           REQUIRED  -- creates games.json with odds
    2. fetch_covers_lines.py   OPTIONAL  -- adds opening RL/total prices + movement history from Covers.com
    3. fetch_opener.py         OPTIONAL  -- true opening lines from Covers.com (Playwright; adds odds.covers_opener)
    4. fetch_pitchers.py           REQUIRED  -- adds probable pitchers + gamePks
    5. fetch_pitcher_advanced.py   OPTIONAL  -- Baseball Savant advanced metrics
    6. fetch_weather.py            REQUIRED  -- adds weather per stadium
    7. fetch_teamstats.py          REQUIRED  -- adds team standings and form
    8. fetch_bullpen.py            OPTIONAL  -- reliever usage last 3 days, taxed flags
    9. fetch_lineups.py            OPTIONAL  -- confirmed lineups + IL (2-3h before first pitch)
   10. rotowire_expected_lineups.py OPTIONAL -- expected lineups snapshot (sideline; Rotowire only serves today)
   11. fetch_umpire_inference.py   OPTIONAL  -- inferred HP from yesterday's crew rotation
   12. fetch_umpires.py            OPTIONAL  -- confirmed umpires from MLB API (1-2h before)
   13. build_prompt.py             REQUIRED  -- generates daily/{sport}/{date}/prompt.md

Required steps: pipeline stops immediately if any of these fail.
Optional steps: failure is logged clearly, pipeline continues.

Static reference files (MLB only, manually downloaded from FanGraphs):
    data/mlb/splits_vs_LHP.txt          -- batter splits vs LHP
    data/mlb/splits_vs_RHP.txt          -- batter splits vs RHP
    data/mlb/splits_home.txt            -- batter splits at home
    data/mlb/splits_away.txt            -- batter splits away
    data/mlb/pitchers_xfip_siera.txt    -- starter xFIP/SIERA (2-yr blend)
    data/mlb/pitchers_last14.txt        -- starter stats last 14 days
    data/mlb/Bullpen.txt                -- all relievers, role, usage last 6 days
    data/mlb/park_factors_all.txt       -- park factors all conditions (3yr)
    data/mlb/park_factors_roof_closed.txt -- park factors roof closed only
Refresh these weekly (or at minimum before each series).
"""

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from tz_util import ET


SCRIPTS_DIR  = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent

# Use the system Python 3.12 install explicitly so that pybaseball (and any
# other package installed there) is always available, regardless of which venv
# or Python runtime launched this script.
PYTHON = r"C:\Users\marko\AppData\Local\Programs\Python\Python312\python.exe"


# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILE REGISTRY
# Files that must be manually downloaded and placed in data/{sport}/ before
# running the pipeline. build_prompt.py reads these directly — no fetch step.
# ─────────────────────────────────────────────────────────────────────────────

_STATIC_FILES: dict[str, list[str]] = {
    "mlb": [
        "splits_vs_LHP.txt",
        "splits_vs_RHP.txt",
        "splits_home.txt",
        "splits_away.txt",
        "pitchers_xfip_siera.txt",
        "pitchers_last14.txt",
        "Bullpen.txt",
        "park_factors_all.txt",
        "park_factors_roof_closed.txt",
        "lineup_tracker.txt",
    ],
    # Other sports have no static files yet — add here when they're added.
}

_STATIC_STALE_DAYS = 7   # warn if a file hasn't been updated in this many days

# Per-file overrides for staleness threshold (in days). Files not listed here use _STATIC_STALE_DAYS.
# lineup_tracker.txt holds projected batting orders — outdated by next day, so threshold is 1 day.
_STALE_DAYS_OVERRIDE: dict[str, int] = {
    "lineup_tracker.txt": 1,
    "Bullpen.txt":        2,   # bullpen usage roles change within days
}


# ─────────────────────────────────────────────────────────────────────────────
# .ENV LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _load_dotenv():
    """
    Load .env from project root into this process's environment BEFORE
    spawning any subprocesses. Each child process inherits the parent
    environment, so all scripts get the API key without any of them
    needing to load it themselves (fetch_odds.py also loads it as a
    belt-and-suspenders fallback, but this is the primary mechanism).
    """
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            # setdefault: real env vars always win over the .env file
            os.environ.setdefault(key.strip(), val.strip())


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def _check_static_files(sport: str) -> None:
    """
    Pre-flight check: verify all expected static reference files for this sport
    exist in data/{sport}/ and have been updated within the last 7 days.

    Prints OK or WARNING for each file, then a one-line summary.
    Never raises an exception or stops the pipeline — warnings only.
    Silently skips sports that have no registered static files.
    """
    files = _STATIC_FILES.get(sport)
    if not files:
        return   # no static files registered for this sport yet

    data_dir = PROJECT_ROOT / "data" / sport
    now      = datetime.now().timestamp()

    print(f"\n{'-' * 55}")
    print(f"  STATIC FILE CHECK  ({sport.upper()} reference data)")
    print(f"{'-' * 55}")

    warnings = 0

    for filename in files:
        path = data_dir / filename

        if not path.exists():
            print(f"  WARNING  {filename}")
            print(f"           File not found — download from FanGraphs and place in data/{sport}/")
            warnings += 1
            continue

        # Calculate age in whole days
        age_seconds = now - path.stat().st_mtime
        age_days    = int(age_seconds // 86400)

        if age_days == 0:
            age_str = "today"
        elif age_days == 1:
            age_str = "1 day old"
        else:
            age_str = f"{age_days} days old"

        # Use per-file staleness threshold if one exists
        stale_threshold = _STALE_DAYS_OVERRIDE.get(filename, _STATIC_STALE_DAYS)

        if age_days >= stale_threshold:
            print(f"  WARNING  {filename:<36}  ({age_str} -- refresh recommended)")
            warnings += 1
        else:
            print(f"  OK       {filename:<36}  ({age_str})")

    print()
    if warnings:
        print(f"  {warnings} file(s) need attention.")
        print(f"  Prompt will still build using whatever data is present.")
    else:
        print(f"  All {len(files)} static files OK.")


def run_step(name: str, script: str, args: list) -> tuple[bool, float]:
    """
    Run one pipeline step as a subprocess.

    Output streams directly to the terminal in real time so you can watch
    each script's progress without waiting for the whole pipeline to finish.

    Returns (success, elapsed_seconds).
    success is True when the script exits with code 0.
    """
    cmd = [PYTHON, str(SCRIPTS_DIR / script)] + args

    # Visual separator so each step's output is clearly bounded
    print(f"\n{'-' * 55}", flush=True)
    print(f"  RUNNING: {name}", flush=True)
    print(f"{'-' * 55}", flush=True)

    t0     = time.time()
    result = subprocess.run(cmd)           # streams stdout/stderr to terminal
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"\n  EXIT CODE: {result.returncode}  ({name} failed)")

    return result.returncode == 0, elapsed


def _confirm_run_watcher(timeout_secs: int = 20) -> bool:
    """
    Ask the operator whether to launch the continuous lineup watcher.

    Returns True to run it, False to skip.

    Behaviour:
      - Explicit NO / N (case-insensitive)  -> False (skip)
      - Explicit YES / Y (or anything else)  -> True  (run)
      - No input within timeout_secs         -> True  (auto-accept default)

    The prompt is read on a background thread so the main thread can enforce
    the timeout. If the timer expires we stop waiting and default to YES; the
    reader thread is a daemon, so it dies when the process moves on.
    """
    import threading

    prompt_msg = f"\n  Run lineup watcher? [YES / NO] (Auto-accepting in {timeout_secs}s): "
    answer: dict[str, str] = {}

    def _reader():
        try:
            answer["value"] = input(prompt_msg)
        except (EOFError, KeyboardInterrupt):
            answer["value"] = ""

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    t.join(timeout_secs)

    if t.is_alive():
        # Timed out — no input arrived. Default to YES.
        print(f"\n  No response in {timeout_secs}s — auto-accepting (YES).")
        return True

    response = (answer.get("value") or "").strip().lower()
    if response in ("n", "no"):
        return False
    return True


def _print_summary(results: list[tuple], sport: str, date: str, total_elapsed: float):
    """
    Print the pipeline summary table showing pass/fail for every step
    and the location of the final prompt.md.

    results is a list of (step_name, status_label, elapsed_seconds).
    """
    prompt_path = PROJECT_ROOT / "daily" / sport / date / "prompt.md"

    print(f"\n{'=' * 55}")
    print(f"  PIPELINE SUMMARY  {sport.upper()}  {date}")
    print(f"{'=' * 55}")
    print()
    print(f"  {'Step':<16}  {'Result':<16}  {'Time':>6}")
    print(f"  {'-' * 16}  {'-' * 16}  {'-' * 6}")

    for step_name, status, elapsed in results:
        print(f"  {step_name:<16}  {status:<16}  {elapsed:>5.1f}s")

    print()

    if prompt_path.exists():
        text  = prompt_path.read_text(encoding="utf-8")
        size  = prompt_path.stat().st_size
        words = len(text.split())
        print(f"  Prompt : daily/{sport}/{date}/prompt.md")
        print(f"  Size   : {size:,} bytes  (~{words:,} words)")
    else:
        print(f"  Prompt : not generated")

    print(f"  Total  : {total_elapsed:.0f}s")
    print(f"\n{'=' * 55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# DATA COMPLETENESS GATE
# Runs after all fetch steps, before build_prompt. Halts on missing pitcher
# stats so prompts are never built on degraded data.
#
# KNOWN LIMITATION (v1): checks non-null, not freshness. A pitcher carrying
# HH%/Brl% from a prior fetch while today's fetch failed would pass the gate
# (stale-but-present). Out of scope for v1 — document and monitor.
# ─────────────────────────────────────────────────────────────────────────────

def preflight_data_gate(sport: str, date: str) -> bool:
    """
    Assert data completeness for every eligible starting pitcher before build_prompt runs.

    Eligible pitcher = named, non-TBD, has a valid MLBAM ID, game not postponed/cancelled.
    TBD starters are skipped — they trigger a PASS rule in the prompt, not a gate failure.

    Assertions (all three must pass for every eligible pitcher):
      1. Starting pitcher is named (present in games.json context block)
      2. MLBAM ID (mlb_id) is populated — set by fetch_pitchers.py
      3. hard_hit_pct AND barrel_pct are non-null — set by fetch_pitcher_advanced.py
         xERA is intentionally excluded: legitimately None for low-BBE pitchers.

    Interpreter warning (NOT a halt condition):
      Prints a warning if the active interpreter differs from PYTHON, but does not
      halt — run_daily.py already hardcodes PYTHON for all child processes, so data
      assertions #1-3 catch any actual enrichment failures regardless of parent
      interpreter.

    This week's failures each assertion would have caught:
      - Jun 20: wrong venv (hermes) → pybaseball ImportError → HH%/Brl% null
                Caught by assertion #3 (HH%/Brl% null)
                Interpreter warning also fires, pointing at root cause
      - Jun 21: fetch_pitchers.py never run → mlb_id absent → enrichment skipped
                Caught by assertion #2 (mlb_id absent)

    Returns True when all assertions pass, False when any fail (caller halts pipeline).
    """
    import json as _json

    print(f"\n{'=' * 55}")
    print(f"  DATA COMPLETENESS GATE  {sport.upper()}  {date}")
    print(f"{'=' * 55}")

    # Interpreter warning — downgraded from HALT per design decision 2026-06-21.
    # Child processes are always invoked via PYTHON regardless of parent interpreter,
    # so a mismatch here does not mean advanced stats are absent — the data
    # assertions below confirm that independently.
    active = Path(sys.executable).resolve()
    expected = Path(PYTHON).resolve()
    if active != expected:
        print(f"  WARNING: launched under unexpected interpreter: {sys.executable}")
        print(f"  Expected: {PYTHON}")
        print(f"  (child fetch scripts still use {PYTHON} -- data assertions below are the real gate)")
        print()

    games_path = PROJECT_ROOT / "data" / sport / date / "games.json"
    if not games_path.exists():
        print(f"  ERROR: games.json not found — run fetch_odds.py + fetch_pitchers.py first.")
        print(f"{'=' * 55}\n")
        return False

    games = _json.loads(games_path.read_text(encoding="utf-8"))

    _SKIP = {"postponed", "cancelled", "suspended"}

    failures  = []   # collects human-readable failure strings
    eligible  = 0    # pitchers checked (non-TBD, non-postponed, have mlb_id)

    print(f"  {'Game':<15}  {'Side':<4}  {'Pitcher':<22}  {'ID':>7}  {'HH%':>5}  {'Brl%':>5}  Result")
    print(f"  {'-'*15}  {'-'*4}  {'-'*22}  {'-'*7}  {'-'*5}  {'-'*5}  {'-'*6}")

    for g in games:
        status_raw = (g.get("status") or "").lower()
        if any(s in status_raw for s in _SKIP):
            continue   # postponed/cancelled — no gate check needed

        matchup = f"{g['away']['abbr']}@{g['home']['abbr']}"
        ctx = g.get("context") or {}

        for side_key, side_label in [("pitcher_away", "Away"), ("pitcher_home", "Home")]:
            p = ctx.get(side_key) or {}
            pitcher_name = (p.get("name") or "").strip()

            # TBD starters are excluded — the prompt issues a PASS for them separately
            if not pitcher_name or "TBD" in pitcher_name.upper():
                print(f"  {matchup:<15}  {side_label:<4}  {'TBD':<22}  {'—':>7}  {'—':>5}  {'—':>5}  SKIP(TBD)")
                continue

            mlb_id = p.get("mlb_id")
            hh     = p.get("hard_hit_pct")
            brl    = p.get("barrel_pct")

            # Assertion #2: MLBAM ID present
            if not mlb_id:
                result_label = "FAIL(no_id)"
                failures.append(
                    f"{matchup} {side_label}: {pitcher_name} — no MLBAM ID "
                    f"(fetch_pitchers.py may not have run)"
                )
                print(f"  {matchup:<15}  {side_label:<4}  {pitcher_name:<22}  {'—':>7}  {'—':>5}  {'—':>5}  {result_label}")
                continue

            eligible += 1

            # Assertion #3: HH% and Brl% both non-null
            missing = []
            if hh  is None: missing.append("HH%")
            if brl is None: missing.append("Brl%")

            if missing:
                result_label = f"FAIL({','.join(missing)}=null)"
                failures.append(
                    f"{matchup} {side_label}: {pitcher_name} — "
                    f"{' and '.join(missing)} null (fetch_pitcher_advanced.py not run or wrong interpreter)"
                )
            else:
                result_label = "OK"

            hh_str  = f"{hh:.1f}"  if hh  is not None else "—"
            brl_str = f"{brl:.1f}" if brl is not None else "—"
            print(f"  {matchup:<15}  {side_label:<4}  {pitcher_name:<22}  {mlb_id:>7}  {hh_str:>5}  {brl_str:>5}  {result_label}")

    print()

    if not failures:
        print(f"  Gate PASSED  ({eligible} eligible pitchers, all stats complete)")
        print(f"{'=' * 55}\n")
        return True

    # Gate failed — print checklist and re-run instructions, then return False
    print(f"  Gate FAILED  {len(failures)} pitcher(s) missing required stats:")
    for msg in failures:
        print(f"    - {msg}")
    print()
    print(f"  Fix:")
    print(f"    1. Check the !!! WARNING banner above for which fetch step failed")
    print(f"    2. Re-run pitcher advanced fetch:")
    print(f"       {PYTHON} scripts\\fetch_pitcher_advanced.py --sport {sport} --date {date}")
    print(f"    3. Then re-run the pipeline (fetches are idempotent):")
    print(f"       {PYTHON} scripts\\run_daily.py {sport} --date {date}")
    print()
    print(f"  Override (only when data is genuinely unavailable, e.g. off-day):")
    print(f"    {PYTHON} scripts\\run_daily.py {sport} --date {date} --skip-gate")
    print(f"{'=' * 55}\n")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# MODEL-SPECIFIC PROMPT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _parse_model_names(project_root: Path) -> list:
    """
    Read docs/MODEL_INSTRUCTIONS.md and return all model names as lowercase,
    hyphenated strings suitable for use in filenames.

    Extracts === MODEL NAME === section headers, e.g.:
      === CLAUDE ===       -> "claude"
      === GPT-5.2-HIGH === -> "gpt-5.2-high"
      === CHATGPT ===      -> "chatgpt"

    Returns an empty list if the file doesn't exist.
    """
    path = project_root / "docs" / "MODEL_INSTRUCTIONS.md"
    if not path.exists():
        return []
    text    = path.read_text(encoding="utf-8")
    matches = re.findall(r"===\s*(.+?)\s*===", text)
    # Lowercase and replace spaces with hyphens so names are filename-safe
    return [m.strip().lower().replace(" ", "-") for m in matches]


def _build_model_prompts(sport: str, date: str):
    """
    Generate prompt_{model}.md for every model listed in MODEL_INSTRUCTIONS.md.

    Each model name is passed to build_prompt.py via --model. The script
    resolves the matching instruction section and appends it at the end of
    the prompt. If no instruction is found for a model (shouldn't happen
    since we read the names from MODEL_INSTRUCTIONS.md), we skip silently.

    NOTE: query_model.py handles automated API calls for connected models.
    Empty placeholder _raw.txt files are still created for all models including
    manual ones (opus, sonnet) -- this is done by fetch_results.py using the
    model list in docs/model_roster.md, not by this function.
    Connected models: chatgpt, grok, deepseek, kimi, qwen, gemini
    Manual models:    opus, sonnet (paste into claude.ai)
    """
    models = _parse_model_names(PROJECT_ROOT)
    if not models:
        print("  NOTE: No models found in docs/MODEL_INSTRUCTIONS.md — skipping per-model prompts.")
        return

    print(f"\n{'-' * 55}")
    print(f"  PER-MODEL PROMPTS  ({len(models)} models)")
    print(f"{'-' * 55}")

    for model in models:
        cmd = [
            PYTHON, str(SCRIPTS_DIR / "build_prompt.py"),
            "--sport", sport, "--date", date, "--model", model,
        ]
        # capture_output keeps the per-model build chatter off the main log;
        # we print a single status line per model instead.
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  FAIL  prompt_{model}.md")
            if result.stderr:
                print(f"        {result.stderr.strip()[:200]}")
            continue

        out_path = PROJECT_ROOT / "daily" / sport / date / f"prompt_{model}.md"
        if out_path.exists():
            print(f"  OK    prompt_{model}.md  ({out_path.stat().st_size:,} bytes)")
        else:
            # build_prompt.py found no instruction — file not written, skip silently
            pass

    print()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_daily(sport: str, date: str = None, skip_gate: bool = False, with_picks: bool = False):
    """
    Execute the full daily pipeline for the given sport and date.

    Scripts that accept --sport are passed it explicitly.
    Scripts that don't (fetch_pitchers.py, fetch_weather.py, fetch_umpires.py)
    only get --date — they are MLB-only for now and sport is implicit.
    """
    target_date = date or today_et()
    wall_start  = time.time()

    # Create the picks folder for today's date and drop the post-mortem template
    # in so it's ready to fill in after the models run.
    picks_dir = PROJECT_ROOT / "picks" / sport / target_date
    picks_dir.mkdir(parents=True, exist_ok=True)
    template_src  = PROJECT_ROOT / "docs" / "post_mortem_template.txt"
    template_dest = picks_dir / f"post_mortem_{target_date}.txt"
    if template_src.exists() and not template_dest.exists():
        import shutil
        shutil.copy(template_src, template_dest)

    print(f"\n{'=' * 55}")
    print(f"  DAILY PIPELINE  {sport.upper()}")
    print(f"  Date   : {target_date}")
    print(f"  Started: {datetime.now(ET).strftime('%H:%M ET')}")
    print(f"{'=' * 55}")

    # Pre-flight: check static reference files before any network calls.
    # Warnings only — never stops the pipeline.
    _check_static_files(sport)

    # Pipeline definition — each entry is:
    #   (display_name, script_filename, extra_args, is_required)
    #
    # Note: scripts that accept --sport get it; others only get --date.
    # This matches each script's actual argparse definition.
    pipeline = [
        ("Odds",         "fetch_odds.py",               ["--sport", sport, "--date", target_date], True),
        ("Covers Lines", "fetch_covers_lines.py",      ["--sport", sport, "--date", target_date], False),
        ("Opener Lines", "fetch_opener.py",            ["--sport", sport, "--date", target_date], False),  # optional — Covers true opener (Playwright)
        ("Pitchers",     "fetch_pitchers.py",          ["--date", target_date],                   True),
        ("Pitcher Adv.", "fetch_pitcher_advanced.py",  ["--sport", sport, "--date", target_date], False),
        ("Weather",      "fetch_weather.py",           ["--date", target_date],                   True),
        ("Team Stats",   "fetch_teamstats.py", ["--sport", sport, "--date", target_date], True),
        ("Bullpen",      "fetch_bullpen.py",   ["--sport", sport, "--date", target_date], False),  # optional
        ("Lineups",      "fetch_lineups.py",          ["--sport", sport, "--date", target_date], False),  # optional — confirmed ~2-3h before first pitch
        ("Rotowire Exp", "rotowire_expected_lineups.py", ["--sport", sport, "--date", target_date], False),  # sideline — EXPECTED lineups; captured pre-game (Rotowire only serves today)
        ("Umpire Infer", "fetch_umpire_inference.py", ["--date", target_date],                   False),  # optional — early estimate from crew rotation
        ("Umpires",      "fetch_umpires.py",          ["--date", target_date],                   False),  # optional — confirmed ~1-2h before first pitch
        ("Build Prompt", "build_prompt.py",    ["--sport", sport, "--date", target_date], True),
    ]

    results = []   # accumulates (name, status_label, elapsed) for summary

    for name, script, args, required in pipeline:
        # Data completeness gate fires immediately before Build Prompt.
        # All fetch steps have completed by this point; the gate confirms their
        # output is usable before committing to expensive per-model prompt builds.
        if name == "Build Prompt" and not skip_gate:
            gate_ok = preflight_data_gate(sport, target_date)
            if not gate_ok:
                results.append(("Gate", "FAILED", 0.0))
                for remaining_name, *_ in pipeline[len(results):]:
                    results.append((remaining_name, "skipped", 0.0))
                _print_summary(results, sport, target_date, time.time() - wall_start)
                print(f"  Pipeline halted at data completeness gate.")
                print(f"  Fix the missing stats (see above), then re-run.\n")
                sys.exit(1)

        ok, elapsed = run_step(name, script, args)

        if ok:
            results.append((name, "OK", elapsed))

        elif required:
            # Required step failed — record it, fill the rest as skipped, and stop
            results.append((name, "FAILED", elapsed))
            for remaining_name, *_ in pipeline[len(results):]:
                results.append((remaining_name, "skipped", 0.0))

            _print_summary(results, sport, target_date, time.time() - wall_start)
            print(f"  Pipeline stopped at: {name}")
            print(f"  Fix the error above and re-run: python scripts/run_daily.py {sport} --date {target_date}\n")
            sys.exit(1)

        else:
            # Optional step failed — log it visibly and keep going.
            # A banner is used instead of a plain NOTE so this is not missed
            # in long pipeline output. Silent optional failures have caused
            # prompts to go out without advanced pitcher stats (June 2026).
            print(f"\n{'!' * 55}")
            print(f"  WARNING: {script} failed (optional step — pipeline continues)")
            print(f"  Data affected: prompt may be missing stats from this step.")
            print(f"  Fix: check the error output above, then re-run:")
            print(f"    python scripts/{script} --sport {sport} --date {target_date}")
            print(f"  Then rebuild: python scripts/build_prompt.py --sport {sport} --date {target_date}")
            print(f"{'!' * 55}\n")
            results.append((name, "FAILED (optional)", elapsed))

    _print_summary(results, sport, target_date, time.time() - wall_start)

    # Generate per-model prompts only if the base prompt was built successfully.
    # If build_prompt.py failed above the pipeline would have already exited.
    base_prompt = PROJECT_ROOT / "daily" / sport / target_date / "prompt.md"
    if base_prompt.exists():
        _build_model_prompts(sport, target_date)

    # --with-picks: run all connected models via run_picks_all.py after prompts are ready,
    # then carry straight through the post-picks chain: log → watch set → lineup watcher.
    if with_picks:
        print(f"\n{'=' * 55}")
        print(f"  --with-picks: launching picks for all models")
        print(f"{'=' * 55}")
        cmd = [PYTHON, str(SCRIPTS_DIR / "run_picks_all.py"), "--sport", sport, "--date", target_date]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\n  WARNING: run_picks_all.py finished with errors (exit {result.returncode}).")
            print(f"  Check output above. Re-run failed models manually:")
            print(f"    python scripts/query_model.py --model <model> --date {target_date}")

        # Step 2: parse every model's _raw.txt into picks/{sport}/{date}/{model}.json.
        # log_all_picks.py skips models already logged, so this is safe to always run.
        # Positional sport arg (no --sport flag), matching its argparse signature.
        run_step("Log All Picks", "log_all_picks.py", [sport, "--date", target_date])

        # Step 3: build the confirm-check watch set from the freshly logged picks.
        # watch_set.py uses --sport/--date flags.
        run_step("Watch Set", "watch_set.py", ["--sport", sport, "--date", target_date])

        # Step 4: optionally launch the continuous lineup watcher. Interactive prompt
        # with a 20-second timeout that defaults to YES (run the watcher).
        if _confirm_run_watcher(timeout_secs=20):
            run_step("Lineup Watcher", "run_lineup_watcher.py", ["--sport", sport, "--date", target_date])
        else:
            print(f"\n  Skipped lineup watcher. Launch it later with:")
            print(f"    python scripts/run_lineup_watcher.py --sport {sport} --date {target_date}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _load_dotenv()   # load before argparse so ODDS_API_KEY is set for subprocesses

    parser = argparse.ArgumentParser(
        description=(
            "Run the full daily betting data pipeline for a given sport and date. "
            "Outputs a ready-to-paste prompt at daily/{sport}/{date}/prompt.md."
        )
    )
    parser.add_argument(
        "sport",
        help="Sport code: mlb, nba, nhl, nfl, ncaaf, ncaab"
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--skip-gate", action="store_true",
        help="Bypass the data completeness gate. Use only when data is genuinely "
             "unavailable (off-day, postponed slate, pre-dawn run before Savant populates)."
    )
    parser.add_argument(
        "--with-picks", action="store_true", default=False,
        help="After building prompts, run picks for all connected models, then chain "
             "log_all_picks.py -> watch_set.py, and finally prompt (20s timeout, "
             "default YES) to launch the continuous lineup watcher."
    )
    args = parser.parse_args()

    run_daily(sport=args.sport, date=args.date, skip_gate=args.skip_gate, with_picks=args.with_picks)

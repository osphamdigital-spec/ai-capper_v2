#!/usr/bin/env python
"""
scripts/run_daily_2.py

Post-game orchestrator — the counterpart to run_daily.py.
Chains fetch_results → run_postmortem_all → calc_calibration → build_bankroll
in the correct order, with guards, so it stops being run manually
one script at a time.

Usage:
    python scripts/run_daily_2.py mlb
    python scripts/run_daily_2.py mlb --date 2026-06-15
    python scripts/run_daily_2.py mlb --date 2026-06-15 --rerun
    python scripts/run_daily_2.py mlb --date 2026-06-15 --no-grade

Chain (in order):
    1. fetch_results.py        REQUIRED — fetches final scores; auto-chains
                                grade_picks.py internally (unless --no-grade).
                                Also manages post-mortem file (pastes results,
                                creates tomorrow's folder/template/raw stubs).
    2. run_postmortem_all.py   RUNS regardless of individual-model failures —
                                per-model failures are handled internally with
                                retry logic. The orchestrator does not halt on
                                a non-zero exit from this step.

NOTE: fetch_confirmed_data.py (formerly step 2) is retired — confirmed lineup
data is now sourced from games.json context.lineups (written by the watcher
layer). --skip-confirmed is accepted but has no effect.

Pre-flight guard:
    Checks that logged pick files ({model}.json) exist for the target date
    before firing any API calls or writing any files. Halts with a clear
    message if picks haven't been logged yet.

Halt-then-rerun path (Option D):
    If you run too early and confirmed-data halts at step 2:
      - Wait until boxscores are posted (typically 30–60 min after last game)
      - Re-run the exact same command
    On re-run:
      - fetch_results.py is idempotent (skips already-filled placeholders,
        existing folders/stubs; re-grades picks with same results)
      - run_postmortem_all.py fires all 7 models (no postmortem files exist
        yet from the halted first run, so the skip guard doesn't fire)

Prerequisites:
    - Pick files logged: picks/{sport}/{date}/{model}.json must exist
      (produced by run_daily.py --with-picks or manual log_all_picks.py)
    - Games have completed (fetch_results will fail or return in-progress
      scores if called too early)
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Import shared infrastructure from run_daily.py — never duplicate these.
# run_step()      : subprocess wrapper that streams output live, returns (ok, elapsed)
# PYTHON          : explicit Python 3.12 path with packages installed
# SCRIPTS_DIR     : path to scripts/
# PROJECT_ROOT    : project root
# _load_dotenv()  : loads .env into environment before subprocesses are spawned
# today_et()      : returns today's date in US Eastern Time
sys.path.insert(0, str(Path(__file__).parent))
from run_daily import run_step, PYTHON, SCRIPTS_DIR, PROJECT_ROOT, _load_dotenv, today_et


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_roster_models(sport: str) -> list[str]:
    """
    Read docs/model_roster.md and return the list of model names for this sport.
    Same logic as load_model_roster() in fetch_results.py — duplicated here
    to avoid importing fetch_results (which has side-effects on import).
    """
    roster_path = PROJECT_ROOT / "docs" / "model_roster.md"
    if not roster_path.exists():
        return []

    lines      = roster_path.read_text(encoding="utf-8").splitlines()
    target     = f"## {sport.upper()}"
    in_section = False
    models     = []

    for line in lines:
        if line.strip() == target:
            in_section = True
            continue
        if in_section:
            if line.startswith("##"):
                break
            name = line.strip()
            if name:
                models.append(name)

    return models


def _check_logged_picks(sport: str, date: str) -> tuple[bool, int]:
    """
    Verify that at least one {model}.json pick file exists in picks/{sport}/{date}/.

    Checks against actual model names from model_roster.md — not just any *.json —
    to avoid a false pass from stray files.

    Returns (ok, count_found).
    """
    models    = _load_roster_models(sport)
    picks_dir = PROJECT_ROOT / "picks" / sport / date
    found     = []

    for model in models:
        json_path = picks_dir / f"{model}.json"
        if json_path.exists() and json_path.stat().st_size > 0:
            # Verify it's a valid picks doc, not an empty stub
            try:
                doc = json.loads(json_path.read_text(encoding="utf-8"))
                if isinstance(doc.get("picks"), list):
                    found.append(model)
            except (json.JSONDecodeError, OSError):
                pass

    return len(found) > 0, len(found)


def _check_confirmed_data(sport: str, date: str) -> tuple[int, int]:
    """
    Read confirmed_data.json and games.json and return (confirmed_count, slate_count).

    confirmed_count: number of games in confirmed_data.json with actual data
    slate_count:     number of BOXSCORE-ELIGIBLE games on the slate (excludes
                     postponed/cancelled/suspended — those never have boxscores
                     so they must not count toward the denominator or every
                     postponement would false-trigger the partial-check halt)

    Returns (0, 0) if either file is missing.
    By the time this runs, fetch_results.py (step 1) has already written
    result.status into each game in games.json, so the status is readable here.
    """
    # Statuses that will never produce a boxscore — exclude from denominator
    NO_BOXSCORE = {"postponed", "cancelled", "suspended"}

    confirmed_path = PROJECT_ROOT / "data" / sport / date / "confirmed_data.json"
    games_path     = PROJECT_ROOT / "data" / sport / date / "games.json"

    if not confirmed_path.exists() or not games_path.exists():
        return 0, 0

    try:
        confirmed_doc   = json.loads(confirmed_path.read_text(encoding="utf-8"))
        confirmed_count = len(confirmed_doc.get("games", {}))
    except (json.JSONDecodeError, OSError):
        confirmed_count = 0

    try:
        games       = json.loads(games_path.read_text(encoding="utf-8"))
        # Count only games that are expected to have a boxscore
        slate_count = sum(
            1 for g in games
            if g.get("result", {}).get("status") not in NO_BOXSCORE
        )
    except (json.JSONDecodeError, OSError):
        slate_count = 0

    return confirmed_count, slate_count


def _check_picks_integrity(sport: str, date: str) -> tuple[list[str], list[str]]:
    """
    Check each roster model's picks JSON for counts.games == 0.

    counts.games=0 means the picks call failed (empty raw file) or log_picks
    could not extract game blocks from the response. Either way the model has
    no structured game context — its post-mortem would be groundless fabrication.
    counts.bets=0 is NOT a skip trigger; an all-pass slate is a valid outcome.

    Returns (ok_models, skip_models).
    ok_models:   counts.games > 0 — safe to send post-mortem
    skip_models: counts.games == 0 or file missing/unreadable — must be skipped
    """
    models    = _load_roster_models(sport)
    picks_dir = PROJECT_ROOT / "picks" / sport / date
    ok_models   = []
    skip_models = []

    for model in models:
        json_path = picks_dir / f"{model}.json"
        if not json_path.exists():
            skip_models.append(model)
            continue
        try:
            doc   = json.loads(json_path.read_text(encoding="utf-8"))
            games = doc.get("counts", {}).get("games", 0)
            if games > 0:
                ok_models.append(model)
            else:
                skip_models.append(model)
        except (json.JSONDecodeError, OSError):
            skip_models.append(model)

    return ok_models, skip_models


# Minimum chars a valid post-mortem response must contain.
# Matches the same threshold in run_postmortem_all.py.
_PM_MIN_CHARS = 300


def _verify_postmortems(sport: str, date: str, ok_models: list[str]) -> list[str]:
    """
    Check that every model in ok_models has a non-trivial per-model postmortem file.

    ok_models is the list that passed the integrity gate (counts.games > 0).
    Models that were skipped by the integrity gate are excluded — they never
    had valid picks so no postmortem was expected.

    Returns a list of model names whose postmortem is missing or shorter than
    _PM_MIN_CHARS (indicating an empty or truncated response).
    """
    picks_dir  = PROJECT_ROOT / "picks" / sport / date
    incomplete = []

    for model in ok_models:
        pm_file = picks_dir / f"{model}_postmortem.txt"
        size    = pm_file.stat().st_size if pm_file.exists() else 0
        if size < _PM_MIN_CHARS:
            incomplete.append((model, size))

    return incomplete


def _print_section(title: str):
    """Print a consistent section header matching run_daily.py's style."""
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print(f"{'=' * 55}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_post_game(sport: str, date: str = None, no_grade: bool = False,
                  skip_confirmed: bool = False, rerun: bool = False):
    """
    Execute the full post-game pipeline for the given sport and date.

    Resolves date once here and passes the same value to all three steps —
    never re-derives ET date mid-chain.
    """
    target_date = date or today_et()
    wall_start  = time.time()

    _print_section(f"POST-GAME PIPELINE  {sport.upper()}")
    print(f"  Date   : {target_date}")
    print(f"  Started: {datetime.now().strftime('%H:%M ET')}")
    if skip_confirmed:
        print(f"  NOTE   : --skip-confirmed passed (no-op — fetch_confirmed_data.py retired)")

    # ── PRE-FLIGHT: confirm logged pick files exist ───────────────────────────
    # grade_picks.py (auto-chained inside fetch_results) needs {model}.json files.
    # Checking here (before any API calls) gives a clear error instead of a
    # confusing mid-run failure inside fetch_results.
    print(f"\n{'-' * 55}")
    print(f"  PRE-FLIGHT CHECK")
    print(f"{'-' * 55}")

    picks_dir = PROJECT_ROOT / "picks" / sport / target_date
    ok_picks, picks_found = _check_logged_picks(sport, target_date)

    if not ok_picks:
        roster_models = _load_roster_models(sport)
        print(f"  ERROR: No logged pick files found for {target_date}.")
        print(f"  Expected: picks/{sport}/{target_date}/{{model}}.json")
        print(f"  Checked roster models: {', '.join(roster_models) or '(none — check model_roster.md)'}")
        print(f"")
        print(f"  Fix: run pick generation and logging first:")
        print(f"    python scripts/run_daily.py {sport} --date {target_date} --with-picks")
        print(f"  Or manually:")
        print(f"    python scripts/run_picks_all.py --sport {sport} --date {target_date}")
        print(f"    python scripts/log_all_picks.py {sport} --date {target_date}")
        sys.exit(1)

    print(f"  OK — {picks_found} logged pick file(s) found for {target_date}")

    # ── STEP 1: fetch_results.py ──────────────────────────────────────────────
    # Fetches final scores, updates games.json, writes results.json.
    # Auto-chains grade_picks.py unless --no-grade is set.
    # Also manages post-mortem file (pastes results, creates tomorrow's stubs).
    # REQUIRED: halt if this fails — nothing downstream works without results.
    fetch_args = ["--sport", sport, "--date", target_date]
    if no_grade:
        fetch_args.append("--no-grade")

    ok, elapsed = run_step("Fetch Results", "fetch_results.py", fetch_args)
    if not ok:
        print(f"\n  Pipeline stopped at: Fetch Results")
        print(f"  Fix the error above and re-run:")
        print(f"    python scripts/run_daily_2.py {sport} --date {target_date}")
        sys.exit(1)

    # ── PRE-STEP-2: integrity check — filter models with no game context ──────
    # counts.games=0 in a picks JSON means fetch failure or parse failure.
    # Sending a post-mortem for these models produces groundless fabrication.
    # Pass only ok_models to run_postmortem_all via --models flag.
    ok_models, skip_models = _check_picks_integrity(sport, target_date)

    if skip_models:
        print(f"\n  INTEGRITY GATE — skipping {len(skip_models)} model(s) with counts.games=0:")
        for m in skip_models:
            raw_path = PROJECT_ROOT / "picks" / sport / target_date / f"{m}_raw.txt"
            raw_size = raw_path.stat().st_size if raw_path.exists() else 0
            cause = "empty raw file (fetch failure)" if raw_size == 0 else f"parse failure ({raw_size:,}-byte raw)"
            print(f"    {m}: SKIP — {cause}")
        print()

    if not ok_models:
        print(f"  No models with valid picks (counts.games > 0). Skipping post-mortem step.")
        print(f"  Fix picks for at least one model, then re-run:")
        print(f"    python scripts/run_daily_2.py {sport} --date {target_date}")
    else:
        if skip_models:
            print(f"  Proceeding with {len(ok_models)} model(s): {', '.join(ok_models)}")

        # ── STEP 2: run_postmortem_all.py ─────────────────────────────────────
        # Sends post-mortem queries to all clean models via their respective APIs.
        # query_model.py builds the confirmed-data section from games.json
        # context.lineups + {model}_confirm.json (no confirmed_data.json needed).
        #
        # run_postmortem_all handles per-model skipping (already-done guard),
        # one built-in retry per model at 90s, and its own failure summary.
        # We do NOT halt here on non-zero exit — verification below decides
        # whether a retry of the whole pipeline is needed.
        pm_args = ["--sport", sport, "--date", target_date]
        if rerun:
            pm_args.append("--rerun")
        if skip_models:
            # Pass only clean models — prevents query_model.py inner gate from firing
            # redundantly on already-known-bad models (belt-and-braces preserved).
            pm_args.extend(["--models", ",".join(ok_models)])

        run_step("Run Postmortem All", "run_postmortem_all.py", pm_args)

    # ── FINAL VERIFICATION ────────────────────────────────────────────────────
    # Check that every model that had valid picks now has a non-trivial
    # postmortem file on disk. Any model whose file is missing or shorter
    # than _PM_MIN_CHARS chars either failed its API call or was never run.
    #
    # Exit code 2 signals "incomplete — safe to retry" to the PowerShell
    # wrapper (run_daily_2_retry.ps1). On re-run, run_postmortem_all's
    # model_already_done() guard skips completed models automatically so
    # only the missing ones are re-attempted. Steps 1 and 2 are idempotent.
    total_elapsed = time.time() - wall_start

    if ok_models:
        incomplete = _verify_postmortems(sport, target_date, ok_models)

        print(f"\n{'=' * 55}")
        print(f"  VERIFICATION  {sport.upper()}  {target_date}")
        print(f"{'=' * 55}")

        if incomplete:
            print(f"\n  INCOMPLETE — {len(incomplete)} of {len(ok_models)} post-mortem(s) missing or too short:")
            for model, size in incomplete:
                status = "missing" if size == 0 else f"{size} bytes (below {_PM_MIN_CHARS}-char minimum)"
                print(f"    {model}: {status}")
            print(f"\n  On retry, completed models will be skipped automatically.")
            print(f"  Re-run with the retry wrapper:")
            print(f"    .\\run_daily_2_retry.ps1 {sport}")
            print(f"  Or re-run manually (completed models will be skipped):")
            print(f"    python scripts/run_daily_2.py {sport} --date {target_date}")
        else:
            print(f"\n  OK — all {len(ok_models)} post-mortem(s) complete.")

    # ── SIDELINE: LINEUP ACCURACY COMPARISON ──────────────────────────────────
    # Diagnostic only — compares Rotowire EXPECTED (captured pre-game by
    # run_daily.py) vs MLB ACTUAL confirmed lineups vs tracker REGULARS.
    # Always non-fatal; reports coverage if any source is missing.
    print(f"\n{'-' * 55}")
    print(f"  SIDELINE: Lineup accuracy comparison")
    print(f"{'-' * 55}")
    run_step("Compare Lineups", "compare_lineups.py", ["--sport", sport, "--date", target_date])

    # ── STEP 3: CALIBRATION UPDATE ────────────────────────────────────────────
    # Refresh per-model calibration stats after grading is complete.
    # Only runs when postmortems are all OK — avoids partial-night skew.
    # Output: picks/calibration/{model}_calibration.md  (overwrites previous).
    # These files are read by Phase 5b to inject stats into the next prompt.
    if ok_models and not incomplete:
        print(f"\n{'-' * 55}")
        print(f"  STEP 3: Calibration update")
        print(f"{'-' * 55}")
        run_step("Calc Calibration", "calc_calibration.py", ["--sport", sport])

    # ── STEP 4: BANKROLL UPDATE (v3) ──────────────────────────────────────────
    # Rebuild per-model bankroll accounts + leaderboard from graded picks.
    # Idempotent and downstream of grading ONLY — runs whenever grading happened
    # (independent of post-mortem completeness), because the bankroll feeds the
    # NEXT slate's prompt injection and must stay current even on a night where
    # some post-mortems are incomplete. Non-fatal: a failure here never halts the
    # pipeline. Skipped under --no-grade (no fresh results to ingest).
    # Pre-v3: build_bankroll only counts dates >= v3_start_date, so this is a
    # no-op on balances until v3 goes live.
    if not no_grade:
        print(f"\n{'-' * 55}")
        print(f"  STEP 4: Bankroll update (v3)")
        print(f"{'-' * 55}")
        run_step("Build Bankroll", "build_bankroll.py", ["--sport", sport])

    # ── FINAL SUMMARY ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"  POST-GAME PIPELINE COMPLETE  {sport.upper()}  {target_date}")
    print(f"  Total: {total_elapsed:.0f}s")
    print(f"")
    print(f"  Output files:")
    print(f"    results/{sport}/{target_date}/results.json")
    if not no_grade:
        print(f"    results/{sport}/{target_date}/grades.json")
        print(f"    results/{sport}/{target_date}/best_bets.json")

    print(f"    picks/{sport}/{target_date}/{{model}}_postmortem.txt  (x8)")
    print(f"    picks/{sport}/{target_date}/post_mortem_{target_date}.txt")
    if ok_models and not incomplete:
        print(f"    picks/calibration/{{model}}_calibration.md  (x8 — updated)")
    if not no_grade:
        print(f"    bankroll/{sport}/{{model}}.json + _leaderboard.json  (updated)")
    print(f"{'=' * 55}\n")

    # Exit 2 = postmortems incomplete (retry-able). 0 = all good.
    # Exit 1 is reserved for hard pipeline errors (fetch_results failure, etc.)
    # and is raised via sys.exit(1) earlier in the function.
    if ok_models and incomplete:
        sys.exit(2)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _load_dotenv()   # load before argparse so API keys are set for subprocesses

    parser = argparse.ArgumentParser(
        description=(
            "Post-game orchestrator. Chains fetch_results → run_postmortem_all "
            "→ calc_calibration → build_bankroll in the correct order with guards. "
            "Requires logged pick files ({model}.json) to exist for the target date."
        )
    )
    parser.add_argument(
        "sport",
        help="Sport code: mlb, nba, nhl, nfl, ncaaf, ncaab"
    )
    parser.add_argument(
        "--date", default=None,
        help="Slate date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--no-grade", action="store_true",
        help="Skip auto-running grade_picks.py after fetching results."
    )
    parser.add_argument(
        "--skip-confirmed", action="store_true",
        help="Deprecated/no-op. fetch_confirmed_data.py is retired; confirmed data comes from games.json."
    )
    parser.add_argument(
        "--rerun", action="store_true",
        help=(
            "Passed through to run_postmortem_all.py. Clears existing per-model "
            "postmortem files so all models run again (bypasses skip guard)."
        )
    )
    args = parser.parse_args()

    run_post_game(
        sport          = args.sport,
        date           = args.date,
        no_grade       = args.no_grade,
        skip_confirmed = args.skip_confirmed,
        rerun          = args.rerun,
    )

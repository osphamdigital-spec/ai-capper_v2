#!/usr/bin/env python3
"""
scripts/pick_concentration.py

Measure pick concentration for a given slate date: how often are multiple
models betting the same side? High concentration means the models are
converging (unhealthy); low concentration means genuine disagreement (healthy).

LOGIC:
  For each game, collect the side each model bet (action == "bet" only --
  PASS and LEAN are excluded). For games where 3 or more models placed a
  real bet, compute:

    concentration = (models on the most-backed side) / (total models betting that game)

  Report the average concentration across all qualifying games, plus the game count.

OUTPUT:
  Console: one summary line (ASCII only)
  File:    docs/concentration_log.csv (appended, created with header if new)

Usage:
    python scripts/pick_concentration.py --date 2026-06-07
    python scripts/pick_concentration.py                      # defaults to today ET
"""

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from tz_util import ET


PROJECT_ROOT = Path(__file__).parent.parent
LOG_PATH     = PROJECT_ROOT / "docs" / "concentration_log.csv"


def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def load_picks_for_date(sport: str, date: str) -> dict:
    """
    Read all per-model pick JSON files for the given date.
    Returns {model_name: [pick, ...]} -- only picks with action == "bet".
    """
    picks_dir = PROJECT_ROOT / "picks" / sport / date
    if not picks_dir.exists():
        return {}

    model_picks = {}
    for path in sorted(picks_dir.glob("*.json")):
        # Skip combined/grades/results files that may end up here
        stem = path.stem
        if stem.startswith(("grades", "results", "best_bets", "combined")):
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        # Only real bets -- ignore PASS, LEAN, and anything without a side
        bets = [
            p for p in doc.get("picks", [])
            if p.get("action") == "bet" and p.get("pick_raw")
        ]
        if bets:
            model_picks[stem] = bets

    return model_picks


def compute_concentration(model_picks: dict) -> tuple[float | None, int]:
    """
    For each game that received 3+ real bets across all models, compute
    concentration = (bets on the most-popular side) / (total bets on that game).

    Returns (average_concentration, n_qualifying_games).
    average_concentration is None if there are no qualifying games.
    """
    # Group bets by game: {matchup -> {side -> [model, ...]}}
    game_sides: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for model, bets in model_picks.items():
        for pick in bets:
            matchup = pick.get("matchup", "unknown")
            # Use the normalized pick_side + pick_market as the grouping key.
            # This collapses "Under 7.5", "UNDER 7.5 +100", and "Under" into one
            # bucket, since log_picks.py already parsed pick_side="under" for all.
            side    = f"{pick.get('pick_side', '')}:{pick.get('pick_market', '')}"
            if matchup and side != ":":
                game_sides[matchup][side].append(model)

    concentrations = []
    for matchup, sides in game_sides.items():
        total_bets = sum(len(models) for models in sides.values())
        if total_bets < 3:
            continue  # not enough bets on this game to be meaningful

        most_popular = max(len(models) for models in sides.values())
        concentrations.append(most_popular / total_bets)

    if not concentrations:
        return None, 0

    return sum(concentrations) / len(concentrations), len(concentrations)


def append_to_log(date: str, concentration_pct: float, n_games: int) -> None:
    """
    Append one row to docs/concentration_log.csv.
    Creates the file with a header row if it does not exist.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not LOG_PATH.exists()

    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["date", "concentration_pct", "n_games"])
        writer.writerow([date, round(concentration_pct, 1), n_games])


def main():
    parser = argparse.ArgumentParser(
        description="Measure same-side pick concentration across models for a slate date."
    )
    parser.add_argument("--date",  default=None,
                        help="Slate date YYYY-MM-DD. Default: today ET.")
    parser.add_argument("--sport", default="mlb")
    parser.add_argument("--no-log", action="store_true",
                        help="Skip appending to concentration_log.csv.")
    args = parser.parse_args()

    date = args.date or today_et()

    model_picks = load_picks_for_date(args.sport, date)
    if not model_picks:
        print(f"{date}: no model pick files found in picks/{args.sport}/{date}/")
        return

    concentration, n_games = compute_concentration(model_picks)

    if concentration is None:
        print(f"{date}: no games had 3+ bets -- cannot compute concentration")
        return

    pct = round(concentration * 100, 1)
    print(
        f"{date}: concentration {pct}% across {n_games} games (3+ bets each)"
        f"  [{len(model_picks)} models loaded]"
    )

    if not args.no_log:
        append_to_log(date, pct, n_games)


if __name__ == "__main__":
    main()

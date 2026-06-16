#!/usr/bin/env python
"""
scripts/fetch_confirmed_data.py

Fetch post-game confirmed lineups and HP umpire for every game on a slate.
Run AFTER games complete (morning after the slate).

For each game:
  1. Pull batting order from MLB Stats API boxscore
  2. Look up each batter's wRC+ vs opposing starter's handedness (from static splits)
  3. Pull HP umpire name from boxscore officials

Output: data/{sport}/{date}/confirmed_data.json
This file is consumed by query_model.py when building post-mortem prompts.

NOT for use in pick-generation prompts. Evaluation only.

Usage:
    python scripts/fetch_confirmed_data.py mlb --date 2026-06-15
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Add scripts/ to path so load_static_data is importable
sys.path.insert(0, str(Path(__file__).parent))
from load_static_data import load_splits_vs_lhp, load_splits_vs_rhp, fuzzy_match_player
from tz_util import ET

MLB_API_BASE  = "https://statsapi.mlb.com/api/v1"
PROJECT_ROOT  = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# API HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _api_get(url: str, params: dict | None = None) -> dict:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


# ─────────────────────────────────────────────────────────────────────────────
# CORE FETCH
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_game_confirmed(game: dict, splits_lhp: dict, splits_rhp: dict) -> dict | None:
    """
    Fetch confirmed lineup + HP umpire for one game via its gamePk (mlb_game_pk).
    Returns a dict with lineup and umpire data, or None if boxscore unavailable.
    """
    pk = game.get("mlb_game_pk") or game.get("context", {}).get("mlb_game_pk")
    if not pk:
        return None

    away_abbr = game["away"]["abbr"]
    home_abbr = game["home"]["abbr"]
    matchup   = f"{away_abbr} @ {home_abbr}"

    try:
        bs = _api_get(f"{MLB_API_BASE}/game/{pk}/boxscore")
    except Exception as e:
        print(f"  {matchup}: boxscore fetch failed — {e}")
        return None

    teams = bs.get("teams", {})
    officials = bs.get("officials", [])

    # ── HP umpire ─────────────────────────────────────────────────────────────
    hp_umpire = None
    for o in officials:
        if "Plate" in o.get("officialType", ""):
            hp_umpire = o.get("official", {}).get("fullName")
            break

    # ── Batting orders ────────────────────────────────────────────────────────
    # Opposing pitcher's handedness determines which split file to use.
    ctx = game.get("context", {})
    away_sp_hand = (ctx.get("pitcher_away") or {}).get("hand", "R")  # default R if TBD
    home_sp_hand = (ctx.get("pitcher_home") or {}).get("hand", "R")

    result = {
        "game_pk":       pk,
        "matchup":       matchup,
        "umpire":        hp_umpire,
        "away_sp_hand":  away_sp_hand,
        "home_sp_hand":  home_sp_hand,
        "away_lineup":   [],
        "home_lineup":   [],
    }

    for side, opp_hand, key in (
        ("away", home_sp_hand, "away"),   # away bats vs home SP
        ("home", away_sp_hand, "home"),   # home bats vs away SP
    ):
        team_data  = teams.get(side, {})
        batting_order = team_data.get("battingOrder", [])
        players_map   = team_data.get("players", {})
        splits         = splits_lhp if opp_hand == "L" else splits_rhp
        split_label    = f"vs_{'LHP' if opp_hand == 'L' else 'RHP'}"

        lineup_entries = []
        wrc_values     = []

        for pid in batting_order:
            player_rec  = players_map.get(f"ID{pid}", {})
            full_name   = player_rec.get("person", {}).get("fullName", f"ID{pid}")
            split_key   = fuzzy_match_player(full_name, splits)
            wrc_plus    = splits[split_key]["wrc_plus"] if split_key else None
            if wrc_plus is not None:
                wrc_values.append(wrc_plus)
            lineup_entries.append({
                "name":       full_name,
                "wrc_plus":   wrc_plus,
                "split_used": split_label,
            })

        result[f"{key}_lineup"] = lineup_entries
        result[f"{key}_avg_wrc"] = (
            round(sum(wrc_values) / len(wrc_values), 1) if wrc_values else None
        )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run(sport: str, date: str):
    games_path = PROJECT_ROOT / "data" / sport / date / "games.json"
    out_path   = PROJECT_ROOT / "data" / sport / date / "confirmed_data.json"

    if not games_path.exists():
        print(f"ERROR: {games_path} not found")
        sys.exit(1)

    games = json.loads(games_path.read_text(encoding="utf-8"))
    print(f"\n{'='*55}")
    print(f"  FETCH CONFIRMED DATA  {sport.upper()}  {date}")
    print(f"  {len(games)} game(s)")
    print(f"{'='*55}\n")

    # Load splits once
    print("Loading static splits...")
    splits_lhp = load_splits_vs_lhp()
    splits_rhp = load_splits_vs_rhp()
    print(f"  vs LHP: {len(splits_lhp)} batters | vs RHP: {len(splits_rhp)} batters\n")

    confirmed = {}
    for game in games:
        away = game["away"]["abbr"]
        home = game["home"]["abbr"]
        matchup = f"{away} @ {home}"
        print(f"  Fetching {matchup}...")
        data = _fetch_game_confirmed(game, splits_lhp, splits_rhp)
        if data:
            confirmed[matchup] = data
            lu_count = len(data.get("away_lineup", []))
            ump = data.get("umpire", "unknown")
            print(f"    {lu_count}+{lu_count} batters | HP: {ump}")
        else:
            print(f"    SKIPPED (no data)")

    output = {
        "date":       date,
        "sport":      sport,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "games":      confirmed,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nSaved -> {out_path.relative_to(PROJECT_ROOT)}")
    print(f"Games with data: {len(confirmed)}/{len(games)}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch confirmed lineups + HP umpire for post-mortem evaluation."
    )
    parser.add_argument("sport", help="Sport code: mlb")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today ET)")
    args = parser.parse_args()

    date = args.date or datetime.now(ET).strftime("%Y-%m-%d")
    run(args.sport, date)

#!/usr/bin/env python
"""
scripts/fetch_umpire_inference.py

Infers today's plate umpire from yesterday's crew rotation for series
continuations, and writes the estimate into games.json before the official
assignment is available.

HOW THE ROTATION WORKS
  MLB uses 4-man umpire crews that rotate positions each game within a series:
    HP -> 3B -> 2B -> 1B -> HP  (clockwise)
  Therefore: whoever was at 2B in Game N is at HP in Game N+1.

WHEN THIS APPLIES
  Only for series continuations (seriesGameNumber > 1 today and same matchup
  yesterday). For new series (game 1 of a new series), the crew is re-assigned
  to a different city — without knowing which crew goes where, inference is not
  possible. Those games are left as "unassigned".

ACCURACY
  ~85-90% within an active series. Breaks on: off days, injury replacements,
  ejection replacements, crew reshuffles at the All-Star break.

OUTPUT
  Writes context.umpire with status="inferred" for inferable games.
  fetch_umpires.py overwrites inferred values with status="assigned" once
  MLB publishes the confirmed assignment (~1-2 hours before first pitch).
  Already-confirmed games (status="assigned") are never touched.

TIMING
  Run immediately after yesterday's games complete (any time overnight).
  Provides an early estimate for the morning prompt.

Usage:
    python scripts/fetch_umpire_inference.py
    python scripts/fetch_umpire_inference.py --date 2026-06-05
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path
from tz_util import ET


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def yesterday_of(date_str: str) -> str:
    d = date_cls.fromisoformat(date_str)
    return (d - timedelta(days=1)).strftime("%Y-%m-%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(url: str, params: dict = None) -> dict | None:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  ERROR: HTTP {e.code} -- {url}")
        return None
    except urllib.error.URLError as e:
        print(f"  ERROR: Connection failed -- {e.reason}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MLB SCHEDULE QUERIES
# ─────────────────────────────────────────────────────────────────────────────

def fetch_schedule_with_officials(date_str: str) -> list:
    """
    Returns list of game dicts from the schedule API with officials hydrated.
    Each dict has: gamePk, away_id, home_id, seriesGameNumber, officials[].
    """
    data = api_get(f"{MLB_API_BASE}/schedule", {
        "sportId": 1,
        "date":    date_str,
        "hydrate": "officials",
    })
    if not data:
        return []

    games = []
    for date_block in data.get("dates", []):
        for g in date_block.get("games", []):
            games.append({
                "gamePk":           g.get("gamePk"),
                "away_id":          g["teams"]["away"]["team"]["id"],
                "home_id":          g["teams"]["home"]["team"]["id"],
                "seriesGameNumber": g.get("seriesGameNumber", 1),
                "officials":        g.get("officials", []),
            })
    return games


def extract_positions(officials: list) -> dict:
    """
    Return {"Home Plate": name, "First Base": name, ...} from officials list.
    Returns empty dict if officials list is empty.
    """
    result = {}
    for o in officials:
        otype = o.get("officialType")
        name  = o.get("official", {}).get("fullName")
        if otype and name:
            result[otype] = name
    return result


# ─────────────────────────────────────────────────────────────────────────────
# INFERENCE LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def build_inference_map(target_date: str) -> dict:
    """
    Return {(away_id, home_id): inferred_hp_name} for series continuations.

    Steps:
    1. Fetch today's schedule to find games where seriesGameNumber > 1.
    2. Fetch yesterday's schedule with officials to get crew assignments.
    3. For each continuation game, look up yesterday's same matchup and
       extract the 2B umpire — that is today's inferred HP.

    Returns an empty entry (None) for games where inference isn't possible.
    """
    yesterday = yesterday_of(target_date)

    print(f"  Fetching today's schedule ({target_date}) for series context...")
    today_games = fetch_schedule_with_officials(target_date)

    print(f"  Fetching yesterday's officials ({yesterday}) for crew positions...")
    yest_games  = fetch_schedule_with_officials(yesterday)

    # Build lookup: (away_id, home_id) -> crew positions from yesterday
    yest_crews = {}
    for g in yest_games:
        positions = extract_positions(g["officials"])
        if positions:
            yest_crews[(g["away_id"], g["home_id"])] = positions

    print(f"  Yesterday: {len(yest_crews)} game(s) with confirmed officials")

    inference_map = {}
    for g in today_games:
        key             = (g["away_id"], g["home_id"])
        series_game_num = g["seriesGameNumber"]

        if series_game_num <= 1:
            # Game 1 of a new series — crew assignment unknown, cannot infer
            inference_map[key] = None
            continue

        yest_positions = yest_crews.get(key)
        if not yest_positions:
            # Series continuation but yesterday's officials not found (off day,
            # postponement, or data gap) — cannot infer
            inference_map[key] = None
            continue

        # Rotation: 2B yesterday -> HP today
        inferred_hp = yest_positions.get("Second Base")
        inference_map[key] = inferred_hp

    return inference_map, yest_crews, today_games


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_umpire_inference(date: str = None):
    target_date = date or today_et()
    yesterday   = yesterday_of(target_date)

    print(f"\n{'='*58}")
    print(f"  UMPIRE INFERENCE  MLB")
    print(f"  Date:      {target_date}")
    print(f"  Yesterday: {yesterday}")
    print(f"  Method:    crew rotation (2B yesterday -> HP today)")
    print(f"  Scope:     series continuations only (seriesGameNumber > 1)")
    print(f"{'='*58}\n")

    project_root = Path(__file__).parent.parent
    games_path   = project_root / "data" / "mlb" / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        print("  Run fetch_odds.py first.")
        sys.exit(1)

    with open(games_path, encoding="utf-8") as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games from games.json\n")

    # Build the inference map (requires 2 API calls total)
    inference_map, yest_crews, today_sched = build_inference_map(target_date)

    # Build a lookup from team IDs in today's schedule to match games.json
    # games.json uses team names; schedule API uses team IDs
    # We match by gamePk (already stored by fetch_pitchers.py)
    pk_to_key = {}
    for g in today_sched:
        pk_to_key[g["gamePk"]] = (g["away_id"], g["home_id"])

    print("\nStep 3: Applying inference to games.json...")
    fetched_at = now_utc()
    inferred   = 0
    skipped    = 0
    new_series = 0
    already_confirmed = 0

    for game in games:
        matchup = f"{game['away']['abbr']} @ {game['home']['abbr']}"
        pk      = game.get("mlb_game_pk")
        ctx     = game.get("context") or {}

        # Never overwrite a confirmed umpire
        existing = ctx.get("umpire", {})
        if existing.get("status") == "assigned":
            already_confirmed += 1
            print(f"  -- {matchup}: already confirmed ({existing['name']}) -- skipping")
            game["context"] = ctx
            continue

        # Find the team ID key for this game
        key = pk_to_key.get(pk) if pk else None
        if not key:
            skipped += 1
            print(f"  ?? {matchup}: no gamePk match in schedule -- skipping")
            game["context"] = ctx
            continue

        inferred_name = inference_map.get(key)  # None if new series or data gap

        if inferred_name:
            # Write the inferred assignment
            ctx["umpire"] = {
                "name":            inferred_name,
                "source":          "crew_rotation_inference",
                "source_priority": 2,            # lower than mlb_official (1)
                "fetched_at":      fetched_at,
                "status":          "inferred",
                "note":            "2B umpire from yesterday's game — ~85-90% accurate within a series. Confirm with fetch_umpires.py before first pitch.",
            }
            game["context"] = ctx
            inferred += 1
            print(f"  EST {matchup}: {inferred_name} (inferred from yesterday's 2B)")
        else:
            # New series or data gap — leave as unassigned / don't overwrite
            new_series += 1
            print(f"  --- {matchup}: game 1 of new series -- cannot infer")
            game["context"] = ctx

    # Save
    with open(games_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)

    print(f"\nSaved -> {games_path.relative_to(project_root)}")
    print(f"\n{'='*58}")
    print(f"  INFERENCE SUMMARY  {target_date}")
    print(f"{'='*58}")
    print(f"  Inferred (series cont.):  {inferred}")
    print(f"  New series (no data):     {new_series}")
    if already_confirmed:
        print(f"  Already confirmed:        {already_confirmed}")
    if skipped:
        print(f"  Skipped (no gamePk):      {skipped}")
    print(f"\n  NOTE: inferred values are ~85-90% accurate within a series.")
    print(f"  Run fetch_umpires.py 1-2 hrs before first pitch to confirm.")
    print(f"{'='*58}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Infer plate umpires from yesterday's crew rotation for series continuations."
    )
    parser.add_argument("--date", default=None,
        help="Target slate date YYYY-MM-DD. Default: today ET.")
    args = parser.parse_args()
    fetch_umpire_inference(date=args.date)

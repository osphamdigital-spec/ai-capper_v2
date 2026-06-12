#!/usr/bin/env python
"""
scripts/fetch_umpires.py

Fetch plate umpire assignments and write context.umpire into each game
in data/mlb/[date]/games.json.

Source:  MLB Stats API schedule endpoint with officials hydration (official, free)
         GET https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=DATE&hydrate=officials
         One call covers all games — more efficient than 15 separate boxscore calls.

Timing:  Officials populate approximately 1-2 hours before first pitch.
         For a 6:40 PM ET game, run at ~4:30-5:00 PM ET.
         Morning runs will show status="unassigned" — this is correct behaviour.
         Re-run closer to game time to pick up assignments.

Join key: mlb_game_pk stored in games.json by fetch_pitchers.py.
          Matched against gamePk in the schedule response.

Usage:
    python scripts/fetch_umpires.py
    python scripts/fetch_umpires.py --date 2026-06-01

Modifies:
    data/mlb/[date]/games.json  -- writes context.umpire for each game
    All other fields (odds, pitchers, weather) are never touched.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tz_util import ET


MLB_API_BASE = "https://statsapi.mlb.com/api/v1"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(url: str, params: dict = None) -> dict | None:
    """HTTP GET using stdlib urllib. Returns parsed JSON or None on error."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  ERROR: HTTP {e.code} — {url}")
        return None
    except urllib.error.URLError as e:
        print(f"  ERROR: Connection failed — {e.reason}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MLB API CALLS
# ─────────────────────────────────────────────────────────────────────────────

def fetch_all_officials(date: str) -> dict:
    """
    Fetch all umpire assignments for a date in one API call via schedule?hydrate=officials.
    Returns {gamePk: plate_umpire_name_or_None}.

    One call covers the full slate — more efficient than one boxscore per game.
    Officials populate ~1-2 hours before first pitch; None means not yet assigned.
    """
    data = api_get(f"{MLB_API_BASE}/schedule", {
        "sportId": 1,
        "date":    date,
        "hydrate": "officials",
    })
    if not data:
        return {}

    result = {}
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            pk        = game.get("gamePk")
            hp_name   = None
            for official in game.get("officials", []):
                if official.get("officialType") == "Home Plate":
                    hp_name = official.get("official", {}).get("fullName")
                    break
            result[pk] = hp_name

    return result


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_umpires(date: str = None):
    """
    Fetch plate umpire assignments and write into games.json context blocks.
    Uses a single schedule?hydrate=officials call for the entire slate.
    """
    target_date = date or today_et()

    print(f"\n{'='*55}")
    print(f"  FETCH UMPIRES — MLB")
    print(f"  Source:  MLB Stats API schedule?hydrate=officials")
    print(f"  Date:    {target_date}")
    print(f"  NOTE:    Assignments post ~1-2 hrs before first pitch.")
    print(f"{'='*55}\n")

    # ── Load games.json ───────────────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    games_path = project_root / "data" / "mlb" / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        print("Run fetch_odds.py first.")
        sys.exit(1)

    with open(games_path) as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games\n")

    # ── Single API call for all officials ─────────────────────────────────────
    print("Step 1: Fetching all officials via schedule?hydrate=officials...")
    officials_by_pk = fetch_all_officials(target_date)
    print(f"  Received {len(officials_by_pk)} games from schedule API\n")

    # ── Write umpire into each game ───────────────────────────────────────────
    print("Step 2: Matching officials to games.json...")
    fetched_at = now_utc()
    assigned   = 0
    unassigned = 0

    for game in games:
        matchup = f"{game['away']['abbr']} @ {game['home']['abbr']}"
        pk      = game.get("mlb_game_pk")

        umpire_name = officials_by_pk.get(pk) if pk else None

        umpire_entry = {
            "name":            umpire_name,
            "source":          "mlb_official",
            "source_priority": 1,
            "fetched_at":      fetched_at,
            "status":          "assigned" if umpire_name else "unassigned",
        }

        # Preserve all existing context fields
        ctx = game.get("context") or {}
        ctx["umpire"] = umpire_entry
        game["context"] = ctx

        if umpire_name:
            assigned += 1
            print(f"  OK {matchup}: {umpire_name}")
        else:
            print(f"  -- {matchup}: not yet assigned  (gamePk={pk})")
            unassigned += 1

    # ── Save ──────────────────────────────────────────────────────────────────
    with open(games_path, "w") as f:
        json.dump(games, f, indent=2)

    print(f"\nStep 3: Saved -> {games_path.relative_to(project_root)}\n")

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"{'='*55}")
    print(f"  UMPIRE SUMMARY")
    print(f"{'='*55}")
    print(f"  {'Matchup':<22}  {'Plate Umpire':<28}  Status")
    print(f"  {'-'*58}")

    for game in games:
        matchup     = f"{game['away']['abbr']} @ {game['home']['abbr']}"
        u           = game["context"].get("umpire", {})
        name        = u.get("name") or "— not yet assigned —"
        status      = u.get("status", "?")
        flag        = "OK" if status == "assigned" else "--"
        print(f"  {flag} {matchup:<20}  {name:<28}  {status}")

    print(f"\n  Assigned:   {assigned}")
    print(f"  Unassigned: {unassigned}")
    print(f"  Total:      {len(games)}")

    if unassigned > 0:
        # Find the earliest unassigned game time and suggest a re-run window
        earliest = None
        for game in games:
            if game["context"].get("umpire", {}).get("status") == "unassigned":
                try:
                    dt = datetime.fromisoformat(game["commence_et"])
                    if earliest is None or dt < earliest:
                        earliest = dt
                except Exception:
                    pass

        if earliest:
            suggest = (earliest - timedelta(hours=2)).strftime("%I:%M %p ET")
            print(f"\n  Re-run at {suggest} (2 hours before first pitch)")
            print(f"  Assignments are usually posted by then.")

    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch MLB plate umpire assignments from the MLB Stats API."
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time.",
    )
    args = parser.parse_args()

    fetch_umpires(date=args.date)

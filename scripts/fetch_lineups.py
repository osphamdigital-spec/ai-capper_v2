#!/usr/bin/env python
"""
scripts/fetch_lineups.py

Fetch confirmed starting lineups and IL injury absences for both teams
in each game on the slate.

Lineups are only confirmed ~2-3 hours before first pitch. If not yet
posted, status is recorded as "not_yet_confirmed" and the script
exits cleanly — this is expected behaviour for morning runs.

Sources (MLB Stats API — no auth required):
  Lineups:   GET /api/v1/schedule?sportId=1&date=DATE&hydrate=lineups
             Returns awayPlayers / homePlayers arrays in batting order.
             NOTE: /game/{gamePk}/lineups returns 404 consistently — do not use.
  IL roster: GET /api/v1/teams/{teamId}/roster?rosterType=40Man&season=YEAR

Prerequisites:
  - fetch_pitchers.py must have run (provides game["mlb_game_pk"] for matching)
  - fetch_teamstats.py must have run (provides ctx["team_away"]["team_id"])

Usage:
    python scripts/fetch_lineups.py
    python scripts/fetch_lineups.py --date 2026-06-05
    python scripts/fetch_lineups.py --sport mlb --date 2026-06-05

Modifies:
    data/{sport}/{date}/games.json
    Writes context.lineups for each game. Structure:
      {
        "away": {
          "status": "confirmed" | "not_yet_confirmed",
          "order":  [{"name": "Juan Soto", "pos": "LF", "bat_order": 1}, ...]
          "il_absences": [{"name": "Aaron Judge", "pos": "RF"}, ...]
        },
        "home": { same structure }
      }
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tz_util import ET


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

# Any status description containing these strings counts as an IL placement
IL_KEYWORDS = ("IL", "Injured List")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(url: str, params: dict = None) -> dict | None:
    """HTTP GET via stdlib urllib. Returns parsed JSON or None on error."""
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
# LINEUP FETCH — one schedule call for all games
# ─────────────────────────────────────────────────────────────────────────────

def fetch_all_lineups(date: str) -> dict:
    """
    Fetch lineups for all games on a given date via schedule?hydrate=lineups.
    Returns {gamePk: {"awayPlayers": [...], "homePlayers": [...]}} for games
    that have lineups posted; empty dict for games not yet confirmed.

    The /game/{gamePk}/lineups endpoint returns 404 consistently and should
    not be used. The schedule hydrate approach works and returns players in
    batting order.
    """
    data = api_get(f"{MLB_API_BASE}/schedule", {
        "sportId": 1,
        "date":    date,
        "hydrate": "lineups",
    })
    if not data:
        return {}

    result = {}
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            pk      = game.get("gamePk")
            lineups = game.get("lineups", {})
            # lineups is {} when not yet posted, populated when confirmed
            if pk and lineups:
                result[pk] = lineups

    return result


def parse_player_list(players: list) -> list:
    """
    Convert a raw awayPlayers/homePlayers list into batting-order dicts.
    The list is already in batting order as returned by the API.
    """
    order = []
    for i, player in enumerate(players, start=1):
        name = player.get("fullName", "Unknown")
        pos  = player.get("primaryPosition", {}).get("abbreviation", "")
        order.append({"name": name, "pos": pos, "bat_order": i})
    return order


# ─────────────────────────────────────────────────────────────────────────────
# IL ROSTER FETCH + PARSE
# ─────────────────────────────────────────────────────────────────────────────

def fetch_il_players(team_id: int, season: str) -> list:
    """
    Fetch the 40-man roster for a team and return players on the IL.

    Players on the IL have a status.description field containing "IL"
    (e.g. "10-Day IL", "15-Day IL", "60-Day IL").

    Returns list of {"name": ..., "pos": ...} dicts.
    """
    data = api_get(f"{MLB_API_BASE}/teams/{team_id}/roster", {
        "rosterType": "40Man",
        "season":     season,
    })
    if not data:
        return []

    il_players = []
    for player in data.get("roster", []):
        status_desc = player.get("status", {}).get("description", "")
        if any(kw in status_desc for kw in IL_KEYWORDS):
            name = player.get("person", {}).get("fullName", "Unknown")
            pos  = player.get("position", {}).get("abbreviation", "")
            il_players.append({"name": name, "pos": pos})

    return il_players


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_lineups(sport: str = "mlb", date: str = None):
    """
    For each game on the slate: fetch confirmed lineup + IL absences and
    write into context.lineups in games.json.

    Uses schedule?hydrate=lineups for a single API call covering all games.
    Falls back to not_yet_confirmed for any game without lineups posted.
    """
    target_date = date or today_et()
    season      = target_date[:4]

    print(f"\n{'='*55}")
    print(f"  FETCH LINEUPS  {sport.upper()}")
    print(f"  Date:    {target_date}")
    print(f"  Sources: MLB Stats API schedule?hydrate=lineups + /roster (40Man)")
    print(f"{'='*55}\n")

    project_root = Path(__file__).parent.parent
    games_path   = project_root / "data" / sport / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        print("  Run fetch_odds.py first.")
        sys.exit(1)

    with open(games_path, encoding="utf-8") as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games\n")

    # Single API call for all lineup data
    print("Step 1: Fetching all lineups via schedule?hydrate=lineups...")
    lineup_by_pk = fetch_all_lineups(target_date)
    print(f"  Games with lineups confirmed: {len(lineup_by_pk)} / {len(games)}\n")

    confirmed  = 0
    not_yet    = 0
    fetched_at = now_utc()

    for game in games:
        away    = game["away"]
        home    = game["home"]
        matchup = f"{away['abbr']} @ {home['abbr']}"
        ctx     = game.get("context") or {}

        game_pk = game.get("mlb_game_pk")
        raw     = lineup_by_pk.get(game_pk) if game_pk else None

        if raw:
            # Lineups are confirmed
            away_order = parse_player_list(raw.get("awayPlayers", []))
            home_order = parse_player_list(raw.get("homePlayers", []))

            away_lineup = {"status": "confirmed",          "order": away_order, "il_absences": []}
            home_lineup = {"status": "confirmed",          "order": home_order, "il_absences": []}
        else:
            away_lineup = {"status": "not_yet_confirmed",  "order": [],         "il_absences": []}
            home_lineup = {"status": "not_yet_confirmed",  "order": [],         "il_absences": []}

        # IL absences — only if team_id is available (requires fetch_teamstats.py)
        away_team_id = (ctx.get("team_away") or {}).get("team_id")
        home_team_id = (ctx.get("team_home") or {}).get("team_id")

        if away_team_id:
            away_lineup["il_absences"] = fetch_il_players(int(away_team_id), season)
        if home_team_id:
            home_lineup["il_absences"] = fetch_il_players(int(home_team_id), season)

        ctx["lineups"] = {
            "away":       away_lineup,
            "home":       home_lineup,
            "fetched_at": fetched_at,
        }
        game["context"] = ctx

        if raw:
            confirmed += 1
            away_n  = len(away_lineup["order"])
            home_n  = len(home_lineup["order"])
            away_il = len(away_lineup.get("il_absences", []))
            home_il = len(home_lineup.get("il_absences", []))
            print(
                f"  {matchup}: confirmed "
                f"({away_n} away batters, {away_il} IL) / "
                f"({home_n} home batters, {home_il} IL)"
            )
        else:
            not_yet += 1
            print(f"  {matchup}: not yet confirmed")

    # Save
    with open(games_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)

    print(f"\nSaved -> {games_path.relative_to(project_root)}")
    print(f"\n{'='*55}")
    print(f"  DONE")
    print(f"  Confirmed:    {confirmed}")
    print(f"  Not yet:      {not_yet}")
    if not_yet and confirmed == 0:
        print(f"  NOTE: lineups usually post 2-3 hours before first pitch")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch confirmed lineups and IL absences into games.json context block."
    )
    parser.add_argument("--sport", default="mlb",
        help="Sport code (default: mlb)")
    parser.add_argument("--date", default=None,
        help="Slate date YYYY-MM-DD. Default: today ET.")
    args = parser.parse_args()
    fetch_lineups(sport=args.sport, date=args.date)

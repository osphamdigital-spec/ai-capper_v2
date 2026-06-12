#!/usr/bin/env python
"""
scripts/fetch_pitchers.py

Fetch probable pitcher data from the MLB Stats API and write it into the
context block of each game in data/mlb/[date]/games.json.

Sources (per the agreed source priority hierarchy):
  Pitchers: MLB Stats API (source_priority=1)  >  Covers (source_priority=2)
  This script uses source_priority=1 only.

Two API calls are made:
  1. GET /api/v1/schedule?sportId=1&date=DATE&hydrate=probablePitcher
     Returns game list + pitcher IDs and names.
  2. GET /api/v1/people/{id}?hydrate=stats(group=[pitching],type=[season],season=YEAR)
     Returns pitchHand (L/R) + season ERA, WHIP, K, IP, W, L.
     One call per unique pitcher found. Up to 18 calls for a full 9-game slate.

Join key:
  Games are matched by (away_team_name, home_team_name) pair.
  Both TheOddsAPI and MLB Stats API use identical official full team names.

Usage:
    python scripts/fetch_pitchers.py
    python scripts/fetch_pitchers.py --date 2026-06-01
    python scripts/fetch_pitchers.py --show-api    # print raw API responses

Modifies:
    data/mlb/[date]/games.json  -- writes context.pitcher_away and context.pitcher_home
    Odds data is never touched.
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


# Official MLB Stats API — no key required, powers MLB.com
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    """Return current time as UTC ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hours_until_game(commence_utc: str | None) -> float | None:
    """
    Return how many hours remain until the game starts, as a float.
    commence_utc is the ISO 8601 UTC string stored in games.json by fetch_odds.py
    (e.g. "2026-06-08T17:05:00Z"). Returns None if missing or unparseable.
    Negative = game already started.
    """
    if not commence_utc:
        return None
    try:
        game_time = datetime.fromisoformat(commence_utc.rstrip("Z")).replace(
            tzinfo=timezone.utc
        )
        return (game_time - datetime.now(timezone.utc)).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def api_get(url: str, params: dict = None) -> dict | None:
    """
    HTTP GET using stdlib urllib. Returns parsed JSON or None on error.
    The MLB Stats API requires no authentication.
    """
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
# MLB STATS API CALLS
# ─────────────────────────────────────────────────────────────────────────────

def fetch_schedule(date: str) -> dict | None:
    """
    Fetch the MLB schedule for a given date with probable pitchers.
    Returns the raw API response dict.
    """
    return api_get(f"{MLB_API_BASE}/schedule", {
        "sportId": 1,        # 1 = MLB
        "date":    date,
        "hydrate": "probablePitcher",
    })


def fetch_player(player_id: int, season: str) -> dict | None:
    """
    Fetch a player's details and season pitching stats.
    Returns the raw 'people[0]' dict from the API, or None on error.

    The hydrate syntax for stats uses square brackets:
      group=[pitching]   — pitching stat group
      type=[season]      — full season totals (not splits by month etc)
      season=2026        — the season year
    """
    data = api_get(f"{MLB_API_BASE}/people/{player_id}", {
        "hydrate": f"stats(group=[pitching],type=[season],season={season})",
    })
    if not data or not data.get("people"):
        return None
    return data["people"][0]


# ─────────────────────────────────────────────────────────────────────────────
# PARSING — raw API data → canonical context fields
# ─────────────────────────────────────────────────────────────────────────────

def parse_player_stats(player_data: dict) -> dict:
    """
    Extract pitchHand and season stats from a /people/{id} response.
    Returns a flat dict with the fields we store in the context block.

    Stats are stored as ERA = float (e.g. 2.15), WHIP = float (e.g. 0.87).
    The API returns ERA and WHIP as strings — we convert to float.
    A "-" value means no games pitched yet; we store None.
    """
    result = {
        "hand":            None,
        "era":             None,
        "whip":            None,
        "strikeouts":      None,
        "innings_pitched": None,
        "wins":            None,
        "losses":          None,
        # FIP components — all standard fields in the season pitching stats response
        "home_runs":       None,   # HR  (homeRuns)
        "walks":           None,   # BB  (baseOnBalls)
        "hit_batters":     None,   # HBP (hitBatsmen)
    }

    if not player_data:
        return result

    # pitchHand is on the top-level person object (not inside stats)
    pitch_hand = player_data.get("pitchHand", {})
    result["hand"] = pitch_hand.get("code")   # "L" or "R"

    # Season stats are inside the stats array
    for stat_group in player_data.get("stats", []):
        # Find the season totals group (not monthly splits etc)
        if stat_group.get("type", {}).get("displayName") == "season":
            splits = stat_group.get("splits", [])
            if splits:
                s = splits[0].get("stat", {})
                # Convert ERA and WHIP from string to float, handle "-" = None
                def safe_float(val):
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return None

                result["era"]             = safe_float(s.get("era"))
                result["whip"]            = safe_float(s.get("whip"))
                result["strikeouts"]      = s.get("strikeOuts")
                result["innings_pitched"] = s.get("inningsPitched")
                result["wins"]            = s.get("wins")
                result["losses"]          = s.get("losses")
                result["home_runs"]       = s.get("homeRuns")
                result["walks"]           = s.get("baseOnBalls")
                result["hit_batters"]     = s.get("hitBatsmen")
                break

    return result


def build_pitcher_entry(probable_pitcher: dict, player_data: dict) -> dict | None:
    """
    Build the canonical pitcher context entry from schedule + player data.

    probable_pitcher: the probablePitcher object from the schedule response
    player_data:      the people[0] object from the /people/{id} response

    Returns None if no probable pitcher was announced for this game.
    """
    if not probable_pitcher:
        return None

    stats = parse_player_stats(player_data)

    return {
        # ── Identity ───────────────────────────────────────────────
        "name":    probable_pitcher.get("fullName"),
        "mlb_id":  probable_pitcher.get("id"),
        "hand":    stats["hand"],      # L | R  (from /people endpoint)

        # ── Status ────────────────────────────────────────────────
        # MLB only publishes "probable" pre-game. "confirmed" = closer to first pitch.
        "status":  "probable",

        # ── Season stats ──────────────────────────────────────────
        "era":             stats["era"],
        "whip":            stats["whip"],
        "strikeouts":      stats["strikeouts"],
        "innings_pitched": stats["innings_pitched"],
        "wins":            stats["wins"],
        "losses":          stats["losses"],
        # FIP components — needed by fetch_pitcher_advanced.py:compute_fip()
        "home_runs":       stats["home_runs"],
        "walks":           stats["walks"],
        "hit_batters":     stats["hit_batters"],

        # ── Provenance ────────────────────────────────────────────
        "source":          "mlb_official",
        "source_priority": 1,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_pitchers(date: str = None, show_api: bool = False):
    """
    Fetch probable pitcher data and write it into games.json context blocks.

    Args:
        date:     Override target date (YYYY-MM-DD). Default: today ET.
        show_api: If True, print raw API responses for inspection.
    """
    target_date = date or today_et()
    season = target_date[:4]   # "2026" — used for season stats query

    print(f"\n{'='*55}")
    print(f"  FETCH PITCHERS — MLB")
    print(f"  Slate date (US ET): {target_date}")
    print(f"  Season:             {season}")
    print(f"{'='*55}\n")

    # ── Load games.json ───────────────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    games_path = project_root / "data" / "mlb" / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found.")
        print(f"  Expected: {games_path}")
        print(f"  Run fetch_odds.py first to create it.")
        sys.exit(1)

    with open(games_path) as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games from games.json\n")

    # ── Step 1: Fetch MLB schedule ────────────────────────────────────────────
    print("Step 1: Fetching MLB Stats API schedule with probable pitchers...")
    schedule = fetch_schedule(target_date)

    if not schedule:
        print("ERROR: Failed to fetch schedule. Check your internet connection.")
        sys.exit(1)

    # Extract games from the dates array
    mlb_games = []
    for date_block in schedule.get("dates", []):
        mlb_games.extend(date_block.get("games", []))

    print(f"  MLB API returned {len(mlb_games)} games\n")

    # ── Optional: print raw API structure ─────────────────────────────────────
    if show_api and mlb_games:
        print("--- RAW MLB STATS API RESPONSE (first game, teams section) ---")
        g = mlb_games[0]
        sample = {
            "gamePk":    g.get("gamePk"),
            "gameDate":  g.get("gameDate"),
            "teams": {
                "away": {
                    "team":             g["teams"]["away"]["team"],
                    "probablePitcher":  g["teams"]["away"].get("probablePitcher"),
                },
                "home": {
                    "team":             g["teams"]["home"]["team"],
                    "probablePitcher":  g["teams"]["home"].get("probablePitcher"),
                },
            },
        }
        print(json.dumps(sample, indent=2))
        print("--- END SCHEDULE RESPONSE ---\n")

    # ── Step 2: Collect unique pitcher IDs ───────────────────────────────────
    # Build a map: player_id → probablePitcher dict (for name/id lookup later)
    pitcher_id_to_pp = {}
    for game in mlb_games:
        for side in ("away", "home"):
            pp = game["teams"][side].get("probablePitcher")
            if pp and pp.get("id"):
                pitcher_id_to_pp[pp["id"]] = pp

    print(f"Step 2: Fetching season stats for {len(pitcher_id_to_pp)} pitchers...")
    if not pitcher_id_to_pp:
        print("  No probable pitchers announced yet. Context will be null.")

    # ── Step 3: Fetch player details + stats for each pitcher ─────────────────
    pitcher_id_to_data = {}
    for pid, pp in sorted(pitcher_id_to_pp.items(), key=lambda x: x[1].get("fullName", "")):
        player_data = fetch_player(pid, season)
        pitcher_id_to_data[pid] = player_data

        if show_api and player_data:
            print(f"\n--- RAW PLAYER RESPONSE: {pp.get('fullName')} ---")
            # Show just the relevant sections
            sample = {
                "id":        player_data.get("id"),
                "fullName":  player_data.get("fullName"),
                "pitchHand": player_data.get("pitchHand"),
                "stats":     player_data.get("stats", []),
            }
            print(json.dumps(sample, indent=2))
            print(f"--- END PLAYER RESPONSE ---")
            # Only show the first pitcher in --show-api mode to avoid flooding
            show_api = False

        stats = parse_player_stats(player_data)
        era_str = f"ERA {stats['era']}" if stats["era"] is not None else "no stats yet"
        hand_str = stats["hand"] or "?"
        print(f"  {pp.get('fullName', '?')} ({hand_str}): {era_str}")

    print()

    # ── Step 4: Build lookup by team names for matching ───────────────────────
    # Both TheOddsAPI and MLB Stats API use identical full team names.
    # Match on (away_name, home_name) pair — no fuzzy matching needed.
    mlb_by_teams = {}
    for game in mlb_games:
        away = game["teams"]["away"]["team"]["name"]
        home = game["teams"]["home"]["team"]["name"]
        mlb_by_teams[(away, home)] = game

    # ── Step 5: Match games and write context ─────────────────────────────────
    print("Step 3: Matching games and writing pitcher context...")
    updated  = 0
    no_match = []
    tbd      = []

    for game in games:
        away_name = game["away"]["name"]
        home_name = game["home"]["name"]
        key       = (away_name, home_name)
        matchup   = f"{game['away']['abbr']} @ {game['home']['abbr']}"

        mlb_game = mlb_by_teams.get(key)

        # Store the MLB gamePk — used by fetch_umpires.py to call the boxscore API
        if mlb_game:
            game["mlb_game_pk"] = mlb_game.get("gamePk")

        if not mlb_game:
            # Team name mismatch between TheOddsAPI and MLB Stats API
            # Log it so we can add a name-mapping fix if needed
            print(f"  WARNING: No MLB API match for {matchup}")
            print(f"    Looked for: away='{away_name}' home='{home_name}'")
            print(f"    Available:  {list(mlb_by_teams.keys())}")
            no_match.append(matchup)
            continue

        # Extract probable pitcher objects from schedule response
        away_pp = mlb_game["teams"]["away"].get("probablePitcher")
        home_pp = mlb_game["teams"]["home"].get("probablePitcher")

        # Build canonical pitcher entries from fresh API data
        away_pitcher = build_pitcher_entry(
            away_pp,
            pitcher_id_to_data.get(away_pp["id"]) if away_pp else None,
        )
        home_pitcher = build_pitcher_entry(
            home_pp,
            pitcher_id_to_data.get(home_pp["id"]) if home_pp else None,
        )

        # Track games where pitchers are TBD
        if not away_pp or not home_pp:
            tbd_side = "away" if not away_pp else "home"
            tbd.append(f"{matchup} ({tbd_side} TBD)")

        # ── Change detection & opener flagging ────────────────────────────────
        # Read whatever was already in games.json BEFORE this run so we can
        # compare names/IDs. This is the key that was missing previously.
        ctx = game.get("context") or {}
        hrs = hours_until_game(game.get("commence_utc"))
        fetch_ts = now_utc()

        for new_pitcher, old_key in (
            (away_pitcher, "pitcher_away"),
            (home_pitcher, "pitcher_home"),
        ):
            if new_pitcher is None:
                continue

            old_pitcher = ctx.get(old_key)
            old_name    = (old_pitcher or {}).get("name")
            old_id      = (old_pitcher or {}).get("mlb_id")
            new_name    = new_pitcher.get("name")
            new_id      = new_pitcher.get("mlb_id")

            # --- Starter change flag ---
            # Only fire if there WAS a previously stored name AND it differs from
            # what the API just returned. Avoids false positives on first run.
            if (
                old_name
                and old_name != "TBD"
                and new_name
                and old_id != new_id
            ):
                new_pitcher["starter_change_flag"] = {
                    "old_name":   old_name,
                    "old_id":     old_id,
                    "new_name":   new_name,
                    "detected_at": fetch_ts,
                }
                print(
                    f"  !! STARTER CHANGE detected in {matchup} ({old_key}): "
                    f"{old_name} -> {new_name}"
                )
            else:
                # Preserve a previously detected flag if we're just re-running
                # without a further change (don't wipe the flag on subsequent runs)
                prior_flag = (old_pitcher or {}).get("starter_change_flag")
                if prior_flag and prior_flag.get("new_name") == new_name:
                    new_pitcher["starter_change_flag"] = prior_flag

            # --- Opener / unconfirmed flag ---
            # If the game is within 3 hours AND the listed pitcher has < 5.0 IP
            # on the season, it is likely an opener or a stale/unconfirmed entry.
            try:
                ip_val = float(new_pitcher.get("innings_pitched") or 0)
            except (ValueError, TypeError):
                ip_val = 0.0

            if hrs is not None and 0 <= hrs <= 3 and ip_val < 5.0:
                new_pitcher["opener_flag"] = True
                print(
                    f"  !! OPENER/UNCONFIRMED flag set for {matchup} "
                    f"({old_key}): {new_name} {new_pitcher.get('innings_pitched')} IP, "
                    f"{hrs:.1f}h to game"
                )
            else:
                new_pitcher.pop("opener_flag", None)  # clear stale flag from prior run

        # Write into context block, preserving all other existing fields
        ctx["pitcher_away"]             = away_pitcher
        ctx["pitcher_home"]             = home_pitcher
        ctx["pitchers_source"]          = "mlb_official"
        ctx["pitchers_source_priority"] = 1
        ctx["pitchers_fetched_at"]      = fetch_ts
        game["context"] = ctx

        # Summary line for this game
        away_name_str = away_pp["fullName"] if away_pp else "TBD"
        home_name_str = home_pp["fullName"] if home_pp else "TBD"
        print(f"  {matchup}: {away_name_str} vs {home_name_str}")
        updated += 1

    # ── Step 6: Save updated games.json ──────────────────────────────────────
    with open(games_path, "w") as f:
        json.dump(games, f, indent=2)

    print(f"\nStep 4: Saved -> {games_path.relative_to(project_root)}")

    # ── Step 7: Print one completed game object ───────────────────────────────
    print(f"\n{'='*55}")
    print("COMPLETED GAME OBJECT — context block (DET @ TB)")
    print(f"{'='*55}")

    for game in games:
        if game["away"]["abbr"] == "DET":
            # Show identity + context only (odds block is large, unchanged)
            display = {
                "game_id":    game["game_id"],
                "sport":      game["sport"],
                "date_et":    game["date_et"],
                "away":       game["away"],
                "home":       game["home"],
                "commence_et": game["commence_et"],
                "context":    game.get("context"),
                "odds":       "(omitted — unchanged)",
                "result":     game.get("result"),
            }
            print(json.dumps(display, indent=2))
            break

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  DONE")
    print(f"  Games updated:  {updated}/{len(games)}")
    if tbd:
        print(f"  Pitchers TBD:   {len(tbd)}")
        for t in tbd:
            print(f"    {t}")
    if no_match:
        print(f"  Unmatched:      {len(no_match)} — check team name mapping")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch MLB probable pitchers and write into games.json context block."
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--show-api", action="store_true",
        help="Print raw API responses for the first game and first pitcher (for inspection)."
    )
    args = parser.parse_args()

    fetch_pitchers(date=args.date, show_api=args.show_api)

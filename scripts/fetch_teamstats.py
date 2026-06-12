#!/usr/bin/env python
"""
scripts/fetch_teamstats.py

Fetch team standings and form data from the MLB Stats API and write it
into the context block of each game in data/{sport}/{date}/games.json.

One API call fetches all 30 MLB teams at once — no per-team looping.
Data written includes: overall W-L record, run differential, runs scored/allowed
per game, last 10 games record, home record (for home teams), away record (for
away teams), and current win/loss streak.

Usage:
    python scripts/fetch_teamstats.py
    python scripts/fetch_teamstats.py --date 2026-06-02
    python scripts/fetch_teamstats.py --sport mlb --show-api

Reads:
    data/{sport}/{date}/games.json

Modifies:
    data/{sport}/{date}/games.json  -- writes context.team_away and context.team_home
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



# Official MLB Stats API — no key required, powers MLB.com
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"


# ─────────────────────────────────────────────────────────────────────────────
# SPORT CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
# Each sport that fetch_teamstats.py supports needs an entry here.
# When NBA or NHL seasons start, add their config and write a matching
# fetch_standings_{sport}() function — nothing else in this file changes.
#
# MLB uses the statsapi.mlb.com endpoint (AL leagueId=103, NL leagueId=104).
# NBA and NHL use completely different APIs — they will get their own functions.

SPORT_CONFIG = {
    "mlb": {
        "league_ids":  "103,104",        # AL (103) + NL (104) — both leagues in one call
        "season_type": "regularSeason",
    },
    # "nba": {...}   add when NBA season begins (uses stats.nba.com, different API)
    # "nhl": {...}   add when NHL season begins (uses api-web.nhle.com, different API)
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    """Return current time as UTC ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(url: str, params: dict = None) -> dict | None:
    """
    HTTP GET using stdlib urllib. Returns parsed JSON or None on error.
    The MLB Stats API requires no authentication and no API key.
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


def get_split(splits: list, split_type: str) -> dict:
    """
    Pull one split record from the splitRecords array by its type field.
    The API returns a list of dicts like: {"wins": 6, "losses": 4, "type": "lastTen", ...}
    We look up by type name and return the matching dict, or {} if not found.
    """
    for s in splits:
        if s.get("type") == split_type:
            return s
    return {}


def fetch_l10_rsg(team_id: int, season: int, before_date: str) -> float | None:
    """
    Fetch a team's average runs scored per game over their last 10 games
    played before before_date (YYYY-MM-DD). Uses the MLB Stats API game log
    endpoint — one call per team, so we only call this for teams in the slate.

    Returns RS/G rounded to 1 decimal, or None on error.
    """
    url = f"{MLB_API_BASE}/teams/{team_id}/stats"
    params = {"stats": "gameLog", "season": season, "group": "hitting"}
    data = api_get(url, params)
    if not data:
        return None

    # The API returns a stats array; first element contains the game-by-game splits
    splits = []
    for stat_block in data.get("stats", []):
        splits = stat_block.get("splits", [])
        if splits:
            break

    if not splits:
        return None

    # Filter to games that took place before before_date (API date format is YYYY-MM-DD)
    past_games = [s for s in splits if s.get("date", "") < before_date]
    last10     = past_games[-10:]   # last 10 chronologically

    if not last10:
        return None

    total_runs = sum(s.get("stat", {}).get("runs", 0) for s in last10)
    return round(total_runs / len(last10), 1)


# ─────────────────────────────────────────────────────────────────────────────
# PARSING — raw API data → canonical context fields
# ─────────────────────────────────────────────────────────────────────────────

def parse_team_record(tr: dict) -> dict:
    """
    Flatten one team's standings entry from the raw API response into the
    fields we actually need. The raw response is deeply nested and contains
    a lot of noise (wild card ranks, magic numbers, etc.) — we keep only what
    the prompt and future stat calculations will use.

    Fields returned:
      name, abbr, team_id     — identity for debugging and future joins
      wins, losses, pct       — overall season record
      run_differential        — season total (positive = more RS than RA)
      runs_scored, runs_allowed, games_played — raw totals for any calculations
      rs_per_game, ra_per_game — pre-computed rates (rounded to 1 decimal)
      last10_wins, last10_losses — form over the last 10 games
      home_wins, home_losses  — record at home (used for home team in prompt)
      away_wins, away_losses  — record on road (used for away team in prompt)
      streak                  — current run/loss streak code e.g. "W3", "L1"
      source, source_priority, fetched_at — provenance
    """
    gp     = tr.get("gamesPlayed") or 1   # use 1 as floor to avoid divide-by-zero on day 1
    splits = tr.get("records", {}).get("splitRecords", [])

    last10 = get_split(splits, "lastTen")
    home   = get_split(splits, "home")
    away   = get_split(splits, "away")
    streak = tr.get("streak", {})

    rs = tr.get("runsScored", 0)
    ra = tr.get("runsAllowed", 0)

    return {
        # ── Identity ──────────────────────────────────────────────
        "name":    tr["team"]["name"],          # e.g. "New York Yankees"
        "abbr":    tr["team"]["abbreviation"],  # e.g. "NYY"
        "team_id": tr["team"]["id"],            # MLB internal ID (e.g. 147)

        # ── Overall record ────────────────────────────────────────
        "wins":    tr.get("wins"),
        "losses":  tr.get("losses"),
        "pct":     tr.get("winningPercentage"),  # string, e.g. ".610"

        # ── Run scoring ───────────────────────────────────────────
        # Raw totals kept for future stat engine; per-game rates for the prompt.
        "run_differential": tr.get("runDifferential"),
        "runs_scored":      rs,
        "runs_allowed":     ra,
        "games_played":     tr.get("gamesPlayed"),
        "rs_per_game":      round(rs / gp, 1),
        "ra_per_game":      round(ra / gp, 1),

        # ── Split records ─────────────────────────────────────────
        # last10 is form — shows hot/cold streaks better than overall record.
        # home/away used contextually: show away record for away team, home for home.
        "last10_wins":   last10.get("wins"),
        "last10_losses": last10.get("losses"),
        "home_wins":     home.get("wins"),
        "home_losses":   home.get("losses"),
        "away_wins":     away.get("wins"),
        "away_losses":   away.get("losses"),

        # ── Streak ───────────────────────────────────────────────
        # "W3" = won last 3, "L1" = lost last 1. Shows current momentum.
        "streak": streak.get("streakCode"),

        # ── Provenance ────────────────────────────────────────────
        "source":          "mlb_official",
        "source_priority": 1,
        "fetched_at":      None,   # set by caller once the API call completes
    }


# ─────────────────────────────────────────────────────────────────────────────
# STANDINGS FETCH (MLB)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_standings_mlb(season: str, show_api: bool = False) -> dict:
    """
    Fetch all 30 MLB team standings in a single API call.

    Returns a dict keyed by full team name (e.g. "New York Yankees").
    Key confirmed to match TheOddsAPI team names exactly — no mapping needed.

    Endpoint:
      GET /api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason&hydrate=team,record

    The hydrate=team,record parameter pulls both team identity data and the full
    records block (which contains splitRecords with lastTen, home, away splits).
    """
    data = api_get(f"{MLB_API_BASE}/standings", {
        "leagueId":       "103,104",        # both leagues in one request
        "season":         season,
        "standingsTypes": "regularSeason",
        "hydrate":        "team,record",    # record hydration gives us splitRecords
    })

    if show_api and data and data.get("records"):
        print("\n--- RAW STANDINGS API RESPONSE (first team record) ---")
        print(json.dumps(data["records"][0]["teamRecords"][0], indent=2))
        print("--- END ---\n")

    if not data:
        return {}

    # Parse all 30 teams from all 6 divisions into a flat name->stats lookup
    lookup = {}
    for division in data["records"]:
        for tr in division["teamRecords"]:
            team_name = tr["team"]["name"]
            lookup[team_name] = parse_team_record(tr)

    return lookup


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_teamstats(sport: str = "mlb", date: str = None, show_api: bool = False):
    """
    Load games.json, fetch team standings for all teams on the slate,
    match by full team name, and write context.team_away / context.team_home
    into each game. All other context fields (pitchers, weather, umpire) are
    preserved — this function only touches the team_away/team_home fields.
    """
    target_date = date or today_et()
    season      = target_date[:4]   # "2026" — the year part of the date

    print(f"\n{'='*55}")
    print(f"  FETCH TEAM STATS  {sport.upper()}")
    print(f"  Slate date (US ET): {target_date}")
    print(f"  Season:             {season}")
    print(f"{'='*55}\n")

    # Guard: only MLB is supported right now. NBA/NHL need their own API calls.
    if sport not in SPORT_CONFIG:
        print(f"ERROR: fetch_teamstats.py does not yet support sport='{sport}'.")
        print(f"  Supported: {list(SPORT_CONFIG.keys())}")
        print(f"  To add a new sport: add it to SPORT_CONFIG and write a")
        print(f"  fetch_standings_{{sport}}() function following the same pattern.")
        sys.exit(1)

    # ── Load games.json ───────────────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    games_path   = project_root / "data" / sport / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found.")
        print(f"  Expected: {games_path}")
        print(f"  Run fetch_odds.py first to create it.")
        sys.exit(1)

    with open(games_path, encoding="utf-8") as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games\n")

    # ── Step 1: Fetch standings — one API call for all 30 teams ──────────────
    print("Step 1: Fetching MLB standings (all 30 teams, one API call)...")
    fetched_at = now_utc()   # timestamp before the call, used as fetch time for all records
    standings  = fetch_standings_mlb(season, show_api=show_api)

    if not standings:
        print("ERROR: Standings API returned no data. Check your internet connection.")
        sys.exit(1)

    # Stamp every record with the fetch time (was left as None in parse_team_record)
    for record in standings.values():
        record["fetched_at"] = fetched_at

    print(f"  Received {len(standings)} team records\n")

    # ── Step 2: Match each game's teams and write context ─────────────────────
    # Full team name is the join key — confirmed to match TheOddsAPI names exactly.
    print("Step 2: Matching teams and writing context...")
    updated  = 0
    no_match = []

    for game in games:
        away_name = game["away"]["name"]
        home_name = game["home"]["name"]
        matchup   = f"{game['away']['abbr']} @ {game['home']['abbr']}"

        away_stats = standings.get(away_name)
        home_stats = standings.get(home_name)

        # Warn on mismatch but continue — partial data is better than nothing
        if not away_stats:
            print(f"  WARNING: No standings match for away='{away_name}' in {matchup}")
            no_match.append(away_name)
        if not home_stats:
            print(f"  WARNING: No standings match for home='{home_name}' in {matchup}")
            no_match.append(home_name)

        # Write into context, preserving all other existing fields.
        # game.get("context") or {} handles both None and missing key safely.
        ctx = game.get("context") or {}
        ctx["team_away"]                 = away_stats
        ctx["team_home"]                 = home_stats
        ctx["teamstats_source"]          = "mlb_official"
        ctx["teamstats_source_priority"] = 1
        ctx["teamstats_fetched_at"]      = fetched_at
        game["context"] = ctx
        updated += 1

        # One-line summary for each game
        a   = away_stats or {}
        h   = home_stats or {}
        a10 = f"{a.get('last10_wins', '?')}-{a.get('last10_losses', '?')}"
        h10 = f"{h.get('last10_wins', '?')}-{h.get('last10_losses', '?')}"
        print(
            f"  {matchup}: "
            f"{a.get('wins', '?')}-{a.get('losses', '?')} (L10 {a10})  vs  "
            f"{h.get('wins', '?')}-{h.get('losses', '?')} (L10 {h10})"
        )

    # ── Step 2b: Fetch L10 RS/G for each team in the slate ───────────────────
    # One API call per team (max 30, typically 16-20 per slate day).
    # This gives the runs scored per game in their last 10 games — a much better
    # short-term offensive form signal than the full-season RS/G.
    print("Step 2b: Fetching L10 RS/G for each team in the slate...")
    seen_team_ids: set = set()

    for game in games:
        for side in ("away", "home"):
            ctx_key  = f"team_{side}"
            team_ctx = (game.get("context") or {}).get(ctx_key)
            if not team_ctx:
                continue
            tid = team_ctx.get("team_id")
            if not tid or tid in seen_team_ids:
                continue
            seen_team_ids.add(tid)

            l10_rsg = fetch_l10_rsg(int(tid), int(season), target_date)
            team_ctx["l10_rs_per_game"] = l10_rsg   # None if fetch failed
            abbr = team_ctx.get("abbr", tid)
            print(f"  {abbr}: L10 RS/G = {l10_rsg if l10_rsg is not None else 'n/a'}")

    # ── Step 3: Save ──────────────────────────────────────────────────────────
    with open(games_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)

    print(f"\nStep 3: Saved -> {games_path.relative_to(project_root)}\n")

    # ── Show context block for the first game as a sanity check ───────────────
    print(f"{'='*55}")
    print("SAMPLE CONTEXT — team_away / team_home (first game)")
    print(f"{'='*55}")
    if games:
        ctx = games[0].get("context", {})
        print(json.dumps({
            "team_away": ctx.get("team_away"),
            "team_home": ctx.get("team_home"),
        }, indent=2))

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  DONE")
    print(f"  Games updated:  {updated}/{len(games)}")
    if no_match:
        print(f"  WARNING — unmatched teams: {no_match}")
        print(f"  Check team name mapping between TheOddsAPI and MLB Stats API.")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch MLB team standings and form data into games.json context block."
    )
    parser.add_argument(
        "--sport", default="mlb",
        help=(
            "Sport code. Currently supported: mlb. "
            "NBA/NHL support to be added when those seasons begin. "
            "Default: mlb"
        )
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--show-api", action="store_true",
        help="Print the raw MLB Stats API response for the first team record (for inspection)."
    )
    args = parser.parse_args()
    fetch_teamstats(sport=args.sport, date=args.date, show_api=args.show_api)

#!/usr/bin/env python
"""
scripts/fetch_bullpen.py

Fetch bullpen usage data for the last 3 days for each team on today's slate.
Identifies the closer and flags relievers who are likely taxed/unavailable.

Source: MLB Stats API — free, no auth required, same source as fetch_umpires.py.
  Schedule  : GET /api/v1/schedule?sportId=1&teamId={id}&startDate={d}&endDate={d}&gameType=R
  Boxscore  : GET /api/v1/game/{gamePk}/boxscore

Why this approach:
  FanGraphs is blocked by Cloudflare. The MLB Stats API boxscore contains the
  full pitching log for each game — who threw, how many pitches, and whether
  they recorded a save. Pitchers who didn't appear are available by definition,
  so we only track who DID appear.

Taxed flags (written into games.json):
  "likely_unavailable" — threw 25+ pitches yesterday, OR appeared on both
                         yesterday AND the day before (back-to-back usage)
  "reduced"            — appeared yesterday with <25 pitches (probably fine
                         for one inning but manager may protect them)

Usage:
    python scripts/fetch_bullpen.py
    python scripts/fetch_bullpen.py --date 2026-06-04
    python scripts/fetch_bullpen.py --sport mlb --date 2026-06-04

Modifies:
    data/{sport}/{date}/games.json — writes context.bullpen_away and context.bullpen_home
    All other context fields (odds, pitchers, weather, umpire) are never touched.
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


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

# A reliever is flagged "likely_unavailable" if they threw this many or more
# pitches the day before — 25 pitches is roughly 1 full inning of hard work.
HEAVY_USAGE_THRESHOLD = 25


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(url: str, params: dict = None) -> dict | None:
    """
    HTTP GET using stdlib urllib. Returns parsed JSON or None on error.
    No authentication is required for the MLB Stats API.
    """
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  ERROR: HTTP {e.code} — {url}")
        return None
    except urllib.error.URLError as e:
        print(f"  ERROR: Connection failed — {e.reason}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — TEAM ID LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def get_team_ids_for_date(target_date: str) -> dict:
    """
    Fetch today's MLB schedule to get the official MLB team ID for each team.
    Returns a dict: {full_team_name: team_id}.

    We need team IDs to query each team's recent game history via a separate
    schedule call (which accepts teamId= as a filter). Team names in games.json
    come from TheOddsAPI and match the official MLB team names exactly, so
    no fuzzy matching is needed.
    """
    data = api_get(f"{MLB_API_BASE}/schedule", {
        "sportId": 1,       # 1 = MLB
        "date": target_date,
    })
    if not data:
        return {}

    team_ids = {}
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            for side in ("away", "home"):
                team = game["teams"][side]["team"]
                team_ids[team["name"]] = team["id"]

    return team_ids


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1b — SEASON CLOSER LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def get_season_closer(team_id: int, season: str) -> str | None:
    """
    Fetch the season saves leaders for a team from the MLB Stats API.
    Returns the full name of the pitcher with the most saves, or None.

    This is the authoritative closer lookup — it works even when the closer
    hasn't recorded a save in the last 3 games (blown saves, team losses,
    non-save situations). The boxscore save-event approach misses this case.

    API: GET /api/v1/stats/leaders?leaderCategories=saves&season=YEAR
                                   &teamId=ID&sportId=1&limit=1
    """
    data = api_get(f"{MLB_API_BASE}/stats/leaders", {
        "leaderCategories": "saves",
        "season":           season,
        "teamId":           team_id,
        "sportId":          1,
        "limit":            1,    # Only need the top saves pitcher
    })
    if not data:
        return None

    for cat in data.get("leagueLeaders", []):
        leaders = cat.get("leaders", [])
        if leaders:
            # leaders[0] has the most saves; only use them if saves > 0
            top = leaders[0]
            if int(top.get("value", 0)) > 0:
                return top.get("person", {}).get("fullName")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — RECENT COMPLETED GAME LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def get_recent_completed_games(team_id: int, start_date: str, end_date: str) -> list:
    """
    Fetch a team's schedule between start_date and end_date (inclusive).
    Returns a list of (official_date, game_pk, side) for completed games only.

    official_date : str "YYYY-MM-DD" — the date the game was played
    game_pk       : int — used to fetch the boxscore
    side          : "away" or "home" — which half of the boxscore to parse

    We filter to abstractGameState == "Final" so postponed games and any
    game that hasn't finished yet are excluded.
    """
    data = api_get(f"{MLB_API_BASE}/schedule", {
        "sportId":   1,
        "teamId":    team_id,
        "startDate": start_date,
        "endDate":   end_date,
        "gameType":  "R",    # R = Regular Season (excludes spring training, playoffs)
    })
    if not data:
        return []

    completed = []
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            # Skip games that haven't finished yet
            if game.get("status", {}).get("abstractGameState") != "Final":
                continue

            game_pk = game.get("gamePk")
            if not game_pk:
                continue

            # The official_date is on the date block, not the game itself
            official_date = date_block.get("date", "")

            # Determine which side (away/home) this team played so we know
            # which half of the boxscore to read in the next step
            away_id = game["teams"]["away"]["team"]["id"]
            side = "away" if away_id == team_id else "home"

            completed.append((official_date, game_pk, side))

    # Sort oldest-first so the last item in the list is the most recent game
    completed.sort(key=lambda x: x[0])
    return completed


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — BOXSCORE PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_relievers_from_boxscore(game_pk: int, side: str) -> list:
    """
    Fetch the boxscore for a completed game and return a list of reliever
    appearances for the given side ("away" or "home").

    The boxscore "pitchers" array is ordered by appearance in the game.
    Index 0 is the starting pitcher — we skip him because starters don't
    appear on consecutive days and are never the target of bullpen fatigue.
    Indices 1+ are relievers.

    Each returned entry is a dict:
    {
        "player_id": int,
        "name":      str,
        "pitches":   int,   -- total pitches thrown in this game
        "innings":   str,   -- "2.0", "1.1", etc. (MLB notation: .1 = 1 out, .2 = 2 outs)
        "saves":     int,   -- 1 if this pitcher earned a save in this game, else 0
    }

    We use "saves" to identify the team's closer — the pitcher who records
    saves most frequently over the last 3 games is their closer.
    """
    data = api_get(f"{MLB_API_BASE}/game/{game_pk}/boxscore")
    if not data:
        return []

    team_data  = data.get("teams", {}).get(side, {})
    pitcher_ids = team_data.get("pitchers", [])   # list of int player IDs, in order
    players     = team_data.get("players", {})    # keyed by "ID{player_id}"

    if not pitcher_ids:
        return []

    relievers = []

    for i, pid in enumerate(pitcher_ids):
        # Skip index 0 — that's the starting pitcher
        if i == 0:
            continue

        # Look up this player in the players dict (keyed as "ID123456")
        player_key = f"ID{pid}"
        player = players.get(player_key, {})
        if not player:
            continue

        name     = player.get("person", {}).get("fullName", f"Player {pid}")
        pitching = player.get("stats", {}).get("pitching", {})

        # numberOfPitches is an int; default to 0 if absent (shouldn't happen for active pitchers)
        pitches = pitching.get("numberOfPitches", 0) or 0

        # inningsPitched is a string like "2.0" (MLB's notation for fractions)
        innings = pitching.get("inningsPitched", "0.0") or "0.0"

        # saves: 1 if this pitcher recorded a save in this specific game, else 0
        saves = pitching.get("saves", 0) or 0

        relievers.append({
            "player_id": pid,
            "name":      name,
            "pitches":   pitches,
            "innings":   innings,
            "saves":     saves,
        })

    return relievers


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — BULLPEN SUMMARY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_bullpen_summary(
    appearances_by_date: dict,
    target_date:         str,
    team_abbr:           str,
    team_bullpen_era:    float | None,
    season_closer_name:  str | None = None,
) -> dict:
    """
    Given reliever appearances across the last few days, build the bullpen
    context dict that gets written into games.json.

    appearances_by_date: {date_str: [reliever_dict, ...]}
        e.g. {"2026-06-03": [{...}, {...}], "2026-06-02": [{...}]}

    target_date: the slate date (e.g. "2026-06-04") — NOT a game date.
        "Yesterday" means the day before the slate.

    team_abbr: used for display/debug only (e.g. "CHW").

    team_bullpen_era: pulled from context.team_away/home if fetch_teamstats
        has already run. None if not available — shown as null in JSON.

    Returns the bullpen context dict to be written under context.bullpen_away
    or context.bullpen_home.
    """
    # Define the key dates relative to the slate
    tgt            = datetime.strptime(target_date, "%Y-%m-%d")
    yesterday      = (tgt - timedelta(days=1)).strftime("%Y-%m-%d")
    two_days_ago   = (tgt - timedelta(days=2)).strftime("%Y-%m-%d")
    three_days_ago = (tgt - timedelta(days=3)).strftime("%Y-%m-%d")
    four_days_ago  = (tgt - timedelta(days=4)).strftime("%Y-%m-%d")

    # ── Aggregate per-pitcher data across all recent games ────────────────────
    # pitchers dict: player_id -> {name, by_date: {date: pitches}, saves_total}
    pitchers = {}

    for date, relievers in appearances_by_date.items():
        for r in relievers:
            pid = r["player_id"]
            if pid not in pitchers:
                pitchers[pid] = {
                    "name":        r["name"],
                    "by_date":     {},
                    "saves_total": 0,
                }
            # Record how many pitches this pitcher threw on each date
            pitchers[pid]["by_date"][date]  = r["pitches"]
            pitchers[pid]["saves_total"]   += r["saves"]

    # ── Identify the closer ───────────────────────────────────────────────────
    # Two-step approach:
    # 1. Use the season saves leader (authoritative — works even when the closer
    #    hasn't pitched in a save situation in the last 3 games).
    # 2. Fall back to whoever recorded a save in recent boxscores if the season
    #    stat lookup failed or returned nothing.
    closer_name = season_closer_name   # set by the caller from get_season_closer()

    if not closer_name:
        # Fallback: scan recent boxscores for any save event
        max_saves = 0
        for pid, info in pitchers.items():
            if info["saves_total"] > max_saves:
                max_saves   = info["saves_total"]
                closer_name = info["name"]

    # ── Build the taxed relievers list ────────────────────────────────────────
    # Only include pitchers who are ACTUALLY taxed — absence from this list
    # means "available" by definition (they didn't pitch recently).
    taxed = []

    for pid, info in pitchers.items():
        pitches_yesterday    = info["by_date"].get(yesterday)    # None if didn't pitch
        pitches_two_days_ago = info["by_date"].get(two_days_ago) # None if didn't pitch

        pitched_yesterday    = pitches_yesterday    is not None
        pitched_two_days_ago = pitches_two_days_ago is not None

        # Consecutive = appeared both yesterday AND the day before
        consecutive_days = pitched_yesterday and pitched_two_days_ago

        # Heavy usage = 25+ pitches yesterday (manager may skip them tonight)
        heavy_yesterday = pitched_yesterday and (pitches_yesterday or 0) >= HEAVY_USAGE_THRESHOLD

        # 3-in-4 = appeared on 3 or more of the last 4 days (cumulative overload,
        # even if not strictly back-to-back ending yesterday).
        days_pitched_last4 = sum(
            1 for d in (yesterday, two_days_ago, three_days_ago, four_days_ago)
            if info["by_date"].get(d) is not None
        )
        three_in_four = days_pitched_last4 >= 3

        # Only include pitchers who are taxed in some way.
        # "Not taxed" means: didn't pitch yesterday, no back-to-back ending
        # yesterday, and not 3-in-4 overloaded.
        if not pitched_yesterday and not consecutive_days and not three_in_four:
            continue

        # Determine severity of the flag
        if heavy_yesterday or consecutive_days or three_in_four:
            flag = "likely_unavailable"
        else:
            # Pitched yesterday but lightly (< 25 pitches), not consecutive
            flag = "reduced"

        taxed.append({
            "name":                      info["name"],
            "pitches_yesterday":         pitches_yesterday,
            "pitches_two_days_ago":      pitches_two_days_ago,
            "appeared_consecutive_days": consecutive_days,
            "days_pitched_last4":        days_pitched_last4,
            "three_in_four":             three_in_four,
            "flag":                      flag,
        })

    # Sort: worst-flagged first, then by highest pitch count yesterday
    taxed.sort(key=lambda x: (
        0 if x["flag"] == "likely_unavailable" else 1,
        -(x["pitches_yesterday"] or 0),
    ))

    # ── Closer availability ───────────────────────────────────────────────────
    # The closer is unavailable if they appear in the taxed list with
    # "likely_unavailable" flag (heavy usage or consecutive days).
    # "reduced" = closer will probably pitch but manager might protect them.
    closer_taxed = any(
        t["name"] == closer_name and t["flag"] == "likely_unavailable"
        for t in taxed
    ) if closer_name else False

    return {
        "team_bullpen_era": team_bullpen_era,
        "closer": {
            "name":      closer_name,     # None if no save situations in last 3 games
            "available": not closer_taxed,
        },
        "taxed_relievers": taxed,
        "source":          "mlb_stats_api",
        "fetched_at":      now_utc(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_bullpen(date: str = None, sport: str = "mlb"):
    """
    Main entry point: fetch bullpen data for all teams on today's slate
    and write it into each game's context block in games.json.
    """
    target_date = date or today_et()

    # Look back 4 days before the slate date to check recent usage.
    # 4 days (not 3) so we can detect a "3-in-4" overload pattern.
    # e.g. slate=2026-06-05 → look at games on 2026-06-01 through 2026-06-04
    tgt        = datetime.strptime(target_date, "%Y-%m-%d")
    start_date = (tgt - timedelta(days=4)).strftime("%Y-%m-%d")
    end_date   = (tgt - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\n{'='*55}")
    print(f"  FETCH BULLPEN — {sport.upper()}")
    print(f"  Slate date:   {target_date}")
    print(f"  Lookback:     {start_date}  to  {end_date}")
    print(f"  Heavy thresh: {HEAVY_USAGE_THRESHOLD}+ pitches = likely unavailable")
    print(f"{'='*55}\n")

    # ── Load games.json ───────────────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    games_path   = project_root / "data" / sport / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        print("  Run fetch_odds.py first to create it.")
        sys.exit(1)

    with open(games_path, encoding="utf-8") as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games\n")

    # ── Step 1: Get MLB team IDs from today's schedule ────────────────────────
    # The schedule API returns a team ID for each team playing today.
    # We need this ID to query each team's recent game history.
    print("Step 1: Fetching team IDs from MLB schedule API...")
    team_ids = get_team_ids_for_date(target_date)

    if not team_ids:
        print("  ERROR: Could not fetch team IDs — check internet connection")
        sys.exit(1)

    print(f"  Found {len(team_ids)} team IDs\n")

    # ── Step 2: Fetch recent game history for each team ───────────────────────
    # We process each unique team once and cache the result.
    # A team only appears once per day's slate (you can't play two games
    # in the same day under normal circumstances), but the cache prevents
    # re-fetching if the same team somehow appears in multiple games.
    print("Step 2: Fetching recent boxscores for each team...")

    bullpen_cache = {}   # team_name -> bullpen context dict (or None on error)

    for game in games:
        for side in ("away", "home"):
            team_name = game[side]["name"]
            team_abbr = game[side]["abbr"]

            # Skip if we've already fetched this team
            if team_name in bullpen_cache:
                continue

            team_id = team_ids.get(team_name)
            if not team_id:
                print(f"  WARNING: No MLB team ID found for '{team_name}' — skipping")
                bullpen_cache[team_name] = None
                continue

            print(f"\n  -- {team_abbr} (id={team_id}) --")

            # Look up who leads this team in saves for the season — this is the
            # authoritative closer even if they haven't saved a game in 3 days
            season = target_date[:4]
            season_closer = get_season_closer(team_id, season)
            if season_closer:
                print(f"     Season saves leader: {season_closer}")
            else:
                print(f"     Season saves leader: none found")

            # Fetch the list of completed regular-season games in our lookback window
            recent_games = get_recent_completed_games(team_id, start_date, end_date)
            print(f"     Completed games in lookback: {len(recent_games)}")

            if not recent_games:
                print(f"     No games found — team may have had off-days")
                # Still record the season closer even with no recent game data
                bullpen_cache[team_name] = {
                    "team_bullpen_era": None,
                    "closer":          {"name": season_closer, "available": True},
                    "taxed_relievers": [],
                    "source":          "mlb_stats_api",
                    "fetched_at":      now_utc(),
                    "note":            "No completed games in lookback window",
                }
                continue

            # We only care about the 3 most recent games (oldest taxing data is 3 days old)
            recent_games = recent_games[-3:]

            # ── Fetch boxscore for each recent game ───────────────────────────
            appearances_by_date = {}   # {date_str: [reliever_dict, ...]}

            for game_date, game_pk, team_side in recent_games:
                print(f"     Boxscore: {game_date}  gamePk={game_pk}  ({team_side})")
                relievers = parse_relievers_from_boxscore(game_pk, team_side)

                if relievers:
                    appearances_by_date[game_date] = relievers
                    # Print a compact summary of who pitched
                    for r in relievers:
                        print(f"       {r['name']}: {r['pitches']}p  {r['innings']}ip"
                              + ("  SAVE" if r["saves"] else ""))
                else:
                    appearances_by_date[game_date] = []
                    print(f"       (no reliever data returned)")

            # ── Pull bullpen ERA from team stats context if available ──────────
            # fetch_teamstats.py stores team stats under context.team_away /
            # context.team_home. The field may not be present on early runs.
            ctx = game.get("context") or {}
            team_ctx_key = f"team_{side}"          # "team_away" or "team_home"
            team_stats   = ctx.get(team_ctx_key) or {}
            bullpen_era  = team_stats.get("bullpen_era")   # None if not stored

            # ── Build the bullpen summary for this team ───────────────────────
            summary = build_bullpen_summary(
                appearances_by_date=appearances_by_date,
                target_date=target_date,
                team_abbr=team_abbr,
                team_bullpen_era=bullpen_era,
                season_closer_name=season_closer,
            )
            bullpen_cache[team_name] = summary

            # Print a quick one-line digest
            closer_name = summary["closer"]["name"] or "unknown"
            closer_avail = "available" if summary["closer"]["available"] else "TAXED"
            n_taxed = len(summary["taxed_relievers"])
            print(f"     Closer: {closer_name} ({closer_avail})"
                  f" | Taxed: {n_taxed}")

    # ── Step 3: Write bullpen data into games.json ────────────────────────────
    print(f"\n\nStep 3: Writing bullpen context to games.json...")

    for game in games:
        matchup = f"{game['away']['abbr']} @ {game['home']['abbr']}"

        # Preserve all existing context fields — only touch bullpen keys
        ctx = game.get("context") or {}
        ctx["bullpen_away"] = bullpen_cache.get(game["away"]["name"])
        ctx["bullpen_home"] = bullpen_cache.get(game["home"]["name"])
        game["context"] = ctx

        away_n = len((ctx["bullpen_away"] or {}).get("taxed_relievers", []))
        home_n = len((ctx["bullpen_home"] or {}).get("taxed_relievers", []))
        print(f"  {matchup}: {away_n} away taxed / {home_n} home taxed")

    # ── Save ──────────────────────────────────────────────────────────────────
    with open(games_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)

    print(f"\nStep 4: Saved -> {games_path.relative_to(project_root)}")

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  BULLPEN SUMMARY — {target_date}")
    print(f"{'='*55}")

    for game in games:
        matchup = f"{game['away']['abbr']} @ {game['home']['abbr']}"
        print(f"\n  {matchup}")

        for side_key, abbr in [
            ("bullpen_away", game["away"]["abbr"]),
            ("bullpen_home", game["home"]["abbr"]),
        ]:
            b = (game.get("context") or {}).get(side_key) or {}

            closer      = b.get("closer", {})
            closer_name = closer.get("name") or "unknown"
            avail_str   = "available" if closer.get("available", True) else "TAXED"
            era         = b.get("team_bullpen_era")
            era_str     = f"ERA {era:.2f}" if era is not None else "ERA N/A"
            taxed       = b.get("taxed_relievers", [])

            print(f"    {abbr}: {era_str} | Closer: {closer_name} ({avail_str})")

            if taxed:
                for t in taxed:
                    p_yday = t.get("pitches_yesterday")
                    p_2day = t.get("pitches_two_days_ago")
                    consec = t.get("appeared_consecutive_days", False)
                    t3in4  = t.get("three_in_four", False)
                    d4     = t.get("days_pitched_last4")
                    flag   = t.get("flag", "")

                    # Build a readable detail string for the summary line
                    details = []
                    if p_yday is not None:  details.append(f"{p_yday}p yesterday")
                    if p_2day is not None:  details.append(f"{p_2day}p 2 days ago")
                    if consec:              details.append("consecutive")
                    if t3in4:               details.append(f"3-in-4 ({d4}/4 days)")

                    detail_str = ", ".join(details)
                    flag_icon  = "!!" if flag == "likely_unavailable" else " ~"
                    print(f"    {flag_icon} {t['name']} [{flag}] — {detail_str}")
            else:
                print(f"       No heavy usage in last 2 days")

    print(f"\n{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Fetch MLB bullpen usage for the last 3 days and write into games.json. "
            "Flags relievers who are likely unavailable due to heavy usage or "
            "consecutive-day appearances."
        )
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time.",
    )
    parser.add_argument(
        "--sport", default="mlb",
        help="Sport code (default: mlb). Only mlb is supported currently.",
    )
    args = parser.parse_args()

    fetch_bullpen(date=args.date, sport=args.sport)

#!/usr/bin/env python
"""
scripts/fetch_pitcher_advanced.py

Fetch advanced pitcher statistics from Baseball Savant via pybaseball
and write them into the pitcher context blocks in games.json.

Requires: pip install pybaseball

DATA SOURCES
  Baseball Savant (via pybaseball) — two API calls cover all pitchers:
    statcast_pitcher_expected_stats(year)      -> xERA
    statcast_pitcher_exitvelo_barrels(year)    -> Hard Hit % (EV95+%), Barrel %
  Computed from existing games.json fields:
    K/9 = 9 x strikeouts / innings_pitched

NOTE ON FANGRAPHS
  FanGraphs endpoints (FIP, xFIP, K%, BB%, BABIP) return HTTP 403 as of
  June 2026. This is a known pybaseball issue — FanGraphs changed their API.
  If access is restored, add a fetch_fangraphs() block here and include
  those fields. See docs/LEARNINGS.md for context.

MATCHING
  Pitchers are joined by MLBAM player ID (mlb_id in our games.json = player_id
  in Savant tables). No fuzzy name matching — the ID is exact.

SMALL SAMPLE FLAG
  Any pitcher with fewer than 40 innings pitched gets small_sample: true.
  The prompt builder uses this to add a caution note.

Usage:
    python scripts/fetch_pitcher_advanced.py --date 2026-06-03
    python scripts/fetch_pitcher_advanced.py --sport mlb --date 2026-06-03

Modifies:
    data/{sport}/{date}/games.json  -- adds advanced fields to pitcher_away/home
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import warnings
from datetime import datetime, timezone
from pathlib import Path
from tz_util import ET


warnings.filterwarnings("ignore")   # suppress pybaseball progress bar noise

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

# FIP constant normalises FIP to the ERA scale for the current season.
# Updated annually: league ERA minus the league's FIP components normalised.
# 3.10 is the standard value for 2026.
FIP_CONSTANT = 3.10


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ip_to_decimal(ip_str) -> float | None:
    """
    Convert MLB innings-pitched string to a decimal number.
    The MLB convention: "69.2" means 69 and 2/3 innings (not 69.2 innings).
    The digit after the decimal is the number of outs (0, 1, or 2) = thirds.

    Examples:  "69.2" -> 69.667   "61.0" -> 61.0   "12.2" -> 12.667
    """
    if ip_str is None:
        return None
    try:
        s = str(ip_str)
        if "." in s:
            full, thirds = s.split(".", 1)
            return int(full) + int(thirds) / 3.0
        return float(s)
    except (ValueError, TypeError):
        return None


def compute_k_per_9(strikeouts, innings_pitched_str) -> float | None:
    """
    K/9 = 9 × strikeouts ÷ innings_pitched_decimal.
    Returns None if either input is missing or innings = 0.
    """
    if strikeouts is None:
        return None
    ip = ip_to_decimal(innings_pitched_str)
    if ip is None or ip <= 0:
        return None
    return round(9 * int(strikeouts) / ip, 1)


def is_small_sample(innings_pitched_str, threshold: float = 30.0) -> bool:
    """Return True if pitcher has fewer than threshold innings pitched."""
    ip = ip_to_decimal(innings_pitched_str)
    return ip is not None and ip < threshold


def compute_fip(pitcher: dict) -> float | None:
    """
    Compute FIP from the pitcher's season stat fields already in games.json.
    No API call — pure arithmetic from data fetched by fetch_pitchers.py.

    Formula:  FIP = ((13 × HR) + (3 × (BB + HBP)) - (2 × K)) / IP + FIP_CONSTANT

    Returns FIP rounded to 2 decimal places, or None when:
      - IP is 0 or missing (can't divide by zero)
      - Any of HR, BB, K is missing (HBP defaults to 0 if absent — it is
        recorded inconsistently early in the season)
    """
    if not pitcher:
        return None

    hr  = pitcher.get("home_runs")
    bb  = pitcher.get("walks")
    hbp = pitcher.get("hit_batters") or 0   # default 0 — missing early season is common
    k   = pitcher.get("strikeouts")
    ip  = ip_to_decimal(pitcher.get("innings_pitched"))

    # Require HR, BB, K, and a positive IP; HBP is allowed to default to 0
    if any(v is None for v in (hr, bb, k)) or not ip or ip <= 0:
        return None

    fip = ((13 * int(hr)) + (3 * (int(bb) + int(hbp))) - (2 * int(k))) / ip + FIP_CONSTANT
    return round(fip, 2)


def api_get(url: str, params: dict = None) -> dict | None:
    """HTTP GET using stdlib urllib. Returns parsed JSON or None on error."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} — {url}")
        return None
    except urllib.error.URLError as e:
        print(f"  Connection failed — {e.reason}")
        return None


def fetch_recent_starts(person_id: int, season: int, n: int = 3) -> dict | None:
    """
    Fetch the last N regular-season starts for a pitcher from the MLB Stats API.

    Endpoint: GET /api/v1/people/{personId}/stats
              ?stats=gameLog&group=pitching&season=YEAR&gameType=R

    Filters to starts only (gamesStarted == 1). Returns the last N in
    chronological order (most recent last). Handles < N starts gracefully
    — returns however many exist, minimum 1.

    Returns:
        {
            "starts": [
                {"date": "Jun 1", "opponent": "HOU", "ip": "6.0", "er": 1},
                ...
            ],
            "rolling_era": 2.45
        }
        or None if the pitcher has no starts yet this season.
    """
    data = api_get(f"{MLB_API_BASE}/people/{person_id}/stats", {
        "stats":    "gameLog",
        "group":    "pitching",
        "season":   str(season),
        "gameType": "R",
    })
    if not data:
        return None

    # Extract splits — gameLog puts all game entries under the first stats element
    splits = []
    for stat_group in data.get("stats", []):
        candidate = stat_group.get("splits", [])
        if candidate:
            splits = candidate
            break

    if not splits:
        return None

    # Filter to starts only
    starts_only = [
        s for s in splits
        if s.get("stat", {}).get("gamesStarted") == 1
    ]

    if not starts_only:
        return None

    # Take last N (splits are chronological — most recent is last)
    recent = starts_only[-n:]

    result = []
    total_er      = 0
    total_ip_dec  = 0.0

    for s in recent:
        stat     = s.get("stat", {})
        date_str = s.get("date", "")
        try:
            dt       = datetime.strptime(date_str, "%Y-%m-%d")
            date_fmt = f"{dt.strftime('%b')} {dt.day}"   # "Jun 1"
        except ValueError:
            date_fmt = date_str

        opp    = s.get("opponent", {}).get("abbreviation", "???")
        ip_str = stat.get("inningsPitched") or "0.0"
        er     = int(stat.get("earnedRuns") or 0)
        ip_dec = ip_to_decimal(str(ip_str)) or 0.0
        k      = stat.get("strikeOuts")
        bb     = stat.get("baseOnBalls")

        total_er     += er
        total_ip_dec += ip_dec

        entry = {
            "date":     date_fmt,
            "opponent": opp,
            "ip":       str(ip_str),
            "er":       er,
        }
        # Only add K/BB when the API actually returns them (not None)
        if k is not None:
            entry["k"] = int(k)
        if bb is not None:
            entry["bb"] = int(bb)
        result.append(entry)

    rolling_era = round(total_er / total_ip_dec * 9, 2) if total_ip_dec > 0 else None

    return {
        "starts":      result,
        "rolling_era": rolling_era,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SAVANT DATA FETCH
# ─────────────────────────────────────────────────────────────────────────────

def fetch_savant_tables(season: int) -> tuple[dict, dict]:
    """
    Fetch both Savant tables and return two lookup dicts keyed by MLBAM player_id.

    Two API calls cover the entire league — no per-pitcher looping needed.

    Returns:
        expected_stats:  {player_id: {"xera": float | None}}
        exitvelo_stats:  {player_id: {"hard_hit_pct": float | None,
                                      "barrel_pct":   float | None}}
    """
    try:
        from pybaseball import (
            statcast_pitcher_expected_stats,
            statcast_pitcher_exitvelo_barrels,
        )
    except ImportError:
        print("ERROR: pybaseball is not installed.")
        print("  Run: pip install pybaseball")
        sys.exit(1)

    # ── Expected stats (xERA) ─────────────────────────────────────────────────
    print("  Calling statcast_pitcher_expected_stats...")
    df_exp = statcast_pitcher_expected_stats(season)

    expected_stats = {}
    for _, row in df_exp.iterrows():
        pid   = int(row["player_id"])
        xera  = row.get("xera")
        whiff = row.get("whiff_percent")   # % of swings that miss — column confirmed in Savant expected stats
        expected_stats[pid] = {
            "xera":          round(float(xera),  2) if xera  is not None else None,
            "whiff_percent": round(float(whiff), 1) if whiff is not None else None,
        }

    # ── Exit velo / barrels (Hard Hit %, Barrel %) ────────────────────────────
    # minBBE=10 excludes pitchers with barely any batted-ball events — the
    # percentages are meaningless on 3 batted balls.
    print("  Calling statcast_pitcher_exitvelo_barrels...")
    df_ev = statcast_pitcher_exitvelo_barrels(season, minBBE=10)

    exitvelo_stats = {}
    for _, row in df_ev.iterrows():
        pid = int(row["player_id"])
        hh  = row.get("ev95percent")   # % of balls hit at 95+ mph (Hard Hit %)
        brl = row.get("brl_percent")   # % of plate appearances ending in a barrel
        exitvelo_stats[pid] = {
            "hard_hit_pct": round(float(hh),  1) if hh  is not None else None,
            "barrel_pct":   round(float(brl), 1) if brl is not None else None,
        }

    print(f"  Expected stats: {len(expected_stats)} pitchers")
    print(f"  Exit velo stats: {len(exitvelo_stats)} pitchers")

    return expected_stats, exitvelo_stats


# ─────────────────────────────────────────────────────────────────────────────
# TEAM OFFENSIVE BARREL %
# ─────────────────────────────────────────────────────────────────────────────

# Baseball Savant uses "ARI" for Arizona; all other codes already match games.json.
_SAVANT_BATTER_TEAM_TO_GAMES: dict[str, str] = {"ARI": "AZ"}


# FanGraphs blocked by Cloudflare Turnstile -- pybaseball returns 403.
# Team barrel% is loaded from static file in load_static_data.py instead.
# This function is kept as a stub for reference only.
def fetch_team_barrel_pct(season: int) -> dict:
    """
    Stub -- FanGraphs API blocked (403). Team barrel% is now loaded from
    data/static/team_barrels.txt via load_static_data.load_team_barrels().
    Returns {} so callers that checked this return value continue unchanged.
    """
    print("INFO: team barrel% loading from static file via load_static_data.py")
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# PITCHER ENRICHMENT
# ─────────────────────────────────────────────────────────────────────────────

def enrich_pitcher(
    pitcher: dict,
    expected_stats: dict,
    exitvelo_stats: dict,
    fetched_at: str,
) -> dict:
    """
    Add advanced stats in-place to one pitcher context dict.

    Sources:
      K/9           — computed from strikeouts + innings_pitched (already in dict)
      xERA          — joined from expected_stats by mlb_id
      hard_hit_pct  — joined from exitvelo_stats by mlb_id
      barrel_pct    — joined from exitvelo_stats by mlb_id
      small_sample  — True when innings_pitched < 40

    Returns the modified dict (also mutated in place).
    """
    if not pitcher or not pitcher.get("name"):
        return pitcher

    # Computed stats from existing fields — no API calls needed
    pitcher["k_per_9"] = compute_k_per_9(
        pitcher.get("strikeouts"),
        pitcher.get("innings_pitched"),
    )
    pitcher["fip"] = compute_fip(pitcher)

    # Savant fields — require a valid MLBAM ID
    mlb_id = pitcher.get("mlb_id")
    if mlb_id:
        pid = int(mlb_id)
        exp = expected_stats.get(pid, {})
        ev  = exitvelo_stats.get(pid, {})
    else:
        exp = {}
        ev  = {}

    pitcher["xera"]         = exp.get("xera")
    pitcher["whiff_rate"]   = exp.get("whiff_percent")   # % of swings that miss (e.g. 28.4)
    pitcher["hard_hit_pct"] = ev.get("hard_hit_pct")
    pitcher["barrel_pct"]   = ev.get("barrel_pct")

    # Small sample flag — ERA / xERA become noisy below 40 IP
    pitcher["small_sample"]         = is_small_sample(pitcher.get("innings_pitched"))
    pitcher["advanced_source"]      = "baseball_savant"
    pitcher["advanced_fetched_at"]  = fetched_at

    return pitcher


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_pitcher_advanced(sport: str = "mlb", date: str = None):
    target_date = date or today_et()
    season      = int(target_date[:4])

    print(f"\n{'='*55}")
    print(f"  FETCH PITCHER ADVANCED  {sport.upper()}")
    print(f"  Date:    {target_date}")
    print(f"  Season:  {season}")
    print(f"  Source:  Baseball Savant (via pybaseball)")
    print(f"{'='*55}\n")

    project_root = Path(__file__).parent.parent
    games_path   = project_root / "data" / sport / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: {games_path} not found.")
        print("  Run fetch_odds.py + fetch_pitchers.py first.")
        sys.exit(1)

    with open(games_path, encoding="utf-8") as f:
        games = json.load(f)

    # Count how many pitchers have MLBAM IDs (set by fetch_pitchers.py)
    pitchers_total  = 0
    pitchers_with_id = 0
    for g in games:
        ctx = g.get("context") or {}
        for key in ("pitcher_away", "pitcher_home"):
            p = ctx.get(key)
            if p and p.get("name"):
                pitchers_total += 1
                if p.get("mlb_id"):
                    pitchers_with_id += 1

    print(f"Loaded {len(games)} games  |  "
          f"{pitchers_total} pitchers  |  {pitchers_with_id} have MLBAM ID\n")

    if pitchers_with_id == 0:
        print("WARNING: No pitchers have mlb_id — run fetch_pitchers.py first.")

    # ── Fetch Savant tables ───────────────────────────────────────────────────
    print("Step 1: Fetching Baseball Savant data...")
    fetched_at = now_utc()
    expected_stats, exitvelo_stats = fetch_savant_tables(season)

    # ── Team offensive barrel% ────────────────────────────────────────────────
    print("\nStep 1b: Fetching team offensive barrel%...")
    team_barrel_pct = fetch_team_barrel_pct(season)

    # ── Enrich pitchers ───────────────────────────────────────────────────────
    print("\nStep 2: Enriching pitcher contexts...\n")
    print(f"  {'Matchup':<12}  {'Side':<4}  {'Name':<22}  "
          f"{'xERA':>5}  {'HH%':>5}  {'Brl%':>5}  {'K/9':>4}  {'IP':>5}  {'Sm?'}")
    print(f"  {'-'*12}  {'-'*4}  {'-'*22}  "
          f"{'-'*5}  {'-'*5}  {'-'*5}  {'-'*4}  {'-'*5}  {'-'*3}")

    matched = 0
    for game in games:
        ctx     = game.get("context") or {}
        matchup = f"{game['away']['abbr']} @ {game['home']['abbr']}"

        for side_key, side_label in [("pitcher_away", "Away"), ("pitcher_home", "Home")]:
            pitcher = ctx.get(side_key)
            if not pitcher or not pitcher.get("name"):
                continue

            mlb_id = pitcher.get("mlb_id")
            had_id = mlb_id and int(mlb_id) in expected_stats

            enrich_pitcher(pitcher, expected_stats, exitvelo_stats, fetched_at)
            if had_id:
                matched += 1

            # Fetch last-3-starts rolling form from MLB Stats API game log
            if mlb_id:
                recent = fetch_recent_starts(int(mlb_id), season)
                pitcher["recent_starts"] = recent   # None if no starts yet
            else:
                pitcher["recent_starts"] = None

            # Summary row (dash for None values)
            def fmt(v, fmt_str="{:.2f}"):
                return fmt_str.format(v) if v is not None else "—"

            sm  = "Y" if pitcher.get("small_sample") else ""
            ip  = pitcher.get("innings_pitched") or "—"
            print(f"  {matchup:<12}  {side_label:<4}  {pitcher['name']:<22}  "
                  f"{fmt(pitcher.get('xera')):>5}  "
                  f"{fmt(pitcher.get('hard_hit_pct'), '{:.1f}'):>5}  "
                  f"{fmt(pitcher.get('barrel_pct'), '{:.1f}'):>5}  "
                  f"{fmt(pitcher.get('k_per_9'), '{:.1f}'):>4}  "
                  f"{str(ip):>5}  {sm}")

        # ── Team offensive barrel% ───────────────────────────────────────────
        # Written to ctx["team_away"]["barrel_pct"] and ctx["team_home"]["barrel_pct"].
        # Skipped silently when fetch_teamstats.py has not yet run (no team_away/home).
        for side_key, abbr in [
            ("team_away", game["away"]["abbr"]),
            ("team_home", game["home"]["abbr"]),
        ]:
            team = ctx.get(side_key)
            if team is not None and abbr in team_barrel_pct:
                team["barrel_pct"] = team_barrel_pct[abbr]

        game["context"] = ctx

    # ── Save ──────────────────────────────────────────────────────────────────
    with open(games_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)

    print(f"\nStep 3: Saved -> {games_path.relative_to(project_root)}")

    print(f"\n{'='*55}")
    print(f"  DONE")
    print(f"  Pitchers processed:  {pitchers_total}")
    print(f"  Savant data matched: {matched} / {pitchers_with_id} with ID")
    print(f"  FIP: computed from HR/BB/HBP/K/IP (no FanGraphs needed)")
    print(f"  Whiff%: from statcast_pitcher_expected_stats (whiff_percent column)")
    print(f"  Team Brl%: loaded from data/static/team_barrels.txt via load_static_data")
    print(f"  Note: xFIP / K%% / BB%% / BABIP still unavailable (FanGraphs 403)")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add advanced Savant stats to pitcher contexts in games.json."
    )
    parser.add_argument("--sport", default="mlb")
    parser.add_argument("--date",  default=None,
        help="Slate date YYYY-MM-DD. Default: today ET.")
    args = parser.parse_args()
    fetch_pitcher_advanced(sport=args.sport, date=args.date)

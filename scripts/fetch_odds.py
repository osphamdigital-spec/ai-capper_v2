#!/usr/bin/env python
"""
scripts/fetch_odds.py

Fetch today's odds from TheOddsAPI and write canonical Game objects to disk.

Usage:
    python scripts/fetch_odds.py --sport mlb
    python scripts/fetch_odds.py --sport mlb --date 2026-06-01
    python scripts/fetch_odds.py --sport nba

Writes:
    data/[sport]/[date]/odds_raw.json   -- raw API response (cache, never modified)
    data/[sport]/[date]/games.json      -- canonical Game objects (odds + context + picks)

If games.json already exists for today (a second or third fetch):
    - odds.opening_snapshot is PRESERVED — it is our proxy for the opening line
    - odds.current is OVERWRITTEN with the latest prices
    - context, picks, result blocks are left untouched

Environment variable required:
    ODDS_API_KEY -- your TheOddsAPI key
    Set it with:  $env:ODDS_API_KEY = "your_key_here"
"""

import argparse
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tz_util import ET


# ─────────────────────────────────────────────────────────────────────────────
# .ENV LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _load_dotenv():
    """
    Read .env from the project root and load any KEY=VALUE pairs into os.environ.
    Real environment variables always win — this only fills in what isn't already set.
    No external packages required.
    """
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

_load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# All slate dates use US Eastern Time. See docs/TIMEZONE_STANDARD.md.

# Maps our internal sport codes to TheOddsAPI sport keys.
# The API uses these longer compound keys; we use short codes everywhere else.
SPORT_API_KEYS = {
    "mlb":   "baseball_mlb",
    "nba":   "basketball_nba",
    "nhl":   "icehockey_nhl",
    "nfl":   "americanfootball_nfl",
    "ncaaf": "americanfootball_ncaaf",
    "ncaab": "basketball_ncaab",
}

# TheOddsAPI v4 base URL
API_BASE = "https://api.the-odds-api.com/v4"


# ─────────────────────────────────────────────────────────────────────────────
# TEAM ABBREVIATION LOOKUP TABLES
# ─────────────────────────────────────────────────────────────────────────────
# Source priority: official league naming (1) > TheOddsAPI naming (2) > internal table (3)
# TheOddsAPI usually matches official league names for the four major sports.
# NCAAF/NCAAB names are too varied for a standard table — they fall back to full name.

MLB_ABBR = {
    "Arizona Diamondbacks":     "AZ",
    "Atlanta Braves":           "ATL",
    "Baltimore Orioles":        "BAL",
    "Boston Red Sox":           "BOS",
    "Chicago Cubs":             "CHC",
    "Chicago White Sox":        "CHW",
    "Cincinnati Reds":          "CIN",
    "Cleveland Guardians":      "CLE",
    "Colorado Rockies":         "COL",
    "Detroit Tigers":           "DET",
    "Houston Astros":           "HOU",
    "Kansas City Royals":       "KC",
    "Los Angeles Angels":       "LAA",
    "Los Angeles Dodgers":      "LAD",
    "Miami Marlins":            "MIA",
    "Milwaukee Brewers":        "MIL",
    "Minnesota Twins":          "MIN",
    "New York Mets":            "NYM",
    "New York Yankees":         "NYY",
    "Oakland Athletics":        "OAK",
    "Athletics":                "ATH",   # Sacramento move — API may use this
    "Philadelphia Phillies":    "PHI",
    "Pittsburgh Pirates":       "PIT",
    "San Diego Padres":         "SD",
    "San Francisco Giants":     "SF",
    "Seattle Mariners":         "SEA",
    "St. Louis Cardinals":      "STL",
    "Tampa Bay Rays":           "TB",
    "Texas Rangers":            "TEX",
    "Toronto Blue Jays":        "TOR",
    "Washington Nationals":     "WAS",
}

NBA_ABBR = {
    "Atlanta Hawks":           "ATL",
    "Boston Celtics":          "BOS",
    "Brooklyn Nets":           "BKN",
    "Charlotte Hornets":       "CHA",
    "Chicago Bulls":           "CHI",
    "Cleveland Cavaliers":     "CLE",
    "Dallas Mavericks":        "DAL",
    "Denver Nuggets":          "DEN",
    "Detroit Pistons":         "DET",
    "Golden State Warriors":   "GSW",
    "Houston Rockets":         "HOU",
    "Indiana Pacers":          "IND",
    "Los Angeles Clippers":    "LAC",
    "Los Angeles Lakers":      "LAL",
    "Memphis Grizzlies":       "MEM",
    "Miami Heat":              "MIA",
    "Milwaukee Bucks":         "MIL",
    "Minnesota Timberwolves":  "MIN",
    "New Orleans Pelicans":    "NOP",
    "New York Knicks":         "NYK",
    "Oklahoma City Thunder":   "OKC",
    "Orlando Magic":           "ORL",
    "Philadelphia 76ers":      "PHI",
    "Phoenix Suns":            "PHX",
    "Portland Trail Blazers":  "POR",
    "Sacramento Kings":        "SAC",
    "San Antonio Spurs":       "SAS",
    "Toronto Raptors":         "TOR",
    "Utah Jazz":               "UTA",
    "Washington Wizards":      "WAS",
}

NHL_ABBR = {
    "Anaheim Ducks":          "ANA",
    "Boston Bruins":          "BOS",
    "Buffalo Sabres":         "BUF",
    "Calgary Flames":         "CGY",
    "Carolina Hurricanes":    "CAR",
    "Chicago Blackhawks":     "CHI",
    "Colorado Avalanche":     "COL",
    "Columbus Blue Jackets":  "CBJ",
    "Dallas Stars":           "DAL",
    "Detroit Red Wings":      "DET",
    "Edmonton Oilers":        "EDM",
    "Florida Panthers":       "FLA",
    "Los Angeles Kings":      "LAK",
    "Minnesota Wild":         "MIN",
    "Montreal Canadiens":     "MTL",
    "Nashville Predators":    "NSH",
    "New Jersey Devils":      "NJD",
    "New York Islanders":     "NYI",
    "New York Rangers":       "NYR",
    "Ottawa Senators":        "OTT",
    "Philadelphia Flyers":    "PHI",
    "Pittsburgh Penguins":    "PIT",
    "San Jose Sharks":        "SJS",
    "Seattle Kraken":         "SEA",
    "St. Louis Blues":        "STL",
    "Tampa Bay Lightning":    "TBL",
    "Toronto Maple Leafs":    "TOR",
    "Utah Hockey Club":       "UTA",
    "Vancouver Canucks":      "VAN",
    "Vegas Golden Knights":   "VGK",
    "Washington Capitals":    "WSH",
    "Winnipeg Jets":          "WPG",
}

NFL_ABBR = {
    "Arizona Cardinals":       "ARI",
    "Atlanta Falcons":         "ATL",
    "Baltimore Ravens":        "BAL",
    "Buffalo Bills":           "BUF",
    "Carolina Panthers":       "CAR",
    "Chicago Bears":           "CHI",
    "Cincinnati Bengals":      "CIN",
    "Cleveland Browns":        "CLE",
    "Dallas Cowboys":          "DAL",
    "Denver Broncos":          "DEN",
    "Detroit Lions":           "DET",
    "Green Bay Packers":       "GB",
    "Houston Texans":          "HOU",
    "Indianapolis Colts":      "IND",
    "Jacksonville Jaguars":    "JAX",
    "Kansas City Chiefs":      "KC",
    "Las Vegas Raiders":       "LV",
    "Los Angeles Chargers":    "LAC",
    "Los Angeles Rams":        "LAR",
    "Miami Dolphins":          "MIA",
    "Minnesota Vikings":       "MIN",
    "New England Patriots":    "NE",
    "New Orleans Saints":      "NO",
    "New York Giants":         "NYG",
    "New York Jets":           "NYJ",
    "Philadelphia Eagles":     "PHI",
    "Pittsburgh Steelers":     "PIT",
    "San Francisco 49ers":     "SF",
    "Seattle Seahawks":        "SEA",
    "Tampa Bay Buccaneers":    "TB",
    "Tennessee Titans":        "TEN",
    "Washington Commanders":   "WAS",
}

# NCAAF and NCAAB have ~130 and ~350+ teams respectively with non-standard
# abbreviations. We store the full name and leave abbreviation as TODO.
ABBR_TABLES = {
    "mlb":   MLB_ABBR,
    "nba":   NBA_ABBR,
    "nhl":   NHL_ABBR,
    "nfl":   NFL_ABBR,
    "ncaaf": {},
    "ncaab": {},
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def utc_to_et_iso(utc_str: str) -> str:
    """
    Convert a UTC ISO 8601 string like "2026-06-01T22:40:00Z"
    to an ET ISO 8601 string like "2026-06-01T18:40:00-04:00".
    """
    dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    return dt_utc.astimezone(ET).isoformat()


def utc_to_et_date(utc_str: str) -> str:
    """
    Derive the ET slate date from a UTC commence_time string.
    A game at "2026-06-02T01:05:00Z" is 21:05 ET on June 1 — date_et is June 1,
    not June 2. Using UTC date directly would give the wrong slate date.
    """
    dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
    return dt_utc.astimezone(ET).strftime("%Y-%m-%d")


def get_abbr(sport: str, full_name: str) -> str:
    """
    Look up a team abbreviation by full name.
    Returns the full name unchanged if not found (handles NCAA and unknown teams).
    """
    return ABBR_TABLES.get(sport, {}).get(full_name, full_name)


def american_to_decimal(american: int) -> float:
    """Convert American odds to decimal odds (needed for correct averaging)."""
    if american > 0:
        return (american / 100) + 1.0
    else:
        return (100 / abs(american)) + 1.0


def decimal_to_american(decimal: float) -> int:
    """Convert decimal odds back to American odds, rounded to nearest integer."""
    if decimal >= 2.0:
        return round((decimal - 1) * 100)
    else:
        return round(-100 / (decimal - 1))


# Prices outside this range are almost certainly bad bookmaker data — reject them.
# Real MLB/NBA/NHL/NFL prices are always within -3000 to +3000.
# Prices like -10000 or +10000 appear when a book has a data error in its feed.
PRICE_MIN = -3000
PRICE_MAX =  3000


def validate_price(price: int, team: str, market: str, matchup: str) -> int | None:
    """
    Reject any American odds price that is outside the plausible range.
    Implausible prices corrupt the snapshot median and mislead the AI.

    Returns the price unchanged if valid, or None if rejected.
    Prints a WARNING line so the issue is visible in the console output.
    """
    if price is None:
        return None
    if price < PRICE_MIN or price > PRICE_MAX:
        print(f"  WARNING: implausible price {price} rejected for {team} {market} in {matchup}")
        return None
    return price


def median_american(prices: list) -> int:
    """
    Compute the median of a list of American odds prices.
    Converts to decimal first (linear scale), takes median, converts back.
    American odds are not linear so we must convert before averaging.
    """
    if not prices:
        return None
    decimals = [american_to_decimal(p) for p in prices]
    return decimal_to_american(statistics.median(decimals))


def now_utc() -> str:
    """Return the current time as a UTC ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(url: str, params: dict) -> tuple:
    """
    Make an HTTP GET request to TheOddsAPI using only stdlib urllib.
    Returns (response_body_as_dict, headers_dict).
    Raises SystemExit on HTTP errors.
    """
    full_url = url + "?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(full_url, timeout=15) as resp:
            headers = dict(resp.headers)
            body    = json.loads(resp.read().decode("utf-8"))
            return body, headers
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"ERROR: API returned HTTP {e.code}")
        print(f"  {error_body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Connection failed — {e.reason}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# PARSING — TheOddsAPI event → canonical Game object
# ─────────────────────────────────────────────────────────────────────────────

def parse_bookmaker(book: dict, away_name: str, home_name: str) -> dict:
    """
    Parse one bookmaker entry from the API into our canonical bookmaker structure.

    Key rule: NEVER use outcome array index to determine away vs home.
    Always match by comparing outcome["name"] to event-level team names.
    The API does not guarantee ordering.
    """
    entry = {
        "key":        book["key"],
        "name":       book["title"],
        "updated_at": None,
    }

    # Build a matchup label used in any validation warning messages
    matchup = f"{away_name} @ {home_name}"

    for market in book.get("markets", []):
        mkey   = market["key"]
        update = market.get("last_update")

        # Use market-level last_update (more precise than bookmaker-level)
        if update and not entry["updated_at"]:
            entry["updated_at"] = update

        if mkey == "h2h":
            # Moneyline — validate each price before storing.
            # Bad bookmaker feeds occasionally push extreme values like -10000.
            ml = {}
            for outcome in market["outcomes"]:
                raw_price = outcome["price"]
                if outcome["name"] == away_name:
                    price = validate_price(raw_price, away_name, "moneyline", matchup)
                    if price is not None:
                        ml["away"] = price
                elif outcome["name"] == home_name:
                    price = validate_price(raw_price, home_name, "moneyline", matchup)
                    if price is not None:
                        ml["home"] = price
            if ml:
                entry["moneyline"] = ml

        elif mkey == "spreads":
            # Run line / point spread — validate prices, keep points as-is.
            # Points (±1.5 for MLB) are never implausible so no validation needed there.
            rl = {}
            for outcome in market["outcomes"]:
                raw_price = outcome["price"]
                if outcome["name"] == away_name:
                    rl["away_line"] = outcome["point"]
                    price = validate_price(raw_price, away_name, "runline", matchup)
                    if price is not None:
                        rl["away_price"] = price
                elif outcome["name"] == home_name:
                    rl["home_line"] = outcome["point"]
                    price = validate_price(raw_price, home_name, "runline", matchup)
                    if price is not None:
                        rl["home_price"] = price
            if rl:
                entry["runline"] = rl

        elif mkey == "totals":
            # Over/under — validate over and under prices.
            tot = {}
            for outcome in market["outcomes"]:
                raw_price = outcome["price"]
                if outcome["name"] == "Over":
                    tot["line"] = outcome["point"]
                    price = validate_price(raw_price, "Over", "total", matchup)
                    if price is not None:
                        tot["over_price"] = price
                elif outcome["name"] == "Under":
                    price = validate_price(raw_price, "Under", "total", matchup)
                    if price is not None:
                        tot["under_price"] = price
            if tot:
                entry["total"] = tot

    return entry


def compute_best_available(bookmakers: list) -> dict:
    """
    Find the best (most favourable to the bettor) price per side across all bookmakers.
    'Best' always means the highest number: +189 beats +180, and -210 beats -220.

    Stores both the price and the book name so that:
      - build_prompt.py can show "best: +189 (BetOnline)" in the prompt
      - log_picks.py can record the correct price for CLV logging later

    Returns a dict with moneyline, runline, and total keys.
    Any side that has no data (no book covered it) is stored as None.
    """
    best = {
        "moneyline": {"away": None, "home": None},
        "runline":   {"away_price": None, "home_price": None},
        "total":     {"over": None, "under": None},
    }

    for bk in bookmakers:
        name = bk["name"]

        if "moneyline" in bk:
            for side in ("away", "home"):
                price = bk["moneyline"].get(side)
                if price is not None:
                    cur = best["moneyline"][side]
                    if cur is None or price > cur["price"]:
                        best["moneyline"][side] = {"price": price, "book": name}

        if "runline" in bk:
            for key in ("away_price", "home_price"):
                price = bk["runline"].get(key)
                if price is not None:
                    cur = best["runline"][key]
                    if cur is None or price > cur["price"]:
                        best["runline"][key] = {"price": price, "book": name}

        if "total" in bk:
            for side, bk_key in [("over", "over_price"), ("under", "under_price")]:
                price = bk["total"].get(bk_key)
                if price is not None:
                    cur = best["total"][side]
                    if cur is None or price > cur["price"]:
                        best["total"][side] = {"price": price, "book": name}

    return best


def compute_snapshot(bookmakers: list) -> dict:
    """
    Compute a single consensus odds snapshot from all available bookmakers.
    Uses median of decimal-converted prices — robust to outliers, mathematically correct.
    This is used for opening_snapshot (first fetch of day) to represent the market line.
    """
    away_ml, home_ml = [], []
    away_rl, away_rl_p, home_rl, home_rl_p = [], [], [], []
    totals, over_p, under_p = [], [], []

    for bk in bookmakers:
        if "moneyline" in bk:
            if "away" in bk["moneyline"]:
                away_ml.append(bk["moneyline"]["away"])
            if "home" in bk["moneyline"]:
                home_ml.append(bk["moneyline"]["home"])

        if "runline" in bk:
            rl = bk["runline"]
            if "away_line" in rl:
                away_rl.append(rl["away_line"])
            if "away_price" in rl:
                away_rl_p.append(rl["away_price"])
            if "home_line" in rl:
                home_rl.append(rl["home_line"])
            if "home_price" in rl:
                home_rl_p.append(rl["home_price"])

        if "total" in bk:
            tot = bk["total"]
            if "line" in tot:
                totals.append(tot["line"])
            if "over_price" in tot:
                over_p.append(tot["over_price"])
            if "under_price" in tot:
                under_p.append(tot["under_price"])

    snap = {"fetched_at": now_utc()}

    if away_ml and home_ml:
        snap["moneyline"] = {
            "away": median_american(away_ml),
            "home": median_american(home_ml),
        }

    if away_rl and away_rl_p and home_rl and home_rl_p:
        snap["runline"] = {
            "away_line":  statistics.median(away_rl),
            "away_price": median_american(away_rl_p),
            "home_line":  statistics.median(home_rl),
            "home_price": median_american(home_rl_p),
        }

    if totals and over_p and under_p:
        snap["total"] = {
            "line":        statistics.median(totals),
            "over_price":  median_american(over_p),
            "under_price": median_american(under_p),
        }

    return snap


def parse_event(event: dict, sport: str) -> dict:
    """
    Convert one raw TheOddsAPI event dict into our canonical Game object.

    The canonical Game object is the join key for everything downstream:
    context data (pitchers/weather/umpires), picks, results, and grades
    all reference game_id.
    """
    game_id      = event["id"]
    away_name    = event["away_team"]
    home_name    = event["home_team"]
    commence_utc = event["commence_time"]

    bookmakers = [
        parse_bookmaker(bk, away_name, home_name)
        for bk in event.get("bookmakers", [])
    ]

    snapshot = compute_snapshot(bookmakers)
    fetched  = now_utc()

    return {
        # ── IDENTITY ────────────────────────────────────────────────────────
        "game_id":       game_id,            # TheOddsAPI UUID — immutable join key
        "sport":         sport,
        "date_et":       utc_to_et_date(commence_utc),  # ET slate date, never UTC date
        "status":        "pre",
        "status_source": "theoddsapi",

        # ── TEAMS ───────────────────────────────────────────────────────────
        "away": {
            "name":        away_name,
            "abbr":        get_abbr(sport, away_name),
            "name_source": "theoddsapi",    # source priority 2 — no official API yet
            "abbr_source": "internal_lookup",
        },
        "home": {
            "name":        home_name,
            "abbr":        get_abbr(sport, home_name),
            "name_source": "theoddsapi",
            "abbr_source": "internal_lookup",
        },

        # ── SCHEDULE ────────────────────────────────────────────────────────
        "commence_utc": commence_utc,
        "commence_et":  utc_to_et_iso(commence_utc),

        # ── ODDS ────────────────────────────────────────────────────────────
        "odds": {
            "source":           "theoddsapi",
            "source_priority":  1,
            # First fetch of the day — never overwritten (our opening line proxy)
            "opening_snapshot": snapshot,
            # Updated on every fetch — compare to opening_snapshot for line movement
            "current_snapshot": snapshot,
            # Best price per side across all books — updated every fetch
            # Used in the prompt for "best available" display and in CLV logging
            "best_available": {
                **compute_best_available(bookmakers),
                "fetched_at": snapshot["fetched_at"],
            },
            "current": {
                "fetched_at": fetched,
                "bookmakers": bookmakers,
            },
            "closing_snapshot": None,       # filled by fetch_closing.py at game time
        },

        # ── CONTEXT ─────────────────────────────────────────────────────────
        # Filled by scrape_context.py (pitchers, weather, umpires from Covers)
        "context": None,

        # ── RESULT ──────────────────────────────────────────────────────────
        # Filled by fetch_results.py after game finishes
        "result": {
            "away_score":      None,
            "home_score":      None,
            "final_at":        None,
            "source":          None,       # official_league | manual_verification
            "source_priority": None,
            "verified":        False,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# MERGE — preserve opening_snapshot on subsequent fetches
# ─────────────────────────────────────────────────────────────────────────────

def merge_games(existing: list, fresh: list) -> list:
    """
    Merge freshly fetched Game objects into the existing games.json.

    Opening snapshot is preserved — it captures the first line of the day,
    which is our proxy for the opening line on the free API tier.
    Only odds.current is updated on subsequent fetches.
    Context, picks, and result blocks are never touched here.
    """
    by_id = {g["game_id"]: g for g in existing}

    for new_game in fresh:
        gid = new_game["game_id"]
        if gid in by_id:
            # opening_snapshot is never overwritten — it is the first line of the day
            # current_snapshot, best_available, and current all update with each fetch
            by_id[gid]["odds"]["current"]          = new_game["odds"]["current"]
            by_id[gid]["odds"]["current_snapshot"] = new_game["odds"]["current_snapshot"]
            by_id[gid]["odds"]["best_available"]   = new_game["odds"]["best_available"]
        else:
            # Game wasn't in this morning's file — add it (e.g. newly scheduled)
            by_id[gid] = new_game

    return list(by_id.values())


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_odds(sport: str = "mlb", date: str = None):
    """
    Fetch odds from TheOddsAPI and write canonical Game objects.

    Args:
        sport: Internal sport code (mlb, nba, nhl, nfl, ncaaf, ncaab)
        date:  Override target date (YYYY-MM-DD). Default: today in US Eastern Time.
    """

    # ── Validate inputs ──────────────────────────────────────────────────────
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        print("ERROR: ODDS_API_KEY not set.")
        print("  Add it to the .env file in the project root:")
        print('    ODDS_API_KEY=your_key_here')
        sys.exit(1)

    sport = sport.lower()
    if sport not in SPORT_API_KEYS:
        print(f"ERROR: Unknown sport '{sport}'.")
        print(f"  Valid options: {list(SPORT_API_KEYS.keys())}")
        sys.exit(1)

    target_date   = date or today_et()
    api_sport_key = SPORT_API_KEYS[sport]

    print(f"\n{'='*55}")
    print(f"  FETCH ODDS — {sport.upper()}")
    print(f"  Slate date (US ET): {target_date}")
    print(f"{'='*55}\n")

    # ── Output paths ─────────────────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data" / sport / target_date
    data_dir.mkdir(parents=True, exist_ok=True)

    raw_path   = data_dir / "odds_raw.json"
    games_path = data_dir / "games.json"

    # ── Call TheOddsAPI ──────────────────────────────────────────────────────
    url = f"{API_BASE}/sports/{api_sport_key}/odds"
    params = {
        "apiKey":     api_key,
        "regions":    "us",
        "markets":    "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }

    print("Step 1: Calling TheOddsAPI...")
    raw_data, headers = api_get(url, params)

    # Log remaining credits — free tier is 500/month, we want visibility
    remaining = headers.get("X-Requests-Remaining", headers.get("x-requests-remaining", "?"))
    used      = headers.get("X-Requests-Used",      headers.get("x-requests-used",      "?"))
    print(f"  Events returned:   {len(raw_data)}")
    print(f"  Credits used:      {used}   |   Remaining this month: {remaining}")

    if not raw_data:
        print(f"\nNo {sport.upper()} events returned. Slate may not be posted yet.")
        sys.exit(0)

    # ── Save raw response ─────────────────────────────────────────────────────
    with open(raw_path, "w") as f:
        json.dump(raw_data, f, indent=2)
    print(f"\nStep 2: Raw response saved -> {raw_path.relative_to(project_root)}")

    # ── Filter to target date and parse ──────────────────────────────────────
    # TheOddsAPI returns ALL upcoming events for the sport — we filter to today.
    print(f"\nStep 3: Filtering to {target_date} and parsing events...")

    fresh_games = []
    other_dates = set()
    for event in raw_data:
        event_date = utc_to_et_date(event["commence_time"])
        if event_date == target_date:
            fresh_games.append(parse_event(event, sport))
        else:
            other_dates.add(event_date)

    if other_dates:
        print(f"  Skipped events on other dates: {sorted(other_dates)}")

    print(f"  Games on {target_date}: {len(fresh_games)}")

    if not fresh_games:
        print(f"\nNo {sport.upper()} games found for {target_date}.")
        sys.exit(0)

    # ── Merge or create games.json ────────────────────────────────────────────
    if games_path.exists():
        print(f"\nStep 4: games.json exists — merging (opening_snapshot preserved)...")
        with open(games_path) as f:
            existing = json.load(f)
        final_games = merge_games(existing, fresh_games)
        is_first_fetch = False
    else:
        print(f"\nStep 4: First fetch today — creating games.json with opening_snapshot...")
        final_games = fresh_games
        is_first_fetch = True

    # Sort chronologically by ET game time
    final_games.sort(key=lambda g: g["commence_utc"])

    # ── Write games.json ──────────────────────────────────────────────────────
    with open(games_path, "w") as f:
        json.dump(final_games, f, indent=2)

    print(f"\nStep 5: Game objects saved -> {games_path.relative_to(project_root)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  DONE")
    print(f"  Sport:        {sport.upper()}")
    print(f"  Date:         {target_date}")
    print(f"  Games:        {len(final_games)}")
    if is_first_fetch:
        print(f"  Snapshot:     opening_snapshot SET (first fetch)")
    else:
        print(f"  Snapshot:     opening_snapshot PRESERVED")
    print(f"{'='*55}\n")

    # ── Slate table ───────────────────────────────────────────────────────────
    print(f"  {'Time ET':<8}  {'Matchup':<20}  {'ML (median)':<16}  {'Total':<8}  Books")
    print("  " + "-" * 66)
    for game in final_games:
        # "HH:MM" from the ET ISO string
        time_et = game["commence_et"][11:16]
        matchup = f"{game['away']['abbr']} @ {game['home']['abbr']}"

        snap = game["odds"]["opening_snapshot"]

        ml_str = ""
        if "moneyline" in snap:
            a, h = snap["moneyline"]["away"], snap["moneyline"]["home"]
            ml_str = f"{'+' if a>0 else ''}{a} / {'+' if h>0 else ''}{h}"

        total_str = ""
        if "total" in snap:
            total_str = f"o/u {snap['total']['line']}"

        n_books = len(game["odds"]["current"]["bookmakers"])
        print(f"  {time_et:<8}  {matchup:<20}  {ml_str:<16}  {total_str:<8}  {n_books}")

    print()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch odds from TheOddsAPI and write canonical Game objects."
    )
    parser.add_argument(
        "--sport", default="mlb",
        help="Sport code: mlb, nba, nhl, nfl, ncaaf, ncaab  (default: mlb)"
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    args = parser.parse_args()

    fetch_odds(sport=args.sport, date=args.date)

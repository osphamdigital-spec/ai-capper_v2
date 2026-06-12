#!/usr/bin/env python
"""
scripts/fetch_weather.py

Fetch game-time weather forecasts from Open-Meteo and write into the context
block of each game in data/mlb/[date]/games.json.

Open-Meteo is free, requires no API key, and returns hourly forecasts by lat/lon.

Roof logic:
  dome        — no API call; weather block written with null values + explanatory note
  retractable — API call made; weather written with note that roof may be open/closed
  outdoor     — API call made; weather written normally

Existing context fields (pitcher_away, pitcher_home, umpire) are never touched.

Usage:
    python scripts/fetch_weather.py
    python scripts/fetch_weather.py --date 2026-06-01

Modifies:
    data/mlb/[date]/games.json  -- writes context.weather for each game
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tz_util import ET


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"


# ─────────────────────────────────────────────────────────────────────────────
# STADIUM TABLE
# ─────────────────────────────────────────────────────────────────────────────
# Keyed by the full team name used in TheOddsAPI / MLB Stats API.
# roof: "outdoor" | "retractable" | "dome"
# Retractable = team can open or close; we fetch weather but note uncertainty.
# Dome = climate-controlled; weather is never relevant.

STADIUMS = {
    "Arizona Diamondbacks": {
        "venue": "Chase Field",
        "city":  "Phoenix, AZ",
        "lat":   33.4453, "lon": -112.0667,
        "roof":  "retractable",
    },
    "Atlanta Braves": {
        "venue": "Truist Park",
        "city":  "Cumberland, GA",
        "lat":   33.8908, "lon": -84.4678,
        "roof":  "outdoor",
    },
    "Baltimore Orioles": {
        "venue": "Oriole Park at Camden Yards",
        "city":  "Baltimore, MD",
        "lat":   39.2838, "lon": -76.6217,
        "roof":  "outdoor",
    },
    "Boston Red Sox": {
        "venue": "Fenway Park",
        "city":  "Boston, MA",
        "lat":   42.3467, "lon": -71.0972,
        "roof":  "outdoor",
    },
    "Chicago Cubs": {
        "venue": "Wrigley Field",
        "city":  "Chicago, IL",
        "lat":   41.9484, "lon": -87.6553,
        "roof":  "outdoor",
    },
    "Chicago White Sox": {
        "venue": "Guaranteed Rate Field",
        "city":  "Chicago, IL",
        "lat":   41.8300, "lon": -87.6338,
        "roof":  "outdoor",
    },
    "Cincinnati Reds": {
        "venue": "Great American Ball Park",
        "city":  "Cincinnati, OH",
        "lat":   39.0979, "lon": -84.5082,
        "roof":  "outdoor",
    },
    "Cleveland Guardians": {
        "venue": "Progressive Field",
        "city":  "Cleveland, OH",
        "lat":   41.4962, "lon": -81.6852,
        "roof":  "outdoor",
    },
    "Colorado Rockies": {
        "venue": "Coors Field",
        "city":  "Denver, CO",
        "lat":   39.7559, "lon": -104.9942,
        "roof":  "outdoor",
    },
    "Detroit Tigers": {
        "venue": "Comerica Park",
        "city":  "Detroit, MI",
        "lat":   42.3390, "lon": -83.0485,
        "roof":  "outdoor",
    },
    "Houston Astros": {
        "venue": "Minute Maid Park",
        "city":  "Houston, TX",
        "lat":   29.7573, "lon": -95.3555,
        "roof":  "retractable",
    },
    "Kansas City Royals": {
        "venue": "Kauffman Stadium",
        "city":  "Kansas City, MO",
        "lat":   39.0517, "lon": -94.4803,
        "roof":  "outdoor",
    },
    "Los Angeles Angels": {
        "venue": "Angel Stadium",
        "city":  "Anaheim, CA",
        "lat":   33.8003, "lon": -117.8827,
        "roof":  "outdoor",
    },
    "Los Angeles Dodgers": {
        "venue": "Dodger Stadium",
        "city":  "Los Angeles, CA",
        "lat":   34.0739, "lon": -118.2400,
        "roof":  "outdoor",
    },
    "Miami Marlins": {
        "venue": "loanDepot park",
        "city":  "Miami, FL",
        "lat":   25.7781, "lon": -80.2197,
        "roof":  "retractable",
    },
    "Milwaukee Brewers": {
        "venue": "American Family Field",
        "city":  "Milwaukee, WI",
        "lat":   43.0280, "lon": -87.9712,
        "roof":  "retractable",
    },
    "Minnesota Twins": {
        "venue": "Target Field",
        "city":  "Minneapolis, MN",
        "lat":   44.9817, "lon": -93.2782,
        "roof":  "outdoor",
    },
    "New York Mets": {
        "venue": "Citi Field",
        "city":  "Flushing, NY",
        "lat":   40.7571, "lon": -73.8458,
        "roof":  "outdoor",
    },
    "New York Yankees": {
        "venue": "Yankee Stadium",
        "city":  "Bronx, NY",
        "lat":   40.8296, "lon": -73.9262,
        "roof":  "outdoor",
    },
    "Oakland Athletics": {
        "venue": "Sutter Health Park",
        "city":  "Sacramento, CA",
        "lat":   38.5802, "lon": -121.5085,
        "roof":  "outdoor",
    },
    "Athletics": {
        "venue": "Sutter Health Park",    # name used post-move if API updates
        "city":  "Sacramento, CA",
        "lat":   38.5802, "lon": -121.5085,
        "roof":  "outdoor",
    },
    "Philadelphia Phillies": {
        "venue": "Citizens Bank Park",
        "city":  "Philadelphia, PA",
        "lat":   39.9057, "lon": -75.1665,
        "roof":  "outdoor",
    },
    "Pittsburgh Pirates": {
        "venue": "PNC Park",
        "city":  "Pittsburgh, PA",
        "lat":   40.4469, "lon": -80.0057,
        "roof":  "outdoor",
    },
    "San Diego Padres": {
        "venue": "Petco Park",
        "city":  "San Diego, CA",
        "lat":   32.7076, "lon": -117.1570,
        "roof":  "outdoor",
    },
    "San Francisco Giants": {
        "venue": "Oracle Park",
        "city":  "San Francisco, CA",
        "lat":   37.7786, "lon": -122.3893,
        "roof":  "outdoor",
    },
    "Seattle Mariners": {
        "venue": "T-Mobile Park",
        "city":  "Seattle, WA",
        "lat":   47.5914, "lon": -122.3325,
        "roof":  "retractable",
    },
    "St. Louis Cardinals": {
        "venue": "Busch Stadium",
        "city":  "St. Louis, MO",
        "lat":   38.6226, "lon": -90.1928,
        "roof":  "outdoor",
    },
    "Tampa Bay Rays": {
        "venue": "Tropicana Field",
        "city":  "St. Petersburg, FL",
        "lat":   27.7683, "lon": -82.6534,
        "roof":  "dome",
    },
    "Texas Rangers": {
        "venue": "Globe Life Field",
        "city":  "Arlington, TX",
        "lat":   32.7512, "lon": -97.0832,
        "roof":  "retractable",
    },
    "Toronto Blue Jays": {
        "venue": "Rogers Centre",
        "city":  "Toronto, ON",
        "lat":   43.6414, "lon": -79.3894,
        "roof":  "retractable",
    },
    "Washington Nationals": {
        "venue": "Nationals Park",
        "city":  "Washington, DC",
        "lat":   38.8730, "lon": -77.0074,
        "roof":  "outdoor",
    },
}

# WMO weather interpretation codes → human-readable description
# Source: Open-Meteo docs / WMO 306 standard
WMO_CODES = {
    0:  "Clear sky",
    1:  "Mainly clear",
    2:  "Partly cloudy",
    3:  "Overcast",
    45: "Fog",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Wind direction degrees → compass abbreviation (16-point, rounded to 8)
def degrees_to_compass(degrees: float) -> str:
    """Convert wind direction degrees to 8-point compass abbreviation."""
    if degrees is None:
        return None
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(degrees / 45) % 8
    return dirs[idx]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(url: str, params: dict, retries: int = 3, backoff: float = 3.0) -> dict | None:
    """
    HTTP GET using stdlib urllib. Returns parsed JSON or None on error.
    Retries up to `retries` times on transient SSL/connection errors,
    waiting backoff * attempt seconds between tries (3s, 6s, 9s by default).
    """
    full_url = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(full_url, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"  ERROR: HTTP {e.code}")
            return None  # 4xx/5xx -- no point retrying
        except urllib.error.URLError as e:
            if attempt < retries:
                wait = backoff * attempt
                print(f"  ERROR: Connection failed -- {e.reason}  (retry {attempt}/{retries - 1} in {wait:.0f}s)")
                time.sleep(wait)
            else:
                print(f"  ERROR: Connection failed -- {e.reason}  (all {retries} attempts exhausted)")
                return None


# ─────────────────────────────────────────────────────────────────────────────
# WEATHER FETCH AND PARSE
# ─────────────────────────────────────────────────────────────────────────────

def fetch_hourly_forecast(lat: float, lon: float) -> dict | None:
    """
    Fetch 2-day hourly forecast from Open-Meteo for the given coordinates.
    Returns the full API response dict, or None on error.

    forecast_days=2 ensures we always capture late games (9pm+ ET).
    Temperature in Fahrenheit, wind speed in mph — no unit conversion needed.
    timezone=America/New_York means the time array is in ET.
    """
    return api_get(OPEN_METEO_BASE, {
        "latitude":         lat,
        "longitude":        lon,
        "hourly":           "temperature_2m,windspeed_10m,winddirection_10m,"
                            "precipitation_probability,weathercode",
        "temperature_unit": "fahrenheit",
        "windspeed_unit":   "mph",
        "timezone":         "America/New_York",
        "forecast_days":    2,
    })


def extract_game_hour_weather(forecast: dict, commence_et: str) -> dict:
    """
    Extract the hourly forecast values for the game's start hour.

    commence_et: ISO 8601 string in ET e.g. "2026-06-01T18:41:00-04:00"
    The hourly time array from Open-Meteo looks like:
      ["2026-06-01T00:00", "2026-06-01T01:00", ...]
    We match by constructing the target hour string: "YYYY-MM-DDTHH:00"

    Returns a dict with temp_f, wind_mph, wind_dir, precipitation_pct, conditions.
    Returns all-None dict if the game hour isn't in the forecast window.
    """
    empty = {
        "temp_f": None, "wind_mph": None, "wind_dir": None,
        "precipitation_pct": None, "conditions": None,
    }

    if not forecast:
        return empty

    hourly = forecast.get("hourly", {})
    times  = hourly.get("time", [])

    if not times:
        return empty

    # Parse the game start time to get the ET date + hour
    # commence_et example: "2026-06-01T18:41:00-04:00"
    try:
        dt = datetime.fromisoformat(commence_et)
        # Build the target time string matching Open-Meteo's format: "YYYY-MM-DDTHH:00"
        target = dt.strftime("%Y-%m-%dT%H:00")
    except (ValueError, TypeError):
        return empty

    # Find the matching hour index
    try:
        idx = times.index(target)
    except ValueError:
        # Game time not in forecast window — shouldn't happen with forecast_days=2
        return empty

    def safe_get(key):
        arr = hourly.get(key, [])
        return arr[idx] if idx < len(arr) else None

    temp_f       = safe_get("temperature_2m")
    wind_mph     = safe_get("windspeed_10m")
    wind_deg     = safe_get("winddirection_10m")
    precip_pct   = safe_get("precipitation_probability")
    weather_code = safe_get("weathercode")

    conditions = WMO_CODES.get(int(weather_code), f"Code {weather_code}") \
        if weather_code is not None else None

    return {
        "temp_f":           round(temp_f, 1) if temp_f is not None else None,
        "wind_mph":         round(wind_mph, 1) if wind_mph is not None else None,
        "wind_dir":         degrees_to_compass(wind_deg),
        "precipitation_pct": precip_pct,
        "conditions":       conditions,
    }


def build_weather_entry(stadium: dict, weather_values: dict | None, is_dome: bool) -> dict:
    """
    Build the canonical weather context entry.

    For domes: all weather fields are null with a note.
    For outdoor/retractable: populate from the forecast.
    """
    entry = {
        "venue":  stadium["venue"],
        "city":   stadium["city"],
        "roof":   stadium["roof"],
    }

    if is_dome:
        entry.update({
            "temp_f":            None,
            "wind_mph":          None,
            "wind_dir":          None,
            "precipitation_pct": None,
            "conditions":        None,
            "note":              "Indoor stadium — weather not applicable",
            "source":            None,
            "source_priority":   None,
        })
    else:
        entry.update(weather_values or {
            "temp_f": None, "wind_mph": None, "wind_dir": None,
            "precipitation_pct": None, "conditions": None,
        })
        if stadium["roof"] == "retractable":
            entry["note"] = "Retractable roof — may be open or closed at game time"
        entry["source"]           = "open_meteo"
        entry["source_priority"]  = 1

    entry["fetched_at"] = now_utc()
    return entry


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_weather(date: str = None):
    """
    Fetch game-time weather and write into games.json context blocks.

    Args:
        date: Override target date (YYYY-MM-DD). Default: today ET.
    """
    target_date = date or today_et()

    print(f"\n{'='*55}")
    print(f"  FETCH WEATHER — MLB")
    print(f"  Slate date (US ET): {target_date}")
    print(f"{'='*55}\n")

    # ── Load games.json ───────────────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    games_path = project_root / "data" / "mlb" / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found.")
        print(f"  Expected: {games_path}")
        print(f"  Run fetch_odds.py first.")
        sys.exit(1)

    with open(games_path) as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games from games.json\n")

    # ── Process each game ─────────────────────────────────────────────────────
    updated   = 0
    domes     = 0
    no_stadium = []

    for game in games:
        home_name = game["home"]["name"]
        matchup   = f"{game['away']['abbr']} @ {game['home']['abbr']}"

        stadium = STADIUMS.get(home_name)

        if not stadium:
            print(f"  WARNING: No stadium entry for '{home_name}' ({matchup})")
            no_stadium.append(matchup)
            continue

        is_dome = stadium["roof"] == "dome"

        if is_dome:
            # No API call for dome stadiums
            weather_values = None
            print(f"  {matchup}: {stadium['venue']} — dome, skipping API call")
            domes += 1
        else:
            # Fetch hourly forecast for this stadium
            forecast = fetch_hourly_forecast(stadium["lat"], stadium["lon"])
            weather_values = extract_game_hour_weather(forecast, game["commence_et"])

            # Format a quick summary line
            if weather_values and weather_values.get("temp_f") is not None:
                t  = weather_values["temp_f"]
                w  = weather_values["wind_mph"]
                wd = weather_values["wind_dir"]
                c  = weather_values["conditions"]
                p  = weather_values["precipitation_pct"]
                print(f"  {matchup}: {t}°F, {w}mph {wd}, {c}, {p}% precip")
            else:
                print(f"  {matchup}: weather fetch failed or game time out of window")

        weather_entry = build_weather_entry(stadium, weather_values, is_dome)

        # Write into context block — preserve pitcher and umpire fields
        ctx = game.get("context") or {}
        ctx["weather"] = weather_entry
        game["context"] = ctx

        updated += 1

    # ── Save updated games.json ───────────────────────────────────────────────
    with open(games_path, "w") as f:
        json.dump(games, f, indent=2)

    print(f"\nStep 2: Saved -> {games_path.relative_to(project_root)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    api_calls = updated - domes
    print(f"\n{'='*55}")
    print(f"  DONE")
    print(f"  Games updated:     {updated}/{len(games)}")
    print(f"  Open-Meteo calls:  {api_calls}  (domes skipped: {domes})")
    if no_stadium:
        print(f"  Missing stadium:   {no_stadium}")
    print(f"{'='*55}\n")

    # ── Print one completed context block ─────────────────────────────────────
    print("COMPLETED CONTEXT BLOCK — one outdoor game (MIA @ WAS):")
    print("-" * 55)
    for game in games:
        if game["away"]["abbr"] == "MIA":
            ctx = game.get("context", {})
            display = {
                "game_id":    game["game_id"],
                "matchup":    f"{game['away']['abbr']} @ {game['home']['abbr']}",
                "commence_et": game["commence_et"],
                "context": {
                    "pitcher_away": ctx.get("pitcher_away"),
                    "pitcher_home": ctx.get("pitcher_home"),
                    "weather":      ctx.get("weather"),
                    "umpire":       ctx.get("umpire"),
                },
            }
            print(json.dumps(display, indent=2))
            break


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch game-time weather from Open-Meteo and write into games.json."
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    args = parser.parse_args()

    fetch_weather(date=args.date)

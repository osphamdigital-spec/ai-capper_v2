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

# ─────────────────────────────────────────────────────────────────────────────
# CF BEARING TABLE
# ─────────────────────────────────────────────────────────────────────────────
# Compass bearing in degrees (0 = North, 90 = East, clockwise) from home plate
# to centre field for each MLB park.  Used to compute the angle between the
# wind-to vector and the CF axis — raw geometry only; models interpret it.
#
# Convention: degrees clockwise from North; home-plate → CF direction.
# is_estimate=True: value should be verified against a published azimuth source.
#   Recommended sources: Andrew Clem orientation data (andrewclem.com/Baseball)
#   or Seamheads ballpark database (seamheads.com/ballparks).
# is_estimate=False: verified from multiple independent published sources.
# None entry: dome (wind geometry not applicable) or orientation unknown.
#
# Structure: { team_name: (cf_bearing_deg: int, is_estimate: bool) | None }

CF_BEARINGS: dict[str, tuple[int, bool] | None] = {
    # ── VERIFIED (multiple independent published sources) ─────────────────────
    "Chicago Cubs":             (43,  False),  # Wrigley Field — NE; well-documented; SW wind = out
    "Colorado Rockies":         (42,  False),  # Coors Field — NNE; well-documented; SW wind = out

    # ── ESTIMATED — verify against Andrew Clem / Seamheads ───────────────────
    # Source for all estimates: published ballpark orientation literature cross-
    # referenced with documented "blowing out" wind directions per park.
    # Cite: Andrew Clem (andrewclem.com/Baseball) or Seamheads ballpark DB.
    "Arizona Diamondbacks":     (348, True),   # Chase Field, Phoenix — NNW
    "Atlanta Braves":           (250, True),   # Truist Park, Cumberland GA — WSW
    "Baltimore Orioles":        (325, True),   # Camden Yards — NW
    "Boston Red Sox":           ( 37, True),   # Fenway Park — NNE; Green Monster to W
    "Chicago White Sox":        (337, True),   # Guaranteed Rate Field — NNW
    "Cincinnati Reds":          (290, True),   # GABP — WNW; river to RF
    "Cleveland Guardians":      (322, True),   # Progressive Field — NW
    "Detroit Tigers":           (340, True),   # Comerica Park — NNW
    "Houston Astros":           (314, True),   # Minute Maid Park — NW
    "Kansas City Royals":       (  5, True),   # Kauffman Stadium — N
    "Los Angeles Angels":       (290, True),   # Angel Stadium — WNW
    "Los Angeles Dodgers":      (352, True),   # Dodger Stadium — NNW
    "Miami Marlins":            (310, True),   # loanDepot park — NW
    "Milwaukee Brewers":        (353, True),   # American Family Field — N
    "Minnesota Twins":          (319, True),   # Target Field — NW
    "New York Mets":            (349, True),   # Citi Field — NNW
    "New York Yankees":         ( 23, True),   # Yankee Stadium — NNE
    # Sutter Health Park (Sacramento) — A's home 2025+.  Home plate at
    # 38.580286, -121.513927.  Park faces NE quadrant per operator research.
    # PLACEHOLDER — midpoint of NE quadrant rule-of-thumb, NOT verified against
    # satellite trace or published azimuth dataset.  Replace with measured value.
    "Oakland Athletics":        ( 45, True),   # Sutter Health Park — NE placeholder (est)
    "Athletics":                ( 45, True),   # same park, alternative API name
    "Philadelphia Phillies":    (325, True),   # Citizens Bank Park — NW
    "Pittsburgh Pirates":       (318, True),   # PNC Park — NW; river behind RF
    "San Diego Padres":         (299, True),   # Petco Park — WNW
    "San Francisco Giants":     ( 95, True),   # Oracle Park — E; bay to RF, city to CF
    "Seattle Mariners":         (  8, True),   # T-Mobile Park — N
    "St. Louis Cardinals":      (323, True),   # Busch Stadium — NW
    "Tampa Bay Rays":           None,           # Tropicana Field — dome; not applicable
    "Texas Rangers":            (331, True),   # Globe Life Field — NNW
    "Toronto Blue Jays":        (344, True),   # Rogers Centre — NNW
    "Washington Nationals":     ( 36, True),   # Nationals Park — NNE
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
                            "windgusts_10m,relativehumidity_2m,surface_pressure,"
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

    Returns a dict with temp_f, wind_mph, wind_dir, wind_from_deg, wind_to_deg,
    wind_gust_mph, humidity_pct, pressure_hpa, precipitation_pct, conditions.
    Returns all-None dict if the game hour isn't in the forecast window.

    wind_from_deg: met convention — direction the wind blows FROM (0=N, 90=E).
                   This is Open-Meteo's native winddirection_10m convention.
    wind_to_deg:   (wind_from_deg + 180) % 360 — direction wind blows TOWARD.
    """
    empty = {
        "temp_f": None, "wind_mph": None, "wind_dir": None,
        "wind_from_deg": None, "wind_to_deg": None,
        "wind_gust_mph": None, "humidity_pct": None, "pressure_hpa": None,
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
    wind_gust    = safe_get("windgusts_10m")
    humidity     = safe_get("relativehumidity_2m")
    pressure     = safe_get("surface_pressure")
    precip_pct   = safe_get("precipitation_probability")
    weather_code = safe_get("weathercode")

    conditions = WMO_CODES.get(int(weather_code), f"Code {weather_code}") \
        if weather_code is not None else None

    wind_from_deg = round(wind_deg) if wind_deg is not None else None
    wind_to_deg   = (wind_from_deg + 180) % 360 if wind_from_deg is not None else None

    return {
        "temp_f":            round(temp_f, 1)    if temp_f    is not None else None,
        "wind_mph":          round(wind_mph, 1)  if wind_mph  is not None else None,
        "wind_dir":          degrees_to_compass(wind_deg),
        "wind_from_deg":     wind_from_deg,
        "wind_to_deg":       wind_to_deg,
        "wind_gust_mph":     round(wind_gust, 1) if wind_gust is not None else None,
        "humidity_pct":      round(humidity)      if humidity  is not None else None,
        "pressure_hpa":      round(pressure, 1)  if pressure  is not None else None,
        "precipitation_pct": precip_pct,
        "conditions":        conditions,
    }


def build_weather_entry(
    stadium: dict,
    weather_values: dict | None,
    is_dome: bool,
    home_team_name: str = "",
) -> dict:
    """
    Build the canonical weather context entry.

    For domes: all weather fields are null with a note; no wind geometry.
    For outdoor/retractable: populate from the forecast including wind geometry.

    Wind geometry fields (raw evidence, no derived verdict):
      cf_bearing_deg    — home-plate → CF compass bearing from CF_BEARINGS table
      cf_bearing_est    — True when the bearing is an estimate pending verification
      wind_cf_angle_deg — min angle (0–180°) between wind-to vector and CF axis
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
            "wind_from_deg":     None,
            "wind_to_deg":       None,
            "wind_gust_mph":     None,
            "humidity_pct":      None,
            "pressure_hpa":      None,
            "precipitation_pct": None,
            "conditions":        None,
            "cf_bearing_deg":    None,
            "cf_bearing_est":    False,
            "wind_cf_angle_deg": None,
            "note":              "Indoor stadium — weather not applicable",
            "source":            None,
            "source_priority":   None,
        })
    else:
        fallback = {
            "temp_f": None, "wind_mph": None, "wind_dir": None,
            "wind_from_deg": None, "wind_to_deg": None,
            "wind_gust_mph": None, "humidity_pct": None, "pressure_hpa": None,
            "precipitation_pct": None, "conditions": None,
        }
        entry.update(weather_values or fallback)

        # CF bearing lookup (raw geometry only — models interpret significance)
        cf_entry  = CF_BEARINGS.get(home_team_name)
        if cf_entry is None:
            cf_bearing, cf_bearing_est = None, False
            if home_team_name:
                print(f"  WARNING: cf_bearing unknown for '{home_team_name}' "
                      f"— wind_geo block will show cf_bearing: UNKNOWN in prompt")
        else:
            cf_bearing, cf_bearing_est = cf_entry

        entry["cf_bearing_deg"] = cf_bearing
        entry["cf_bearing_est"] = cf_bearing_est

        wind_to = entry.get("wind_to_deg")
        if wind_to is not None and cf_bearing is not None:
            diff = abs(wind_to - cf_bearing)
            entry["wind_cf_angle_deg"] = round(min(diff, 360 - diff))
        else:
            entry["wind_cf_angle_deg"] = None

        if stadium["roof"] == "retractable":
            entry["note"] = "Retractable roof — may be open or closed at game time"
        entry["source"]          = "open_meteo"
        entry["source_priority"] = 1

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
                g  = weather_values.get("wind_gust_mph")
                wd = weather_values["wind_dir"]
                c  = weather_values["conditions"]
                p  = weather_values["precipitation_pct"]
                gust_str = f" gust {g}mph" if g is not None else ""
                print(f"  {matchup}: {t}°F, {w}mph{gust_str} {wd}, {c}, {p}% precip")
            else:
                print(f"  {matchup}: weather fetch failed or game time out of window")

        weather_entry = build_weather_entry(stadium, weather_values, is_dome, home_name)

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

    # ── CF bearing estimate warning ───────────────────────────────────────────
    # List every venue in this slate that uses an estimated CF bearing so the
    # operator can track verification against Andrew Clem or Seamheads.
    est_venues = [
        g["context"]["weather"].get("venue", g["home"]["name"])
        for g in games
        if g.get("context", {}).get("weather", {}).get("cf_bearing_est") is True
    ]
    if est_venues:
        print(f"CF BEARING ESTIMATES — {len(est_venues)} venue(s) in this slate use")
        print(f"  estimated bearings. Verify against:")
        print(f"    Andrew Clem  : andrewclem.com/Baseball")
        print(f"    Seamheads    : seamheads.com/ballparks")
        for v in sorted(set(est_venues)):
            print(f"    {v}")
        print()

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

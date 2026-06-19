#!/usr/bin/env python
"""
scripts/fetch_wind_edge.py

Fetches today's wind/park edge data from CrookedFence (crookedfence.org/data.json)
and writes it to data/mlb/YYYY-MM-DD/wind_edge.json.

Two purposes:
  1. DAILY USE — wind_edge.json is read by build_prompt.py and injected into each
     game block so models can factor park+wind edge into totals/run-line picks.

  2. ARCHIVE (reverse-engineering) — raw JSON is saved to
     data/mlb/crookedfence_archive/YYYY-MM-DD_raw.json so we can accumulate a
     dataset and reverse-engineer their formula if the site ever goes down.

CrookedFence data fields (per game):
  signal       -- hitter / hitter_strong / pitcher / pitcher_strong / neutral / roof
  hr_edge      -- HR% adjustment vs baseline (e.g. +37 = 37% more HRs expected)
  runs_edge    -- Runs% adjustment (e.g. +19 = 19% more runs expected)
  wind_effect  -- OUT / IN / IN-CROSS / OUT-CROSS / ROOF CLOSED
  wind_mph     -- integer wind speed
  temp_f       -- game-time temperature
  humidity_pct -- humidity %
  pitcher data -- HR/9, ERA, WHIP, GO/AO, profile tag per starter
  stadium_dims -- LF / CF / RF in feet

Usage:
    python scripts/fetch_wind_edge.py
    python scripts/fetch_wind_edge.py --date 2026-06-18
    python scripts/fetch_wind_edge.py --sport mlb --date 2026-06-18

Output:
    data/mlb/YYYY-MM-DD/wind_edge.json
    data/mlb/crookedfence_archive/YYYY-MM-DD_raw.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests as _requests
    _USE_REQUESTS = True
except ImportError:
    import urllib.error
    import urllib.request
    _USE_REQUESTS = False

# Add scripts/ to path so tz_util is importable
sys.path.insert(0, str(Path(__file__).parent))
from tz_util import ET


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

CROOKEDFENCE_URL  = "https://www.crookedfence.org/data.json"
RESULTS_URL       = "https://www.crookedfence.org/results.json"
PROJECT_ROOT      = Path(__file__).parent.parent

# Timeout for HTTP requests in seconds
REQUEST_TIMEOUT   = 15


# ─────────────────────────────────────────────────────────────────────────────
# HTTP FETCH
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_json(url: str) -> dict | list | None:
    """
    Fetch a URL and return parsed JSON, or None on any error.
    Uses requests if available (handles Windows SSL better), falls back to urllib.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, */*",
    }

    if _USE_REQUESTS:
        try:
            resp = _requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except _requests.exceptions.HTTPError as e:
            print(f"  HTTP error fetching {url}: {e}")
            return None
        except _requests.exceptions.RequestException as e:
            print(f"  Network error fetching {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"  JSON parse error from {url}: {e}")
            return None
    else:
        import urllib.error, urllib.request
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"  HTTP error {e.code} fetching {url}")
            return None
        except urllib.error.URLError as e:
            print(f"  Network error fetching {url}: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            print(f"  JSON parse error from {url}: {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# PARSER
# ─────────────────────────────────────────────────────────────────────────────

def _parse_game(raw_game: dict) -> dict:
    """
    Normalise one raw CrookedFence game entry into a clean, consistent dict.

    Actual schema (confirmed from live data.json):
      away/home      -- team abbr string (e.g. "TOR", "BOS")
      stadium        -- venue name string
      game_time      -- "1:35 PM ET"
      signal         -- "hitter" / "hitter_strong" / "neutral" / "pitcher" / "pitcher_strong"
      hr_edge        -- int (% adjustment, e.g. 37)
      runs_edge      -- int (% adjustment, e.g. 19)
      roof           -- "open" / "closed" / "retractable"
      stadium_profile -- {name, city, lf_ft, cf_ft, rf_ft}
      away_pitcher   -- {name, throws, hr9, goao, era, whip, ip, k9, bb9, profile}
      home_pitcher   -- same
      weather        -- {temp_f, wind_speed_mph, wind_from, wind_effect, humidity_pct,
                          pressure_hpa, precip_pct, source}
      edge           -- {hr_pct, runs_pct}   (same values as hr_edge/runs_edge)
      odds           -- {total, total_price, home_ml, away_ml, book}
      value          -- {direction, edge_runs, confidence, reason}
      delay_risk     -- "LOW" / "HIGH"
    """
    wx    = raw_game.get("weather") or {}
    dims  = raw_game.get("stadium_profile") or {}
    away_p = raw_game.get("away_pitcher") or {}
    home_p = raw_game.get("home_pitcher") or {}
    value  = raw_game.get("value") or {}
    odds   = raw_game.get("odds") or {}

    return {
        # Identification — away/home are plain abbr strings in this schema
        "away_team":       raw_game.get("away"),
        "home_team":       raw_game.get("home"),
        "venue":           raw_game.get("stadium"),
        "game_time_et":    raw_game.get("game_time"),
        "roof":            raw_game.get("roof", "open"),
        "delay_risk":      raw_game.get("delay_risk"),

        # Wind/park signal
        "signal":          raw_game.get("signal", "unknown"),

        # Headline edge numbers (top-level fields, confirmed)
        "hr_edge_pct":     raw_game.get("hr_edge"),
        "runs_edge_pct":   raw_game.get("runs_edge"),

        # Weather detail
        "temp_f":          wx.get("temp_f"),
        "wind_mph":        wx.get("wind_speed_mph"),
        "wind_dir_label":  wx.get("wind_from"),     # e.g. "WSW", "N", "SSW"
        "wind_effect":     wx.get("wind_effect"),   # OUT / IN / IN-CROSS / OUT-CROSS / ROOF CLOSED
        "humidity_pct":    wx.get("humidity_pct"),
        "precip_pct":      wx.get("precip_pct"),
        "pressure_hpa":    wx.get("pressure_hpa"),

        # Stadium dimensions
        "lf_ft":           dims.get("lf_ft"),
        "cf_ft":           dims.get("cf_ft"),
        "rf_ft":           dims.get("rf_ft"),

        # Away starter
        "away_pitcher":    away_p.get("name"),
        "away_hand":       away_p.get("throws"),
        "away_hr9":        away_p.get("hr9"),
        "away_era":        away_p.get("era"),
        "away_whip":       away_p.get("whip"),
        "away_goao":       away_p.get("goao"),
        "away_k9":         away_p.get("k9"),
        "away_ip":         away_p.get("ip"),
        "away_profile":    away_p.get("profile"),

        # Home starter
        "home_pitcher":    home_p.get("name"),
        "home_hand":       home_p.get("throws"),
        "home_hr9":        home_p.get("hr9"),
        "home_era":        home_p.get("era"),
        "home_whip":       home_p.get("whip"),
        "home_goao":       home_p.get("goao"),
        "home_k9":         home_p.get("k9"),
        "home_ip":         home_p.get("ip"),
        "home_profile":    home_p.get("profile"),

        # Market + WindOut value model (for reverse-engineering dataset)
        "market_total":    odds.get("total"),
        "total_price":     odds.get("total_price"),
        "home_ml":         odds.get("home_ml"),
        "away_ml":         odds.get("away_ml"),
        "cf_direction":    value.get("direction"),   # "OVER" / "UNDER" / "SKIP"
        "cf_confidence":   value.get("confidence"),  # "HIGH" / "MEDIUM" / "LOW" / "NONE"
        "cf_edge_runs":    value.get("edge_runs"),   # e.g. 1.8 (runs above market total)
        "cf_reason":       value.get("reason"),
    }


def _parse_raw(raw: dict | list) -> list[dict]:
    """
    Handle the CrookedFence envelope: {"date": ..., "generated_at": ..., "games": [...]}
    Also handles bare list format as a fallback.
    """
    if isinstance(raw, list):
        games_list = raw
    elif isinstance(raw, dict):
        games_list = raw.get("games") or raw.get("data") or raw.get("mlb") or []
        # Last resort: if values are all dicts, treat as game map
        if not games_list and all(isinstance(v, dict) for v in raw.values()):
            games_list = list(raw.values())
    else:
        games_list = []

    return [_parse_game(g) for g in games_list if isinstance(g, dict)]


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL LABEL HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _signal_label(signal: str) -> str:
    """Return a short display string for a CrookedFence signal value."""
    mapping = {
        "hitter_strong": "HITTER STRONG",
        "hitter":        "HITTER",
        "neutral":       "NEUTRAL",
        "pitcher":       "PITCHER",
        "pitcher_strong":"PITCHER STRONG",
        "roof":          "ROOF CLOSED",
    }
    return mapping.get((signal or "").lower().replace(" ", "_"), signal.upper() if signal else "?")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_wind_edge(sport: str, date: str):
    """
    Fetch CrookedFence data.json, parse it, and write two output files:
      data/mlb/YYYY-MM-DD/wind_edge.json   -- clean per-game edge data for build_prompt.py
      data/mlb/crookedfence_archive/YYYY-MM-DD_raw.json  -- raw archive for reverse-engineering
    """
    print(f"  Fetching CrookedFence wind/park edge data for {date} ...")

    # ── Fetch raw JSON ─────────────────────────────────────────────────────────
    raw = _fetch_json(CROOKEDFENCE_URL)
    if raw is None:
        print("  ERROR: Could not fetch crookedfence.org/data.json")
        print("  Pipeline will continue — wind_edge block will be absent from prompts today.")
        sys.exit(1)

    # ── Archive raw JSON (for reverse-engineering dataset) ─────────────────────
    archive_dir = PROJECT_ROOT / "data" / sport / "crookedfence_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{date}_raw.json"
    archive_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    print(f"  Raw archive saved: {archive_path.relative_to(PROJECT_ROOT)}")

    # ── Parse into clean game records ─────────────────────────────────────────
    games = _parse_raw(raw)

    if not games:
        print("  WARNING: Parsed 0 games from data.json — schema may have changed.")
        print("  Inspect the raw archive file to check the JSON structure.")
        # Write an empty file so build_prompt.py doesn't crash on missing file
        out_dir = PROJECT_ROOT / "data" / sport / date
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "wind_edge.json").write_text("[]", encoding="utf-8")
        sys.exit(1)

    # ── Write clean output ─────────────────────────────────────────────────────
    out_dir  = PROJECT_ROOT / "data" / sport / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "wind_edge.json"
    out_path.write_text(json.dumps(games, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Print summary table ────────────────────────────────────────────────────
    print(f"\n  {'Game':<28} {'Signal':<16} {'HR Edge':>8} {'Runs Edge':>10}  Wind")
    print(f"  {'-'*28} {'-'*16} {'-'*8} {'-'*10}  {'-'*20}")

    for g in games:
        away   = (g.get("away_team") or "?")[:3].upper()
        home   = (g.get("home_team") or "?")[:3].upper()
        label  = f"{away} @ {home}"
        sig    = _signal_label(g.get("signal", ""))
        hr     = g.get("hr_edge_pct")
        runs   = g.get("runs_edge_pct")
        wind   = g.get("wind_mph")
        effect = g.get("wind_effect") or ""
        temp   = g.get("temp_f")

        hr_str   = f"{hr:+}%"   if hr   is not None else "  n/a"
        runs_str = f"{runs:+}%" if runs is not None else "  n/a"
        wx_str   = f"{wind}mph {effect} {temp}F" if wind is not None else "n/a"

        print(f"  {label:<28} {sig:<16} {hr_str:>8} {runs_str:>10}  {wx_str}")

    print(f"\n  Wind edge data saved: {out_path.relative_to(PROJECT_ROOT)}  ({len(games)} games)")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch CrookedFence wind/park edge data and save for prompt injection."
    )
    parser.add_argument("--sport", default="mlb", help="Sport code (default: mlb)")
    parser.add_argument(
        "--date", default=None,
        help="Target date YYYY-MM-DD (default: today US Eastern Time)"
    )
    args = parser.parse_args()

    target_date = args.date or datetime.now(ET).strftime("%Y-%m-%d")
    fetch_wind_edge(sport=args.sport, date=target_date)

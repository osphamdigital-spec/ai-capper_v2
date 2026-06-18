#!/usr/bin/env python
"""
scripts/rotowire_expected_lineups.py

Scrape Rotowire's "expected lineups" page as SIDELINE data — not a primary
pipeline source. Its purpose is accuracy measurement: comparing what Rotowire
*expected* against what actually happened (MLB Stats API) and against the
recent-regulars pattern (lineup_tracker.txt). See scripts/compare_lineups.py.

Rotowire posts EXPECTED lineups in the morning and flips each to CONFIRMED
once the team officially announces. We capture both the names and the
expected/confirmed status flag.

IMPORTANT — project constraints:
  - This scrapes a third-party site. It is sideline/experimental only. If
    Rotowire changes its markup or blocks access, this script degrades
    gracefully (writes an empty file, exit 0) so it never breaks run_daily_2.
  - Never print non-ASCII to the Windows console (cp1252 crash). All player
    names go to the JSON file (utf-8); console output is ASCII-safe summaries.

Output:
    data/{sport}/{date}/rotowire_lineups.json
    [
      {
        "away_abbr": "TOR", "home_abbr": "BOS",
        "away_status": "expected" | "confirmed" | "unknown",
        "home_status": ...,
        "away_pitcher": {"name": "Trey Yesavage", "throws": "R"} | None,
        "home_pitcher": {...} | None,
        "away_order": [{"name": "George Springer", "pos": "DH", "bats": "R", "bat_order": 1}, ...],
        "home_order": [...]
      },
      ...
    ]

Usage:
    python scripts/rotowire_expected_lineups.py
    python scripts/rotowire_expected_lineups.py --date 2026-06-18
    python scripts/rotowire_expected_lineups.py --sport mlb --date 2026-06-18
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ROTOWIRE_URL = "https://www.rotowire.com/baseball/daily-lineups.php"

# A realistic browser User-Agent — Rotowire serves a basic page to plain clients.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Network resilience — mirror the pipeline's backoff philosophy.
_TIMEOUT_SECS   = 25
_RETRY_ATTEMPTS = 3
_RETRY_DELAYS   = [10, 30]   # seconds between attempts 1->2, 2->3

# Rotowire team abbreviation → games.json abbreviation (only the ones that differ).
# Verified live: Rotowire uses CWS for the White Sox; games.json uses CHW.
# Arizona is ARI on Rotowire; games.json uses AZ. All others match.
_ROTOWIRE_TO_GAMES = {
    "CWS": "CHW",
    "ARI": "AZ",
}


def _rotowire_abbr_to_games(abbr: str) -> str:
    """Translate a Rotowire team abbreviation to the games.json abbreviation."""
    return _ROTOWIRE_TO_GAMES.get(abbr, abbr)


# ─────────────────────────────────────────────────────────────────────────────
# NETWORK
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_html(date: str | None) -> str | None:
    """
    GET the Rotowire lineups page (optionally for a specific date) with retries.
    Returns the HTML string, or None if all attempts fail.
    """
    url = ROTOWIRE_URL
    params = {"date": date} if date else {}

    for attempt in range(_RETRY_ATTEMPTS):
        try:
            resp = requests.get(url, headers=_HEADERS, params=params, timeout=_TIMEOUT_SECS)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e:
            if attempt < _RETRY_ATTEMPTS - 1:
                wait = _RETRY_DELAYS[attempt]
                print(f"  Rotowire fetch failed (attempt {attempt + 1}/{_RETRY_ATTEMPTS}): {e}")
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Rotowire fetch failed after {_RETRY_ATTEMPTS} attempts: {e}")
                return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PARSING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _clean(text: str | None) -> str:
    """Strip and collapse whitespace; return '' for None."""
    return " ".join(text.split()) if text else ""


def _parse_status(side_container) -> str:
    """
    Read the expected/confirmed flag from a side's .lineup__status element.
    Rotowire uses class is-expected / is-confirmed and text 'Expected Lineup' /
    'Confirmed Lineup'. Returns 'expected', 'confirmed', or 'unknown'.
    """
    status_el = side_container.select_one(".lineup__status")
    if not status_el:
        return "unknown"
    classes = status_el.get("class") or []
    if "is-confirmed" in classes:
        return "confirmed"
    if "is-expected" in classes:
        return "expected"
    # Fall back to text inspection
    txt = _clean(status_el.get_text()).lower()
    if "confirm" in txt:
        return "confirmed"
    if "expect" in txt:
        return "expected"
    return "unknown"


def _parse_pitcher(side_container) -> dict | None:
    """
    Extract the probable starting pitcher from .lineup__player-highlight.
    Returns {"name": str, "throws": "L"|"R"|""} or None if absent.
    """
    ph = side_container.select_one(".lineup__player-highlight")
    if not ph:
        return None

    throws_el = ph.select_one(".lineup__throws")
    throws = _clean(throws_el.get_text()) if throws_el else ""

    # Prefer the anchor's full-name title attr. The container div's text includes
    # the throws letter (e.g. "Trey Yesavage R"), so the anchor is more reliable.
    name = ""
    anchor = ph.select_one(".lineup__player-highlight-name a")
    if anchor and anchor.has_attr("title"):
        name = _clean(anchor["title"])
    elif anchor:
        name = _clean(anchor.get_text())
    else:
        name_el = ph.select_one(".lineup__player-highlight-name")
        name = _clean(name_el.get_text()) if name_el else ""

    # Strip a trailing " L" / " R" / " S" hand token if it slipped in via text.
    if throws and name.endswith(f" {throws}"):
        name = name[: -(len(throws) + 1)].strip()

    if not name:
        return None
    return {"name": name, "throws": throws}


def _parse_order(side_container) -> list[dict]:
    """
    Parse the 9-batter order from a side's li.lineup__player rows.
    Uses the anchor title attribute for the FULL player name (the visible text
    is abbreviated, e.g. 'G. Springer'). bat_order is the 1-based DOM position.
    """
    order = []
    rows = side_container.select("li.lineup__player")
    for i, row in enumerate(rows, start=1):
        # Full name comes from the anchor's title attribute; fall back to text.
        a = row.select_one("a")
        if a and a.has_attr("title"):
            name = _clean(a["title"])
        elif a:
            name = _clean(a.get_text())
        else:
            name = _clean(row.get_text())

        pos  = _clean((row.select_one(".lineup__pos") or _Empty()).get_text())
        bats = _clean((row.select_one(".lineup__bats") or _Empty()).get_text())

        if not name:
            continue
        order.append({
            "name": name,
            "pos": pos,
            "bats": bats,
            "bat_order": i,
        })
    return order


class _Empty:
    """Tiny stand-in so .get_text() is always safe on a missing element."""
    @staticmethod
    def get_text(*args, **kwargs):
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PARSE
# ─────────────────────────────────────────────────────────────────────────────

def parse_rotowire(html: str) -> list[dict]:
    """
    Parse the Rotowire daily-lineups HTML into a list of game dicts.
    Returns [] if the page layout is unrecognized (graceful degradation).
    """
    soup = BeautifulSoup(html, "html.parser")
    boxes = soup.select(".lineup__box")
    if not boxes:
        print("  WARNING: no .lineup__box elements found -- Rotowire layout may have changed.")
        return []

    games = []
    for box in boxes:
        # Team abbreviations live in .lineup__abbr (away first, home second).
        abbrs = [_clean(x.get_text()) for x in box.select(".lineup__abbr")]
        if len(abbrs) < 2:
            # Skip non-game boxes (promos, etc.) rather than emit garbage.
            continue
        away_abbr = _rotowire_abbr_to_games(abbrs[0])
        home_abbr = _rotowire_abbr_to_games(abbrs[1])

        visit = box.select_one(".lineup__list.is-visit")
        home  = box.select_one(".lineup__list.is-home")
        if not visit or not home:
            print(f"  WARNING: {away_abbr}@{home_abbr} -- missing a lineup side container; skipping.")
            continue

        game = {
            "away_abbr":    away_abbr,
            "home_abbr":    home_abbr,
            "away_status":  _parse_status(visit),
            "home_status":  _parse_status(home),
            "away_pitcher": _parse_pitcher(visit),
            "home_pitcher": _parse_pitcher(home),
            "away_order":   _parse_order(visit),
            "home_order":   _parse_order(home),
        }
        games.append(game)

    return games


def fetch_rotowire_lineups(date: str | None = None, sport: str = "mlb") -> list[dict]:
    """
    Fetch + parse Rotowire lineups for the given date and write them to
    data/{sport}/{date}/rotowire_lineups.json. Returns the parsed list.

    Always writes a file (possibly an empty list) so downstream comparison
    code can rely on its presence. Never raises on network/parse failure.
    """
    print(f"Fetching Rotowire expected lineups (date={date or 'today'})...")
    html = _fetch_html(date)

    games: list[dict] = []
    if html:
        games = parse_rotowire(html)

    # Write output (even when empty) so compare_lineups.py has a stable target.
    if date:
        out_dir = PROJECT_ROOT / "data" / sport / date
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rotowire_lineups.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(games, f, indent=2, ensure_ascii=False)
        print(f"  Wrote {len(games)} matchup(s) -> {out_path.relative_to(PROJECT_ROOT)}")

    # ASCII-safe console summary (never print player names directly).
    for g in games:
        n_away = len(g["away_order"])
        n_home = len(g["home_order"])
        print(
            f"  {g['away_abbr']}@{g['home_abbr']}: "
            f"away={n_away}b ({g['away_status']}), "
            f"home={n_home}b ({g['home_status']})"
        )

    return games


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Rotowire expected lineups (sideline accuracy data)."
    )
    parser.add_argument("--sport", default="mlb", help="Sport code (default: mlb)")
    parser.add_argument("--date",  default=None,
                        help="Slate date YYYY-MM-DD (default: Rotowire's current day)")
    args = parser.parse_args()

    fetch_rotowire_lineups(date=args.date, sport=args.sport)
    # Always exit 0 — this is sideline data and must never break the pipeline.
    sys.exit(0)


if __name__ == "__main__":
    main()

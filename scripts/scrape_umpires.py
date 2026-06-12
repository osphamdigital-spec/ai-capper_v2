#!/usr/bin/env python
"""
scripts/scrape_umpires.py

Scrape MLB plate umpire assignments from Covers.com and write into the context
block of each game in data/mlb/[date]/games.json.

Primary method:   Text-based regex parsing (robust to CSS class changes)
Fallback/debug:   Selector-based element extraction (--debug flag)
Screenshot:       Always saved to debug_umpires.png

Three-pass text parser:
  Pass 1 — Split page into game blocks by detecting team abbreviation lines.
            Extract plate umpire from each block using HP label patterns.
  Pass 2 — Proximity scan: for unmatched games, attribute each HP mention
            to the nearest preceding team abbreviation in the full text.
  Pass 3 — If page uses a different format, the raw text print lets us
            identify the pattern and adjust the regex.

Usage:
    python scripts/scrape_umpires.py
    python scripts/scrape_umpires.py --date 2026-06-01
    python scripts/scrape_umpires.py --debug    # also attempt selector extraction

Modifies:
    data/mlb/[date]/games.json  -- writes context.umpire for each game
    Odds, pitcher, and weather fields are never touched.
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright
from tz_util import ET


COVERS_URL = "https://www.covers.com/sport/baseball/mlb/umpires"


# ─────────────────────────────────────────────────────────────────────────────
# ABBREVIATION TABLES
# ─────────────────────────────────────────────────────────────────────────────

# Covers may use different short codes from our internal standard.
# Only differences need to be listed; identical codes are pass-through.
COVERS_ABBR_MAP = {
    "ARI":  "AZ",    # Arizona Diamondbacks
    "CWS":  "CHW",   # Chicago White Sox
    "WSH":  "WAS",   # Washington Nationals
    "KCR":  "KC",    # Kansas City Royals
    "SFG":  "SF",    # San Francisco Giants
    "SDP":  "SD",    # San Diego Padres
    "TBR":  "TB",    # Tampa Bay Rays
    "TBD":  "TB",    # Tampa Bay (alt)
}

# City / nickname fragments (lowercase) → internal abbreviation.
# Used when Covers shows full team names instead of codes.
# Longer patterns are tried first so "chicago white sox" beats "chicago".
CITY_TO_ABBR = {
    "chicago white sox":   "CHW",
    "chicago cubs":        "CHC",
    "new york yankees":    "NYY",
    "new york mets":       "NYM",
    "los angeles dodgers": "LAD",
    "los angeles angels":  "LAA",
    "st. louis":           "STL",
    "kansas city":         "KC",
    "san francisco":       "SF",
    "san diego":           "SD",
    "tampa bay":           "TB",
    "minnesota":           "MIN",
    "milwaukee":           "MIL",
    "washington":          "WAS",
    "pittsburgh":          "PIT",
    "philadelphia":        "PHI",
    "cincinnati":          "CIN",
    "cleveland":           "CLE",
    "colorado":            "COL",
    "houston":             "HOU",
    "detroit":             "DET",
    "boston":              "BOS",
    "baltimore":           "BAL",
    "atlanta":             "ATL",
    "arizona":             "AZ",
    "seattle":             "SEA",
    "toronto":             "TOR",
    "texas":               "TEX",
    "miami":               "MIA",
    "oakland":             "OAK",
    "athletics":           "ATH",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_abbr(raw: str) -> str:
    """Normalise a raw Covers abbreviation to our internal standard."""
    return COVERS_ABBR_MAP.get(raw.strip().upper(), raw.strip().upper())


def find_teams_in_line(line: str, all_abbrs: set) -> list:
    """
    Return internal team abbreviations found in a single line of text.
    Checks token-level abbreviations first, then city/name substrings.
    """
    found = []
    line_lower = line.lower()

    # Token-level check: 2–4 uppercase letters that match a known abbreviation
    for token in re.findall(r'\b([A-Z]{2,4})\b', line.upper()):
        internal = norm_abbr(token)
        if internal in all_abbrs and internal not in found:
            found.append(internal)

    # Substring check: city/team name patterns (longer matches first)
    for pattern in sorted(CITY_TO_ABBR, key=len, reverse=True):
        if pattern in line_lower:
            abbr = CITY_TO_ABBR[pattern]
            if abbr in all_abbrs and abbr not in found:
                found.append(abbr)

    return found


# ─────────────────────────────────────────────────────────────────────────────
# TEXT PARSER (primary method)
# ─────────────────────────────────────────────────────────────────────────────

# HP label variations: "HP", "H.P.", "Home Plate", "Plate"
_HP_LABEL = r'(?:HP|H\.P\.|Home\s*Plate|Plate)'

# Name pattern: 2-3 capitalised words.
# Handles "Angel Hernandez", "CB Bucknor", "Phil Cuzzi Jr."
_NAME = r'([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){1,2})'

# HP label then name: "HP: Angel Hernandez"
HP_THEN_NAME = re.compile(
    rf'\b{_HP_LABEL}\b[\s:]+{_NAME}',
    re.MULTILINE | re.IGNORECASE,
)

# Name then HP label: "Angel Hernandez\nHP" or "Angel Hernandez (HP)"
NAME_THEN_HP = re.compile(
    rf'{_NAME}\s*[\n(]?\s*\b{_HP_LABEL}\b',
    re.MULTILINE | re.IGNORECASE,
)


def _extract_hp_from_block(block_text: str) -> str | None:
    """Try both HP patterns on a block of text. Returns umpire name or None."""
    m = HP_THEN_NAME.search(block_text)
    if m:
        return m.group(1).strip()
    m = NAME_THEN_HP.search(block_text)
    if m:
        return m.group(1).strip()
    return None


def parse_umpires_from_text(page_text: str, games: list) -> dict:
    """
    Primary parser. Returns { home_abbr: umpire_name_or_None }.

    Pass 1 — Block split:
        Walk through lines looking for home team abbreviations to mark game
        block boundaries. Extract HP umpire from each block.

    Pass 2 — Proximity scan:
        For any still-unmatched games, find all HP occurrences in the full text
        and attribute each to the nearest preceding home team abbreviation.

    Both passes are attempted regardless; Pass 2 fills any gaps from Pass 1.
    """
    home_abbrs = {g["home"]["abbr"] for g in games}
    all_abbrs  = home_abbrs | {g["away"]["abbr"] for g in games}

    results: dict = {}

    # ── Pass 1: Block split ───────────────────────────────────────────────────
    lines = page_text.splitlines()
    blocks: list = []      # list of (home_abbr, block_text)
    current_home:  str | None = None
    current_lines: list = []

    for line in lines:
        found = find_teams_in_line(line, all_abbrs)
        home_in_line = [a for a in found if a in home_abbrs]

        if home_in_line:
            # Save completed block before starting a new one
            if current_home is not None and current_lines:
                blocks.append((current_home, "\n".join(current_lines)))
            current_home  = home_in_line[0]
            current_lines = [line]
        elif current_home is not None:
            current_lines.append(line)

    # Save the final block
    if current_home is not None and current_lines:
        blocks.append((current_home, "\n".join(current_lines)))

    for home_abbr, block in blocks:
        umpire = _extract_hp_from_block(block)
        if umpire:
            results[home_abbr] = umpire

    # ── Pass 2: Proximity scan for unmatched games ────────────────────────────
    unmatched = home_abbrs - set(results.keys())
    if unmatched:
        for m in HP_THEN_NAME.finditer(page_text):
            candidate = m.group(1).strip()
            pos = m.start()
            text_before = page_text[:pos]

            # Find which home abbreviation appears most recently before this HP label
            best_abbr = None
            best_pos  = -1
            for abbr in home_abbrs:
                idx = text_before.rfind(abbr)
                if idx > best_pos:
                    best_pos  = idx
                    best_abbr = abbr

            if best_abbr and best_abbr not in results:
                results[best_abbr] = candidate

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SELECTOR EXTRACTION (debug only)
# ─────────────────────────────────────────────────────────────────────────────

async def extract_via_selectors(page) -> None:
    """
    Attempt selector-based extraction and print results.
    Does not return data — purely diagnostic to help identify CSS class names
    if the text parser needs refinement.
    """
    print("\n--- SELECTOR-BASED EXTRACTION (debug) ---")
    selectors = [
        "[class*='CoversUmpires']",
        "[class*='umpire']",
        "[class*='Umpire']",
        "[class*='CoversMatchups-matchup']",
        "[class*='matchupContainer']",
        "[class*='gameRow']",
        "table tbody tr",
    ]
    for sel in selectors:
        try:
            elements = await page.query_selector_all(sel)
            if elements and len(elements) > 1:
                print(f"  Matched '{sel}' — {len(elements)} element(s)")
                # Print first 3 elements to show structure
                for i, el in enumerate(elements[:3], 1):
                    text = await el.inner_text()
                    print(f"  [{i}] {text[:300].strip()}")
                    print()
                break
        except Exception:
            continue
    else:
        print("  No selector matched. Text-based parser is the only path.")
    print("--- END SELECTOR OUTPUT ---\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_umpires(date: str = None, debug: bool = False):
    """
    Scrape the Covers umpires page and write plate umpire context to games.json.
    """
    target_date = date or today_et()

    print(f"\n{'='*55}")
    print(f"  SCRAPE UMPIRES — MLB")
    print(f"  Slate date (US ET): {target_date}")
    print(f"{'='*55}\n")

    # ── Load games.json ───────────────────────────────────────────────────────
    project_root = Path(__file__).parent.parent
    games_path = project_root / "data" / "mlb" / target_date / "games.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        print("Run fetch_odds.py first.")
        sys.exit(1)

    with open(games_path) as f:
        games = json.load(f)

    home_abbrs = [g["home"]["abbr"] for g in games]
    print(f"Loaded {len(games)} games. Home teams: {', '.join(home_abbrs)}\n")

    # ── Playwright ───────────────────────────────────────────────────────────
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()

        # Navigate
        print("Step 1: Navigating to Covers umpires page...")
        try:
            await page.goto(
                COVERS_URL,
                wait_until="domcontentloaded",
                timeout=30_000,
            )
        except Exception as e:
            print(f"ERROR: Navigation failed — {e}")
            await browser.close()
            sys.exit(1)

        # Wait for JS render — 6 sec (slightly longer than odds page; umpires
        # page may have heavier initial load or lower cache priority)
        print("Step 2: Waiting 6 seconds for JavaScript to render...")
        await page.wait_for_timeout(6_000)

        # Screenshot — always saved; open debug_umpires.png to visually confirm
        # the umpire table loaded (vs. a CAPTCHA or blank page)
        screenshot_path = project_root / "debug_umpires.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Step 3: Screenshot saved → debug_umpires.png")
        print(f"        Open this file to confirm the table loaded correctly\n")

        # Optional selector debug
        if debug:
            await extract_via_selectors(page)

        # Get full page text (primary data source for parsing)
        print("Step 4: Extracting page text...")
        page_text = await page.inner_text("body")

        await browser.close()

    # ── Always print raw text so the parser can be validated ─────────────────
    # The exact Covers page format is unknown until first run. This output
    # lets you confirm what the parser received and diagnose any mismatches.
    print("\n" + "─" * 55)
    print("RAW PAGE TEXT (first 4 000 characters)")
    print("─" * 55)
    print(page_text[:4_000])
    if len(page_text) > 4_000:
        print(f"\n... [{len(page_text) - 4_000} more characters not shown]")
    print("─" * 55 + "\n")

    # ── Parse ─────────────────────────────────────────────────────────────────
    print("Step 5: Parsing plate umpire assignments...")
    umpire_map = parse_umpires_from_text(page_text, games)
    print(f"  Parser found assignments for {len(umpire_map)} game(s)\n")

    if umpire_map:
        for home, name in umpire_map.items():
            print(f"  {home}: {name}")
        print()

    # ── Write context ─────────────────────────────────────────────────────────
    print("Step 6: Writing umpire context to games.json...")
    fetched_at = now_utc()
    assigned   = 0
    unassigned = 0

    for game in games:
        home_abbr   = game["home"]["abbr"]
        umpire_name = umpire_map.get(home_abbr)

        umpire_entry = {
            "name":            umpire_name,
            "source":          "covers",
            "source_priority": 1,
            "fetched_at":      fetched_at,
            "status":          "assigned" if umpire_name else "unassigned",
        }

        # Preserve all existing context fields — pitcher and weather untouched
        game_ctx = game.get("context") or {}
        game_ctx["umpire"] = umpire_entry
        game["context"] = game_ctx

        if umpire_name:
            assigned += 1
        else:
            unassigned += 1

    # Save
    with open(games_path, "w") as f:
        json.dump(games, f, indent=2)

    print(f"Step 7: Saved → {games_path.relative_to(project_root)}\n")

    # ── Summary table ─────────────────────────────────────────────────────────
    print(f"{'='*55}")
    print(f"  UMPIRE SUMMARY")
    print(f"{'='*55}")
    print(f"  {'Matchup':<22}  {'Plate Umpire':<28}  Status")
    print(f"  {'-'*58}")

    for game in games:
        matchup     = f"{game['away']['abbr']} @ {game['home']['abbr']}"
        umpire_data = game["context"].get("umpire", {})
        name        = umpire_data.get("name") or "— not yet assigned —"
        status      = umpire_data.get("status", "?")
        flag        = "✓" if status == "assigned" else "·"
        print(f"  {flag} {matchup:<20}  {name:<28}  {status}")

    print(f"\n  Assigned:   {assigned}")
    print(f"  Unassigned: {unassigned}")
    print(f"  Total:      {len(games)}")

    if unassigned > 0:
        print(
            f"\n  NOTE: Unassigned is normal before MLB publishes the day's crew."
            f"\n  Assignments are typically posted the night before or morning of game day."
            f"\n  Re-run this script to pick them up once posted."
        )

    print(f"{'='*55}\n")

    # ── Parser diagnostic — if anything unmatched, show why ──────────────────
    unmatched_homes = {g["home"]["abbr"] for g in games} - set(umpire_map.keys())
    if unmatched_homes:
        print("PARSER DIAGNOSTIC — unmatched home teams:")
        print("  If umpires ARE visible in the raw text above but these games")
        print("  didn't match, the text format needs a new parsing strategy.")
        print(f"  Unmatched: {sorted(unmatched_homes)}")
        print()
        print("  To debug: look in the RAW PAGE TEXT above for one of these")
        print("  team names/abbreviations and find the umpire label near it.")
        print("  Then report back so we can adjust the regex.\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape MLB plate umpire assignments from Covers.com."
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time.",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Also attempt selector-based extraction and print matched elements.",
    )
    args = parser.parse_args()

    asyncio.run(scrape_umpires(date=args.date, debug=args.debug))

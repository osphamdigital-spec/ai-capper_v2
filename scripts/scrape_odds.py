#!/usr/bin/env python
"""
scripts/scrape_odds.py

Phase 1 scraper: MLB odds from covers.com
-------------------------------------------
Navigates to covers.com/sport/baseball/mlb/odds using Playwright (headless
Chromium), waits for JavaScript to render, then prints raw game data to screen.

No files are written. No formatting applied. This is the raw data inspection step.

Usage:
    python scripts/scrape_odds.py
    python scripts/scrape_odds.py --date 2026-06-01
    python scripts/scrape_odds.py --debug      # also dumps raw page HTML
"""

import asyncio
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo   # built-in from Python 3.9+

from playwright.async_api import async_playwright
from tz_util import ET


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# All slate dates use US Eastern Time — NEVER the local Australian date.
# See docs/TIMEZONE_STANDARD.md for why.

# URL template — sport is a parameter so this extends to NBA, NHL etc later.
# Each sport maps to a covers.com path segment.
SPORT_URL_SEGMENTS = {
    "mlb": "baseball/mlb",
    "nba": "basketball/nba",
    "nhl": "hockey/nhl",
    "nfl": "football/nfl",
}

COVERS_BASE = "https://www.covers.com/sport/{segment}/odds"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """
    Return today's date in US Eastern Time as a YYYY-MM-DD string.

    The owner is in Australia (AEST = ET + 14-15 hours), so 'today' in
    Australia is often 'tomorrow' in the US. We always want the US date
    because that's what covers.com and MLB.com show as the slate date.
    """
    return datetime.now(ET).strftime("%Y-%m-%d")


def build_url(sport: str) -> str:
    """Build the covers.com odds URL for the given sport code."""
    segment = SPORT_URL_SEGMENTS.get(sport.lower())
    if not segment:
        raise ValueError(
            f"Unknown sport '{sport}'. Valid options: {list(SPORT_URL_SEGMENTS.keys())}"
        )
    return COVERS_BASE.format(segment=segment)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCRAPER
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_odds(sport: str = "mlb", date: str = None, debug: bool = False):
    """
    Navigate to covers.com odds page and print raw game data.

    Args:
        sport:  Sport code. Default "mlb". Future: "nba", "nhl", "nfl".
        date:   Date override (YYYY-MM-DD). Default: today in US Eastern.
        debug:  If True, also dump raw page HTML for selector inspection.
    """

    target_date = date or today_et()
    url = build_url(sport)

    print(f"\n{'='*55}")
    print(f"  {sport.upper()} ODDS SCRAPER — covers.com")
    print(f"  Slate date (US ET): {target_date}")
    print(f"  URL: {url}")
    print(f"{'='*55}\n")

    async with async_playwright() as p:

        # Launch headless Chromium — runs in the background with no visible window.
        # Headless means no GUI, which is faster and needed for automation.
        browser = await p.chromium.launch(headless=True)

        # Create a browser context with a realistic desktop user-agent string.
        # Without this, some sites detect headless browsers and serve blank pages
        # or block the request entirely.
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},  # desktop-sized viewport
        )

        page = await context.new_page()

        # ── STEP 1: NAVIGATE ──────────────────────────────────────────────
        # wait_until="domcontentloaded" returns as soon as the HTML skeleton
        # is parsed — before JavaScript has run. We wait separately for JS below.
        print("Step 1: Navigating to covers.com...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        except Exception as e:
            print(f"ERROR: Navigation failed — {e}")
            await browser.close()
            return

        # ── STEP 2: WAIT FOR JAVASCRIPT TO RENDER ─────────────────────────
        # covers.com is a React app. After the HTML loads, React makes an API
        # call to fetch odds data and renders the table. We give it 5 seconds.
        # If odds aren't showing up, bumping this to 8 seconds often fixes it.
        print("Step 2: Waiting 5 seconds for JavaScript to render odds table...")
        await page.wait_for_timeout(5_000)

        # ── STEP 3: DEBUG DUMP (optional) ─────────────────────────────────
        # Pass --debug on the command line to see the raw HTML.
        # Useful when selectors break after a covers.com site update.
        if debug:
            print("\n--- RAW PAGE HTML (first 10,000 chars) ---")
            html = await page.content()
            print(html[:10_000])
            print("--- END HTML DUMP ---\n")

        # ── STEP 4: SCREENSHOT ────────────────────────────────────────────
        # Saves a screenshot of what the headless browser actually saw.
        # Open debug_odds.png after running to visually confirm the page loaded.
        screenshot_path = "debug_odds.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"Step 3: Screenshot saved → {screenshot_path}")
        print("        (open this file to confirm the odds table loaded)\n")

        # ── STEP 5: FIND GAME ROWS ────────────────────────────────────────
        # covers.com uses React with CSS class names that can change between
        # deploys. We try several selector patterns in order and use the first
        # one that returns results. This makes the scraper more resilient to
        # minor site changes.
        print("Step 4: Searching for game rows on the page...")

        selectors_to_try = [
            # Covers-specific class name patterns (most likely to match)
            ".covers-CoversMatchups-matchupContainer",
            ".covers-CoversOdds-game",
            # Partial class matching — works when covers appends hash suffixes
            "[class*='matchupContainer']",
            "[class*='CoversMatchups']",
            "[class*='gameRow']",
            "[class*='matchup-row']",
            # Generic fallback if covers uses a plain table layout
            "table tr[class*='game']",
            "table tbody tr",
        ]

        game_elements = []
        used_selector = None

        for selector in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                # Require more than 1 match — single match is probably a header row
                if elements and len(elements) > 1:
                    game_elements = elements
                    used_selector = selector
                    break
            except Exception:
                continue  # try the next selector if this one throws an error

        # ── HANDLE: NO GAME ROWS FOUND ────────────────────────────────────
        # If nothing matched, print the full page text so we can manually
        # identify what selector covers.com is actually using right now.
        if not game_elements:
            print("\nWARNING: No game rows found with any known selector.")
            print("Possible reasons:")
            print("  1. covers.com changed its CSS class names (run with --debug to see HTML)")
            print("  2. The headless browser was detected and blocked")
            print("  3. No MLB games are scheduled for today")
            print("\nFull page text dump (to find the right selector manually):\n")
            print("-" * 55)
            body_text = await page.inner_text("body")
            print(body_text)
            print("-" * 55)
            await browser.close()
            return

        # ── STEP 6: PRINT RAW GAME DATA ───────────────────────────────────
        # inner_text() returns the visible text of each element — the same
        # text a human would see in the browser. Newlines and tabs are preserved.
        # This is intentionally raw/messy. We'll parse it properly in Phase 2.
        print(f"Found {len(game_elements)} game elements  (selector: '{used_selector}')\n")
        print("=" * 55)
        print("RAW GAME DATA — unformatted, directly from page")
        print("=" * 55)

        for i, elem in enumerate(game_elements, start=1):
            print(f"\n--- GAME {i} ---")
            try:
                text = await elem.inner_text()
                print(text)
            except Exception as e:
                print(f"  Could not read element: {e}")

        # ── BONUS: HTML OF FIRST GAME ELEMENT ─────────────────────────────
        # Printing the raw HTML of the first game element gives us the exact
        # class names and structure we need when writing precise selectors later.
        print("\n\n--- HTML OF FIRST GAME ELEMENT (for writing precise selectors later) ---")
        try:
            first_html = await game_elements[0].inner_html()
            print(first_html[:3_000])
        except Exception as e:
            print(f"Could not read first element HTML: {e}")

        await browser.close()

    print("\n=== SCRAPE COMPLETE ===\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape MLB odds from covers.com — Phase 1 (raw output only)"
    )
    parser.add_argument(
        "--sport", default="mlb",
        help="Sport code: mlb, nba, nhl, nfl  (default: mlb)"
    )
    parser.add_argument(
        "--date", default=None,
        help="Override target date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Also dump raw page HTML to screen (for selector debugging)"
    )
    args = parser.parse_args()

    asyncio.run(scrape_odds(sport=args.sport, date=args.date, debug=args.debug))

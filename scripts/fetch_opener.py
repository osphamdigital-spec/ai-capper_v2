#!/usr/bin/env python
"""
scripts/fetch_opener.py

Fetch true opening lines (ML, RL, O/U) from Covers.com and write them into
games.json as odds.covers_opener for each matched game.

Why: TheOddsAPI opening_snapshot is our FIRST daily fetch (morning-of).
Covers posts lines when books first open them -- often 1-3 days before game day.
The true opener is what sharp money is measured against. A line that moved
from Covers open -108 to current -125 is a 17-point move; our morning fetch
at -118 only shows 7 points of that story.

Data structure: Covers embeds ALL opening data in Cell 0 of each table row.
Both team abbrs (STL, MIN) and opening prices (-101, -109) appear inline in
that cell. Current per-book prices are in cells 1-4. Uses Playwright to render
JS-populated tables.
Covers.com robots.txt: /sport/baseball/mlb/odds is not disallowed.

Usage:
    python scripts/fetch_opener.py
    python scripts/fetch_opener.py --date 2026-06-14 --sport mlb
    python scripts/fetch_opener.py --dry-run   (print parsed data, don't write)

Reads:
    data/{sport}/{date}/games.json

Writes:
    data/{sport}/{date}/games.json  -- adds odds.covers_opener per matched game

Requires: playwright
    pip install playwright
    python -m playwright install chromium
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR  = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

COVERS_URL = "https://www.covers.com/sport/baseball/mlb/odds?oddsFormat=american"

# Map Covers team abbrs → our internal abbrs where they differ.
# Covers uses standard MLB codes; we inherited some legacy variants from TheOddsAPI.
COVERS_ABBR_REMAP = {
    "WSH": "WAS",   # Covers WSH → our WAS (Washington Nationals)
    "CWS": "CHW",   # Covers CWS → our CHW (Chicago White Sox)
    "ARI": "AZ",    # Covers ARI → our AZ  (Arizona Diamondbacks)
}

# All abbreviations that can appear in Covers cell text (before remapping).
VALID_ABBRS = {
    "NYY", "BOS", "TOR", "TB",  "BAL",
    "CWS", "CLE", "DET", "KC",  "MIN",
    "HOU", "LAA", "ATH", "OAK", "SEA", "TEX",
    "ATL", "MIA", "NYM", "PHI", "WSH",
    "CHC", "CIN", "MIL", "PIT", "STL",
    "ARI", "COL", "LAD", "SD",  "SF",
    # Also accept our internal variants in case Covers ever uses them
    "WAS", "CHW", "AZ",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from tz_util import ET
        return datetime.now(ET).strftime("%Y-%m-%d")
    except ImportError:
        from datetime import timedelta
        et = timezone(timedelta(hours=-4))
        return datetime.now(et).strftime("%Y-%m-%d")


def _remap_abbr(abbr: str) -> str:
    """Normalise a Covers team abbr to our internal abbreviation."""
    return COVERS_ABBR_REMAP.get(abbr, abbr)


def _parse_cell0_ml(cell_text: str) -> dict | None:
    """
    Parse the combined game-info cell from a Covers ML/RL table row.

    Covers Cell 0 structure (after stripping whitespace):
        TODAY,  14:10
        STL
        M. Liberatore  (L, 4.50)
        MIN
        C. Prielipp  (L, 5.23)
        -101          <- opening away price
        -109          <- opening home price
        Projections
        Line Movement
        Picks
        Matchup

    Returns {away_abbr, home_abbr, open_away, open_home} or None if unparseable.
    """
    lines = [ln.strip() for ln in cell_text.replace("\xa0", " ").split("\n")]
    lines = [ln for ln in lines if ln]

    team_abbrs = []
    odds_vals  = []
    found_projections = False

    for ln in lines:
        if ln.lower().startswith("projection"):
            found_projections = True
            break  # everything after this is navigation noise

        # Team abbr: short uppercase token that matches a known abbr
        if ln in VALID_ABBRS:
            team_abbrs.append(_remap_abbr(ln))
            continue

        # Opening price: American odds integer (-180, +105, etc.) on its own line
        # Must be 3-4 digits with optional +/- sign; range sanity check.
        m = re.match(r"^([+-]?\d{3,4})$", ln.replace("−", "-"))
        if m:
            val = int(m.group(1))
            if 100 <= abs(val) <= 1000:
                odds_vals.append(val)

    if len(team_abbrs) < 2:
        return None  # couldn't identify both teams

    return {
        "away_abbr": team_abbrs[0],
        "home_abbr": team_abbrs[1],
        "open_away": odds_vals[0] if len(odds_vals) >= 1 else None,
        "open_home": odds_vals[1] if len(odds_vals) >= 2 else None,
    }


def _parse_cell0_total(cell_text: str) -> dict | None:
    """
    Parse the game-info cell from a Covers Totals table row.

    Cell 0 in the Totals table has the same team block as ML/RL, plus
    opening total line values embedded as 'o X.X' / 'u X.X' tokens.

    Example embedded section:
        o 8.5
        o 8.5
        o 8.5
        u 8.5
        u 8.5
        u 8.5

    We take the FIRST 'o X.X' as the opening over line.
    Returns {away_abbr, home_abbr, line_open} or None.
    """
    lines = [ln.strip() for ln in cell_text.replace("\xa0", " ").split("\n")]
    lines = [ln for ln in lines if ln]

    team_abbrs = []
    line_open  = None

    for ln in lines:
        if ln in VALID_ABBRS:
            team_abbrs.append(_remap_abbr(ln))
            continue

        # Opening total: 'o 8.5', 'o 9.0' etc.
        m = re.match(r"^o\s+(\d{1,2}(?:\.\d)?)$", ln, re.IGNORECASE)
        if m and line_open is None:
            line_open = float(m.group(1))

    if len(team_abbrs) < 2:
        return None

    return {
        "away_abbr": team_abbrs[0],
        "home_abbr": team_abbrs[1],
        "line_open": line_open,
    }


def _parse_total_book_cell(cell_text: str) -> tuple[float | None, int | None, int | None]:
    """
    Parse one sportsbook cell from the Totals table.
    Returns (line, over_price, under_price).

    Cell structure (from Betway example):
        o 9.0
        -104
        1.96
        20/21
        u 9.0
        -118
        1.85
        11/13

    We extract: line from 'o X.X', over price from the integer after 'o X.X',
    under price from the integer after 'u X.X'.
    """
    # Normalise and split
    text = cell_text.replace("\xa0", " ")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    over_line  = None
    over_price = None
    under_price = None
    mode = None  # "over" | "under"

    for ln in lines:
        # 'o X.X' line starts the over block
        m = re.match(r"^o\s+(\d{1,2}(?:\.\d)?)$", ln, re.IGNORECASE)
        if m:
            over_line = float(m.group(1))
            mode = "over"
            continue

        # 'u X.X' line starts the under block
        m = re.match(r"^u\s+(\d{1,2}(?:\.\d)?)$", ln, re.IGNORECASE)
        if m:
            mode = "under"
            continue

        # American odds integer on its own line
        m = re.match(r"^([+-]?\d{3,4})$", ln.replace("−", "-"))
        if m:
            val = int(m.group(1))
            if 100 <= abs(val) <= 1000:
                if mode == "over" and over_price is None:
                    over_price = val
                elif mode == "under" and under_price is None:
                    under_price = val

    return over_line, over_price, under_price


# ─────────────────────────────────────────────────────────────────────────────
# TABLE SCRAPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_table_rows(page, table_id: str) -> list:
    """
    Read all data rows from a Covers table via JavaScript.
    Returns list of lists: [[cell0_text, cell1_text, ...], ...].
    Skips rows with 0 cells (separator rows).
    """
    try:
        # Use state="attached" not default "visible" — RL/TT tables are inside
        # CSS-hidden tab containers (display:none parent) so they're never "visible",
        # but their cells ARE in the DOM and have content.
        page.wait_for_selector(f"#{table_id} tbody tr td", state="attached", timeout=10000)
    except Exception:
        print(f"    WARNING: #{table_id} has no rows after 10s")
        return []

    return page.evaluate(f"""
        () => {{
            const table = document.getElementById('{table_id}');
            if (!table) return [];
            const rows = table.querySelectorAll('tbody tr');
            return Array.from(rows)
                .map(row => Array.from(row.querySelectorAll('td')).map(c => c.innerText))
                .filter(cells => cells.length > 0);
        }}
    """)


def scrape_ml_table(page) -> dict:
    """
    Parse Covers Moneyline table.
    Returns {(away_abbr, home_abbr): {away_open, home_open}}.
    """
    results = {}
    rows = _get_table_rows(page, "moneyline-table")
    for cells in rows:
        if not cells:
            continue
        parsed = _parse_cell0_ml(cells[0])
        if not parsed:
            continue
        key = (parsed["away_abbr"], parsed["home_abbr"])
        entry = {
            "away_open": parsed.get("open_away"),
            "home_open": parsed.get("open_home"),
        }
        results[key] = entry
        print(f"    ML  {key[0]}@{key[1]}: "
              f"away_open={entry['away_open']}  home_open={entry['home_open']}")
    return results


def _parse_rl_book_cell(cell_text: str) -> tuple[int | None, int | None]:
    """
    Parse one book column cell from the Covers RL table.
    Structure (e.g. bet365 for STL -1.5):
        -1.5   <- point value (away)
        +125   <- away price
        2.25   <- decimal (ignored)
        5/4    <- fractional (ignored)
        +1.5   <- point value (home)
        -165   <- home price
    Returns (away_price, home_price).
    """
    lines = [ln.strip() for ln in cell_text.replace("\xa0", " ").split("\n") if ln.strip()]
    mode  = None   # "away" | "home"
    away_price = None
    home_price = None

    for ln in lines:
        # Point value lines: '-1.5' / '+1.5'
        if re.match(r"^[+-]?1\.5$", ln):
            mode = "away" if ln.startswith("-") else "home"
            continue
        # American odds integer
        m = re.match(r"^([+-]?\d{3,4})$", ln.replace("−", "-"))
        if m:
            val = int(m.group(1))
            if 100 <= abs(val) <= 1000:
                if mode == "away" and away_price is None:
                    away_price = val
                elif mode == "home" and home_price is None:
                    home_price = val

    return away_price, home_price


def scrape_rl_table(page) -> dict:
    """
    Parse Covers Run Line (spread) table.

    Note: Covers does NOT expose opening RL prices in cell 0 — only the ±1.5
    point values (which never change). Current RL prices are in cell 1 (first
    sportsbook column). We store these as 'current' prices, not 'open'.
    The point value is always -1.5 (away) / +1.5 (home) — not stored.

    Returns {(away_abbr, home_abbr): {away_price_current, home_price_current}}.
    """
    results = {}
    rows = _get_table_rows(page, "spread-table")
    for cells in rows:
        if not cells:
            continue
        # Teams are in cell 0; prices are in cell 1 (first book)
        parsed = _parse_cell0_ml(cells[0])
        if not parsed:
            continue
        key = (parsed["away_abbr"], parsed["home_abbr"])

        away_price, home_price = (None, None)
        if len(cells) > 1:
            away_price, home_price = _parse_rl_book_cell(cells[1])

        entry = {
            "away_price_current": away_price,
            "home_price_current": home_price,
        }
        results[key] = entry
        print(f"    RL  {key[0]}@{key[1]}: "
              f"away_curr={away_price}  home_curr={home_price}")
    return results


def scrape_total_table(page) -> dict:
    """
    Parse Covers Totals table.
    Opening total LINE is in Cell 0 ('o 8.5' etc).
    Current over/under price comes from Cell 1 (first sportsbook).
    Returns {(away_abbr, home_abbr): {line_open, over_price_open, under_price_open}}.
    Note: Covers does not show opening over/under PRICES -- only the opening line.
    Current book prices are stored as current_{field} for context.
    """
    results = {}
    rows = _get_table_rows(page, "total-table")
    for cells in rows:
        if not cells:
            continue
        parsed = _parse_cell0_total(cells[0])
        if not parsed:
            continue
        key = (parsed["away_abbr"], parsed["home_abbr"])

        # Current line + price from cell 1 (first book listed = bet365 or similar)
        curr_line, over_price, under_price = (None, None, None)
        if len(cells) > 1:
            curr_line, over_price, under_price = _parse_total_book_cell(cells[1])

        entry = {
            "line_open":       parsed.get("line_open"),
            "line_current":    curr_line,     # best available current line
            "over_price":      over_price,    # current over price (one book)
            "under_price":     under_price,   # current under price (one book)
        }
        results[key] = entry
        print(f"    TT  {key[0]}@{key[1]}: "
              f"open={entry['line_open']}  curr={entry['line_current']}  "
              f"O={entry['over_price']}  U={entry['under_price']}")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch true opening lines from Covers.com and write to games.json."
    )
    parser.add_argument("--date",    default=None,  help="Slate date YYYY-MM-DD (default: today ET)")
    parser.add_argument("--sport",   default="mlb", help="Sport code (default: mlb)")
    parser.add_argument("--dry-run", action="store_true", help="Print parsed data; don't write to games.json")
    args = parser.parse_args()

    date  = args.date or today_et()
    sport = args.sport

    games_path = PROJECT_ROOT / "data" / sport / date / "games.json"
    if not games_path.exists():
        print(f"\n  ERROR: games.json not found: {games_path}")
        print(f"  Run fetch_odds.py first.")
        sys.exit(1)

    print(f"\nfetch_opener.py  sport={sport}  date={date}")
    print(f"  games.json : {games_path.relative_to(PROJECT_ROOT)}")
    print(f"  Source     : covers.com/sport/baseball/mlb/odds")

    # ── Playwright: load Covers, force American odds format ───────────────────
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx  = browser.new_context(locale="en-US")
        page = ctx.new_page()

        print(f"\n  Loading page (headless Chromium)...")
        page.goto(COVERS_URL, wait_until="domcontentloaded", timeout=30000)

        print(f"  Waiting for tables...")
        try:
            page.wait_for_selector("#moneyline-table tbody tr td", timeout=20000)
            print(f"  Tables ready.")
        except Exception:
            print(f"  WARNING: Tables may not be loaded. Proceeding.")

        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"\n  Parsing Moneyline table...")
        ml_data = scrape_ml_table(page)

        print(f"\n  Parsing Run Line table...")
        rl_data = scrape_rl_table(page)

        print(f"\n  Parsing Totals table...")
        tt_data = scrape_total_table(page)

        browser.close()

    print(f"\n  ML games : {len(ml_data)}  |  RL : {len(rl_data)}  |  TT : {len(tt_data)}")

    all_keys = set(ml_data) | set(rl_data) | set(tt_data)
    if not all_keys:
        print("\n  ERROR: No games parsed. Page structure may have changed.")
        sys.exit(1)

    if args.dry_run:
        print(f"\n  DRY RUN — not writing to games.json")
        return

    # ── Match to games.json and write covers_opener ───────────────────────────
    games     = json.loads(games_path.read_text(encoding="utf-8"))
    matched   = 0
    unmatched = []

    for game in games:
        away_abbr = game["away"]["abbr"]
        home_abbr = game["home"]["abbr"]
        key = (away_abbr, home_abbr)

        ml = ml_data.get(key, {})
        rl = rl_data.get(key, {})
        tt = tt_data.get(key, {})

        if not ml and not rl and not tt:
            unmatched.append(f"{away_abbr}@{home_abbr}")
            continue

        game.setdefault("odds", {})["covers_opener"] = {
            "source":     "covers.com",
            "fetched_at": fetched_at,
            "moneyline": {
                "away_open": ml.get("away_open"),
                "home_open": ml.get("home_open"),
            } if ml else None,
            "runline": {
                # Opening RL price not available from Covers — storing current book price
                "away_price_current": rl.get("away_price_current"),
                "home_price_current": rl.get("home_price_current"),
            } if rl else None,
            "total": {
                "line_open":    tt.get("line_open"),
                "line_current": tt.get("line_current"),
                "over_price":   tt.get("over_price"),
                "under_price":  tt.get("under_price"),
            } if tt else None,
        }
        matched += 1

    games_path.write_text(
        json.dumps(games, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n  Matched  : {matched}/{len(games)} games")
    if unmatched:
        print(f"  Unmatched: {', '.join(unmatched)}")
    print(f"  Written  : {games_path.relative_to(PROJECT_ROOT)}")
    print(f"\nDone.\n")


if __name__ == "__main__":
    main()

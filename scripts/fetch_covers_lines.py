#!/usr/bin/env python
"""
scripts/fetch_covers_lines.py

Fetch opening run-line/total prices and movement history from Covers.com,
then merge into games.json under a new 'covers_lines' key.

Covers.com serves different sportsbooks depending on country:
  AU IP -> bet365, Betway, William Hill  (what the operator sees)
  US IP -> Kalshi, Polymarket (prediction markets — not sportsbooks)

The linehistorybrick endpoint's countryCode parameter must be 'au' to
request bet365-style data. This script is designed to run from Australia.

Usage:
    # Dry-run: parse ONE game, print JSON, do NOT write to games.json
    python scripts/fetch_covers_lines.py --dry-run

    # Full run: all matched games, write to games.json
    python scripts/fetch_covers_lines.py

    # Specific date
    python scripts/fetch_covers_lines.py --date 2026-06-13

Requires Python 3.12+ with playwright and beautifulsoup4:
    playwright install chromium
    pip install beautifulsoup4 playwright
"""

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from tz_util import ET

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Book IDs as used by Covers in the linehistorybrick HTML (data-book-id attribute)
BOOK_IDS = {
    "bet365":      "1",
    "betway":      "14",
    "williamhill": "7",
    # BetVictor (id=10) is skipped — not commonly available
}

# Covers team abbreviations that differ from our internal system
# Only 3 real discrepancies — do NOT expand this into a full parallel map
COVERS_ABBR_REMAP = {"WSH": "WAS", "CWS": "CHW", "ARI": "AZ"}

COVERS_ODDS_URL = (
    "https://www.covers.com/sport/baseball/mlb/odds?oddsFormat=american"
)
# countryCode=au ensures bet365/Betway/William Hill data (not US prediction markets)
COVERS_HISTORY_URL = (
    "https://www.covers.com/sport/matchupodds/linehistorybrick"
    "?gameId={game_id}"
    "&location=covers_game_odds"
    "&countryCode=au"
    "&stateProvince="
    "&oddsFormat=american"
    "&betType=spread"
)


def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Playwright — render Covers odds page, extract gameIds + team abbrs
# ─────────────────────────────────────────────────────────────────────────────

def fetch_covers_game_ids() -> list[dict]:
    """
    Render the Covers odds page and return a list of:
        {"game_id": "368802", "away_abbr": "MIA", "home_abbr": "PIT"}

    game_id is Covers' internal numeric ID (used in linehistorybrick URL).
    Team abbrs have already been remapped via COVERS_ABBR_REMAP.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx  = browser.new_context(locale="en-US")
        page = ctx.new_page()
        page.goto(COVERS_ODDS_URL, wait_until="domcontentloaded", timeout=30000)
        # Wait until at least one game row is present
        page.wait_for_selector(
            "tr.oddsGameRow", state="attached", timeout=20000
        )

        games = page.evaluate("""
            () => {
                const REMAP = { "WSH": "WAS", "CWS": "CHW", "ARI": "AZ" };
                const remap = a => REMAP[a] || a;
                const seen = new Set();
                const results = [];

                // Game rows have class "oddsGameRow" — they appear in multiple tables
                // (moneyline, spread, total) so deduplicate by game_id.
                for (const row of document.querySelectorAll('tr.oddsGameRow')) {
                    // Game ID from the matchup link: /sport/baseball/mlb/matchup/368802
                    const link = row.querySelector('a[href*="/matchup/"]');
                    if (!link) continue;
                    const parts = link.href.split('/matchup/');
                    const gameId = parts.length > 1 ? parts[1] : null;
                    if (!gameId || seen.has(gameId)) continue;
                    seen.add(gameId);

                    // Team abbreviations are in <strong> inside .away-cell and .home-cell
                    const awayStr = row.querySelector('.away-cell strong');
                    const homeStr = row.querySelector('.home-cell strong');
                    if (!awayStr || !homeStr) continue;

                    results.push({
                        game_id:   gameId,
                        away_abbr: remap(awayStr.innerText.trim()),
                        home_abbr: remap(homeStr.innerText.trim()),
                    });
                }
                return results;
            }
        """)
        browser.close()

    return games


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: urllib — fetch linehistorybrick HTML for one game
# ─────────────────────────────────────────────────────────────────────────────

def fetch_line_history_html(covers_game_id: str) -> str | None:
    """
    GET the linehistorybrick endpoint for a single game.
    Returns HTML string or None if the request fails.

    The betType=spread parameter is arbitrary — the response always contains
    ALL tabs (moneyline, spread, total) regardless of betType. We use 'spread'
    since that's closest to what we're after.

    countryCode=au is required for bet365/Betway/William Hill data.
    """
    url = COVERS_HISTORY_URL.format(game_id=covers_game_id)
    req = urllib.request.Request(url, headers={
        "User-Agent":      (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept":          "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-AU,en;q=0.9",
        "Referer":         "https://www.covers.com/sport/baseball/mlb/odds",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        print(f"  WARNING: fetch failed for covers_game_id={covers_game_id}: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: BeautifulSoup — parse HTML tabs into structured data
# ─────────────────────────────────────────────────────────────────────────────

def _parse_line_td(td) -> dict | None:
    """
    Parse a line <td> from a Covers history row.

    The TD contains 6 outer spans in groups of 3 (American / Decimal / Fractional)
    for each side (away/over first, then home/under):
        <span style="display: inline-flex;">+1.5<span class="text-d-grey">-155</span></span>
        <span style="display: none;">...</span>  <- decimal, skip
        <span style="display: none;">...</span>  <- fractional, skip
        <span style="display: inline-flex;">-1.5<span class="text-d-grey">+130</span></span>
        ...
    We only need span index 0 (first side American) and index 3 (second side American).
    """
    # Direct children spans only — ignores the nested price spans
    spans = td.find_all("span", recursive=False)
    if len(spans) < 4:
        return None

    def extract(span):
        # Inner price span has class "text-d-grey"
        price_span = span.find("span", class_="text-d-grey")
        if not price_span:
            return None, None
        price = price_span.get_text().strip()
        # Remove the price text from the full span text to get the point/line value
        point = span.get_text().replace(price, "").strip()
        return point, price

    away_point, away_price = extract(spans[0])
    home_point, home_price = extract(spans[3])

    if not all([away_point, away_price, home_point, home_price]):
        return None

    return {
        "away_point": away_point,   # "+1.5" (spread) or "o7.5" (total)
        "away_price": away_price,   # "-155"
        "home_point": home_point,   # "-1.5" (spread) or "u7.5" (total)
        "home_price": home_price,   # "+130"
    }


def _parse_time_td(td) -> str:
    """
    Parse the timestamp <td>. Two spans: day label + time.
    Returns e.g. "Today 07:13" or "Jun 13 16:44" or "OPEN 16:44".
    """
    spans = td.find_all("span")
    parts = [s.get_text().strip() for s in spans if s.get_text().strip()]
    return " ".join(parts[:2]) if len(parts) >= 2 else td.get_text().strip()


def _parse_tab(tab_div) -> dict:
    """
    Parse one tab div (#lh-tab-spread or #lh-tab-total).

    Tab structure per book:
      Table 1: no class 'covers-line-history-table' → the OPEN-row table
      Table 2: class 'covers-line-history-table'    → the update-row table

    The OPEN row is explicitly labeled <span class="u-fw-700">OPEN</span>.
    All tabs for all books are pre-loaded in the HTML — CSS hides non-active
    tabs; BeautifulSoup reads the raw HTML so all data is accessible.

    Returns:
      {
        "open":  {"away_point": ..., "away_price": ..., "home_point": ...,
                  "home_price": ..., "time": "16:44"},
        "books": {
            "bet365":      [{"time": ..., "away_point": ..., ...}, ...],
            "betway":      [...],
            "williamhill": [...],
        }
      }
    """
    result = {
        "open":  None,
        "books": {book: [] for book in BOOK_IDS},
    }

    for table in tab_div.find_all("table"):
        book_id    = table.get("data-book-id")
        table_cls  = table.get("class") or []
        is_open_tbl = "covers-line-history-table" not in table_cls

        rows = table.find("tbody").find_all("tr") if table.find("tbody") else []

        if is_open_tbl and book_id == "1":
            # OPEN table — single row, bet365's opening price
            for row in rows:
                tds = row.find_all("td", recursive=False)
                if len(tds) < 4:
                    continue
                # Extract just the clock time from the OPEN label cell
                # The cell has: <span>OPEN</span> <span> 16:44</span>
                time_spans = tds[0].find_all("span")
                time_parts = [s.get_text().strip() for s in time_spans if s.get_text().strip()]
                # Use only the last part (the clock time, e.g. "16:44")
                time_str = time_parts[-1] if time_parts else "?"
                lines = _parse_line_td(tds[3])
                if lines:
                    result["open"] = {"time": time_str, **lines}

        elif not is_open_tbl:
            # Update-row table — find which book this belongs to
            book_name = next(
                (name for name, bid in BOOK_IDS.items() if bid == book_id),
                None,
            )
            if book_name is None:
                continue  # BetVictor (id=10) or unknown — skip

            for row in rows:
                tds = row.find_all("td", recursive=False)
                if len(tds) < 4:
                    continue
                time_str = _parse_time_td(tds[0])
                lines    = _parse_line_td(tds[3])
                if lines:
                    result["books"][book_name].append({"time": time_str, **lines})

    return result


def _deduplicate_movement(entries: list, fields: list[str]) -> list:
    """
    Filter a movement list to only rows where at least one of the given
    fields changed from the previous row.

    Covers returns rows newest-first, so we reverse to get oldest-first for
    dedup logic, then reverse back. Returns at most 5 entries.
    """
    if not entries:
        return []
    ordered = list(reversed(entries))    # oldest first
    deduped = [ordered[0]]
    for entry in ordered[1:]:
        prev = deduped[-1]
        if any(entry.get(f) != prev.get(f) for f in fields):
            deduped.append(entry)
    return list(reversed(deduped))[:5]   # newest-first, capped at 5


def parse_covers_html(html: str) -> dict:
    """
    Parse the full linehistorybrick HTML response.
    Returns the covers_lines dict to store under game["covers_lines"].
    """
    soup = BeautifulSoup(html, "html.parser")

    spread_tab = soup.find(id="lh-tab-spread")
    total_tab  = soup.find(id="lh-tab-total")

    covers_lines = {
        "opening_rl":     None,
        "opening_total":  None,
        "current_rl":     {},
        "current_total":  {},
        "rl_movement":    [],
        "total_movement": [],
        "fetched_at":     datetime.now(ET).strftime("%Y-%m-%dT%H:%M:%S"),
        "source":         "covers.com/bet365",
        "country_code":   "au",
    }

    # ── Spread / Run Line ────────────────────────────────────────────────────
    if spread_tab:
        parsed = _parse_tab(spread_tab)

        if parsed["open"]:
            op = parsed["open"]
            covers_lines["opening_rl"] = {
                "away": f"{op['away_point']} {op['away_price']}",
                "home": f"{op['home_point']} {op['home_price']}",
                "time": op["time"],
            }

        # Current RL: most recent entry per book (entries are newest-first)
        for book, entries in parsed["books"].items():
            if entries:
                e = entries[0]
                covers_lines["current_rl"][book] = {
                    "away": f"{e['away_point']} {e['away_price']}",
                    "home": f"{e['home_point']} {e['home_price']}",
                }

        # RL movement: bet365 only, deduplicated on price change, newest-first, max 5
        bet365_rl = parsed["books"].get("bet365", [])
        moved = _deduplicate_movement(bet365_rl, ["away_price", "home_price"])
        covers_lines["rl_movement"] = [
            {
                "time": e["time"],
                "away": f"{e['away_point']} {e['away_price']}",
                "home": f"{e['home_point']} {e['home_price']}",
            }
            for e in moved
        ]

    # ── Totals ───────────────────────────────────────────────────────────────
    if total_tab:
        parsed = _parse_tab(total_tab)

        def _parse_line(point_str: str) -> float | str:
            # "o7.5" -> 7.5, "u8.0" -> 8.0
            try:
                return float(point_str.lstrip("ou"))
            except ValueError:
                return point_str

        if parsed["open"]:
            op = parsed["open"]
            covers_lines["opening_total"] = {
                "line":  _parse_line(op["away_point"]),
                "over":  op["away_price"],
                "under": op["home_price"],
                "time":  op["time"],
            }

        for book, entries in parsed["books"].items():
            if entries:
                e = entries[0]
                covers_lines["current_total"][book] = {
                    "line":  _parse_line(e["away_point"]),
                    "over":  e["away_price"],
                    "under": e["home_price"],
                }

        # Total movement: deduplicated on line OR either price change
        bet365_tot = parsed["books"].get("bet365", [])
        moved = _deduplicate_movement(
            bet365_tot, ["away_point", "away_price", "home_price"]
        )
        covers_lines["total_movement"] = [
            {
                "time":  e["time"],
                "line":  _parse_line(e["away_point"]),
                "over":  e["away_price"],
                "under": e["home_price"],
            }
            for e in moved
        ]

    return covers_lines


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch Covers.com opening RL/total prices and movement history."
    )
    parser.add_argument("--date",    default=None,  help="Slate date YYYY-MM-DD (default: today ET)")
    parser.add_argument("--sport",   default="mlb")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch ONE game, print parsed JSON, do not write games.json")
    args = parser.parse_args()

    date  = args.date or today_et()
    sport = args.sport

    games_path = PROJECT_ROOT / "data" / sport / date / "games.json"
    if not games_path.exists():
        print(f"ERROR: games.json not found: {games_path}")
        print(f"  Run: python scripts/fetch_odds.py --sport {sport} --date {date}")
        sys.exit(1)

    games  = json.loads(games_path.read_text(encoding="utf-8"))
    # Build lookup: (away_abbr, home_abbr) -> game dict
    lookup = {(g["away"]["abbr"], g["home"]["abbr"]): g for g in games}

    print(f"\n{'='*60}")
    print(f"  FETCH COVERS LINES  {sport.upper()}  {date}")
    print(f"{'='*60}\n")

    # ── Step 1: Playwright to extract Covers gameIds ─────────────────────────
    print("Step 1: Rendering Covers odds page (Playwright)...")
    covers_games = fetch_covers_game_ids()
    print(f"  Covers returned {len(covers_games)} game rows")

    # Match Covers rows to games.json
    matched_pairs = []    # list of (game_dict, covers_game_id)
    unmatched     = []

    for cg in covers_games:
        key  = (cg["away_abbr"], cg["home_abbr"])
        game = lookup.get(key)
        if game is None:
            unmatched.append(f"{cg['away_abbr']}@{cg['home_abbr']}")
        else:
            matched_pairs.append((game, cg["game_id"]))

    if unmatched:
        for u in unmatched:
            print(f"  WARNING: no games.json match for Covers game: {u}")

    print(f"  Matched {len(matched_pairs)}/{len(covers_games)} games to games.json\n")

    if not matched_pairs:
        print("ERROR: No games matched. Check team abbreviations or date.")
        sys.exit(1)

    # In dry-run mode, only process the first game
    target_pairs = matched_pairs[:1] if args.dry_run else matched_pairs

    # ── Steps 2+3: fetch + parse per game ───────────────────────────────────
    for i, (game, covers_id) in enumerate(target_pairs):
        abbr = f"{game['away']['abbr']}@{game['home']['abbr']}"
        print(f"  [{i+1}/{len(target_pairs)}] {abbr}  covers_id={covers_id}")

        html = fetch_line_history_html(covers_id)
        if html is None:
            game["covers_lines"] = None
            continue

        covers_lines = parse_covers_html(html)
        game["covers_lines"] = covers_lines

        if args.dry_run:
            print(f"\nParsed covers_lines for {abbr}:")
            print(json.dumps(covers_lines, indent=2))
            print("\n(dry-run: games.json NOT modified)")
            return

        # Polite delay between requests
        if i < len(target_pairs) - 1:
            time.sleep(0.5)

    # ── Step 4 (full run only): write updated games.json ─────────────────────
    games_path.write_text(json.dumps(games, indent=2), encoding="utf-8")
    success = sum(1 for g in games if g.get("covers_lines") is not None)
    print(f"\nWritten: {games_path.relative_to(PROJECT_ROOT)}")
    print(f"  {success}/{len(games)} games have covers_lines data")


if __name__ == "__main__":
    main()

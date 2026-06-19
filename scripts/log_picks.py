#!/usr/bin/env python
"""
scripts/log_picks.py

Parse a model's raw response text (the ## GAME: format from our prompt)
into a structured JSON file that the grader and stats engine can read.

The raw response is the text you paste into an AI model and it replies with.
This script turns that unstructured text into a permanent, queryable record.

Usage:
    python scripts/log_picks.py --model sonnet --date 2026-06-02 --input picks/mlb/2026-06-02/sonnet.json
    python scripts/log_picks.py --model chatgpt --date 2026-06-02 --input picks/mlb/2026-06-02/chatgpt.json

Arguments:
    --model   Short model identifier, e.g. sonnet, chatgpt, gemini, grok, deepseek
    --date    Slate date (YYYY-MM-DD)
    --sport   Sport code (default: mlb)
    --input   Path to the raw response text file

Reads:
    data/{sport}/{date}/games.json     -- for game_id lookup and abbr mapping
    {input file}                       -- raw model response text

Writes:
    picks/{sport}/{date}/{model}.json  -- parsed structured JSON (overwrites input)
    picks/{sport}/{date}/{model}_raw.txt -- backup of original raw text

The raw text backup means nothing is lost when the structured JSON is written.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from tz_util import ET




# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# GAMES.JSON LOADER — builds the lookup table for game_id and abbr mapping
# ─────────────────────────────────────────────────────────────────────────────

def load_game_lookup(sport: str, date: str, project_root: Path) -> dict:
    """
    Build a lookup table from games.json so we can:
      1. Map (away_abbr, home_abbr) -> game_id (the permanent join key)
      2. Know which abbr is 'away' and which is 'home' for each matchup

    Returns a dict keyed by "AWAY @ HOME" abbr pairs, e.g. "DET @ TB".
    Each value has: game_id, away_abbr, home_abbr, away_name, home_name
    """
    games_path = project_root / "data" / sport / date / "games.json"
    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        print("  Run fetch_odds.py first.")
        sys.exit(1)

    with open(games_path, encoding="utf-8") as f:
        games = json.load(f)

    lookup = {}
    for g in games:
        away_abbr = g["away"]["abbr"]
        home_abbr = g["home"]["abbr"]
        key = f"{away_abbr} @ {home_abbr}"
        lookup[key] = {
            "game_id":   g["game_id"],
            "away_abbr": away_abbr,
            "home_abbr": home_abbr,
            "away_name": g["away"]["name"],
            "home_name": g["home"]["name"],
        }

    return lookup


# ─────────────────────────────────────────────────────────────────────────────
# FIELD PARSERS
# ─────────────────────────────────────────────────────────────────────────────

def parse_price(price_raw: str | None) -> int | None:
    """
    Extract a numeric American odds price from a raw string.
    Handles annotations like "+118 (best +160 BetMGM)" by taking only the first value.

    Examples:
      "+113"                    -> 113
      "-128"                    -> -128
      "N/A"                     -> None
      "+118 (best +160 BetMGM)" -> 118
      "+100 (best available...)" -> 100
    """
    if not price_raw:
        return None
    cleaned = price_raw.strip()
    if cleaned.upper() in ("N/A", "NA", ""):
        return None
    # Extract the first +/- number (American odds format)
    match = re.search(r"([+-]\d+)|\b(\d{3,})\b", cleaned)
    if match:
        val = match.group(1) or match.group(2)
        return int(val)
    return None


def parse_units(units_raw: str | None) -> int:
    """
    Convert the UNITS field to a numeric value.
    PASS and LEAN both represent 0 units risked.

    Examples:
      "1"    -> 1
      "3"    -> 3
      "PASS" -> 0
      "LEAN" -> 0
    """
    if not units_raw:
        return 0
    cleaned = units_raw.strip().upper()
    if cleaned in ("PASS", "LEAN"):
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0


def parse_action(units_raw: str | None) -> str:
    """
    Determine bet action from the UNITS field.

    "PASS" -> "pass"
    "LEAN" -> "lean"
    numeric -> "bet"

    Using UNITS rather than PICK for this because UNITS is more explicit.
    PICK can say "LEAN BAL" but UNITS confirms whether it's a lean or a bet.
    """
    if not units_raw:
        return "pass"
    cleaned = units_raw.strip().upper()
    if cleaned == "PASS":
        return "pass"
    if cleaned == "LEAN":
        return "lean"
    return "bet"


def parse_pick_side_and_market(
    pick_raw: str | None,
    away_abbr: str,
    home_abbr: str,
) -> tuple[str | None, str | None]:
    """
    Parse the PICK field into (pick_side, pick_market).

    pick_side:   "away" | "home" | "over" | "under" | None
    pick_market: "ml"   | "rl"   | "total" | None

    Handles all formats seen across models:
      "PASS"          -> (None, None)
      "LEAN BAL"      -> (side for BAL, "ml")
      "LEAN: BAL ML"  -> (side for BAL, "ml")      [some models prefix LEAN:]
      "SD ML"         -> ("away", "ml")
      "ATL ML"        -> ("home", "ml")
      "NYY -1.5"      -> ("home", "rl")
      "NYY -1.5 RL"   -> ("home", "rl")            [some models append RL]
      "Over"          -> ("over",  "total")
      "Over 9.0"      -> ("over",  "total")         [some models include the line]
      "Under 7.5"     -> ("under", "total")
    """
    if not pick_raw:
        return None, None

    # Strip LEAN: prefix — lean vs bet is already captured in action/units
    text = pick_raw.strip()
    text = re.sub(r"^LEAN\s*:?\s*", "", text, flags=re.IGNORECASE).strip()

    upper = text.upper()

    if upper == "PASS":
        return None, None

    # Split into tokens early — needed for multi-word picks
    tokens = upper.split()
    if not tokens:
        return None, None

    first = tokens[0]

    # Totals: first token is Over/Under (possibly followed by the line value)
    if first in ("OVER", "OVER ML", "OVER TOTAL"):
        return "over", "total"
    if first in ("UNDER", "UNDER ML", "UNDER TOTAL"):
        return "under", "total"

    team_token = first

    # Determine side by matching against away/home abbreviation
    if team_token == away_abbr.upper():
        side = "away"
    elif team_token == home_abbr.upper():
        side = "home"
    else:
        side = None   # unknown abbr — stored raw for manual review

    # Determine market from second token (if present).
    # Strip bare sign tokens — kimi writes "TEX + ML" with a stray "+" between
    # the team and market label. Filter those out so the real market token is found.
    tokens = [t for t in tokens if t not in ("+", "-")]

    market = None
    if len(tokens) >= 2:
        second = tokens[1]
        if second == "ML":
            market = "ml"
        elif "-1.5" in second or "+1.5" in second or second in ("RL", "RUNLINE", "RUN"):
            market = "rl"
        elif re.match(r"^[+-]\d+$", second):
            # "SD +120" or "CHW -118" — team + price with no market label → ML
            market = "ml"
        elif "+1.5" in second:
            # Taking the +1.5 underdog on the run line
            market = "rl"
        elif second in ("OVER", "UNDER"):
            # e.g. "PICK: Over" got split weirdly
            return second.lower(), "total"
    elif side is not None:
        # Only one token (just the team abbr, like "LEAN BAL") — no market specified
        # For leans with no explicit market, default to ML (most common case)
        market = "ml"

    return side, market


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK PARSER — turns one ## GAME block into a structured dict
# ─────────────────────────────────────────────────────────────────────────────

def parse_fields(block: str) -> dict:
    """
    Parse the key: value fields out of a game block or any structured block.

    Handles multi-line values (REASON and DATA GAP can run across several lines).
    A new field starts when a line matches the pattern: ^[A-Z ]+: value
    """
    fields = {}
    current_key = None
    current_lines = []

    for line in block.split("\n"):
        # A field header looks like "PICK: ..." or "REASON: ..."
        # The key is all-caps, optionally with spaces, followed by ": "
        match = re.match(r"^([A-Z][A-Z0-9 _]*?):\s*(.*)", line)
        if match:
            # Save the previous field
            if current_key:
                fields[current_key] = "\n".join(current_lines).strip()
            current_key  = match.group(1).strip()
            current_lines = [match.group(2)]
        elif current_key:
            # Continuation line for the current field (e.g. multi-line REASON)
            current_lines.append(line)

    # Save the last field
    if current_key:
        fields[current_key] = "\n".join(current_lines).strip()

    return fields


def parse_game_block(
    block: str,
    game_lookup: dict,
) -> tuple[dict, dict | None] | None:
    """
    Parse one ## GAME: block into (side_pick, total_pick).

    side_pick  — always present when the block is valid (action may be "pass")
    total_pick — present when TOTAL: field is Over/Under/Lean; None otherwise

    Returns None if the game header can't be matched to a known game.
    """
    lines = block.strip().split("\n")
    if not lines:
        return None

    # First line is the matchup: "DET @ TB"
    header = lines[0].strip()   # e.g. "DET @ TB"

    # Look up this game in games.json
    game_info = game_lookup.get(header)
    if not game_info:
        # Try case-insensitive match as a fallback
        header_upper = header.upper()
        for key, val in game_lookup.items():
            if key.upper() == header_upper:
                game_info = val
                break

    if not game_info:
        print(f"  WARNING: Game '{header}' not found in games.json — skipping")
        return None

    away_abbr = game_info["away_abbr"]
    home_abbr = game_info["home_abbr"]

    # Parse all the key: value fields from the rest of the block
    body = "\n".join(lines[1:])
    fields = parse_fields(body)

    pick_raw        = fields.get("PICK", "").strip()
    price_raw       = fields.get("PRICE", "").strip()
    units_raw       = fields.get("UNITS", "").strip()
    edge_raw        = fields.get("EDGE", "").strip()
    reason          = fields.get("REASON", "").strip()
    total_raw       = fields.get("TOTAL", "").strip()
    total_price_raw = fields.get("TOTAL PRICE", "").strip()
    total_units_raw = fields.get("TOTAL UNITS", "").strip()
    total_edge_raw  = fields.get("TOTAL EDGE", "").strip()
    # Accept both "DATA GAP" (current) and "LOOKED UP" (legacy pre-Jun-15 files)
    data_gap        = (fields.get("DATA GAP") or fields.get("LOOKED UP") or "").strip()

    action                 = parse_action(units_raw)
    pick_side, pick_market = parse_pick_side_and_market(pick_raw, away_abbr, home_abbr)
    price                  = parse_price(price_raw)
    units                  = parse_units(units_raw)
    edge                   = edge_raw.lower() if edge_raw else None

    # Contamination check — parlay/summary content can bleed into a game block
    # in bare format if the section splitter didn't separate them first.
    # Truncate the affected field at the first marker and record a warning
    # so the issue is visible in the JSON rather than silently corrupting data.
    CONTAMINATION_MARKERS = ("LEG 1:", "LEG 2:", "SLATE SUMMARY", "BEST BET:")
    parse_warning = None
    for field_name in ("reason", "data_gap"):
        field_val = reason if field_name == "reason" else data_gap
        for marker in CONTAMINATION_MARKERS:
            if marker in field_val:
                truncated = field_val[:field_val.find(marker)].strip()
                if field_name == "reason":
                    reason = truncated
                else:
                    data_gap = truncated
                parse_warning = (
                    f"field '{field_name}' contained '{marker}' — "
                    "parlay/summary content bled in; field truncated"
                )
                print(f"  NOTE: parse_warning on {header} — {parse_warning}")
                break
        if parse_warning:
            break   # one warning per block is enough

    # ── Parse TOTAL: field as an independent second pick ─────────────────────
    # TOTAL: Over 8.5  → bet on the over
    # TOTAL: Under 7.5 → bet on the under
    # TOTAL: Lean Over / Lean Under → lean, no units
    # TOTAL: No bet / No lean / absent → skip
    total_pick = None   # dict, or None if no total bet/lean
    total_str = total_raw.upper().strip()
    if total_str and total_str not in ("NO BET", "NO LEAN", "NONE", "N/A", ""):
        t_side = None
        t_action = None
        if total_str.startswith("OVER"):
            t_side = "over"
            t_action = "bet"
        elif total_str.startswith("UNDER"):
            t_side = "under"
            t_action = "bet"
        elif "LEAN OVER" in total_str:
            t_side = "over"
            t_action = "lean"
        elif "LEAN UNDER" in total_str:
            t_side = "under"
            t_action = "lean"

        if t_side:
            t_price = parse_price(total_price_raw)
            t_units_str = total_units_raw.upper().strip()
            if t_action == "lean" or t_units_str in ("LEAN", ""):
                t_units = 0
                t_action = "lean"
            elif t_units_str == "NO BET":
                t_units = 0
                t_action = "pass"
            else:
                t_units = parse_units(t_units_str) if t_units_str else 0
                if t_units and t_units > 0:
                    t_action = "bet"
                else:
                    t_action = "lean"
            t_edge = total_edge_raw.lower() if total_edge_raw else None

            total_pick = {
                "game_id":     game_info["game_id"],
                "matchup":     header,
                "away_abbr":   away_abbr,
                "home_abbr":   home_abbr,
                "action":      t_action,
                "pick_raw":    total_raw,
                "pick_side":   t_side,
                "pick_market": "total",
                "price":       t_price,
                "units":       t_units,
                "units_raw":   total_units_raw or t_action.upper(),
                "edge":        t_edge,
                "reason":      reason,
                "data_gap":    data_gap,
                "result":        None,
                "profit_units":  None,
                "clv":           None,
                "closing_line":  None,
                "parse_warning": None,
                "_is_total":   True,   # internal flag so summary tables can label it
            }

    side_pick = {
        # Join key — links this pick to game data and results
        "game_id":     game_info["game_id"],
        "matchup":     header,
        "away_abbr":   away_abbr,
        "home_abbr":   home_abbr,

        # The pick itself
        "action":      action,       # "bet" | "lean" | "pass"
        "pick_raw":    pick_raw,     # original text e.g. "MIL -1.5"
        "pick_side":   pick_side,    # "away" | "home" | "over" | "under" | None
        "pick_market": pick_market,  # "ml" | "rl" | "total" | None
        "price":       price,        # integer American odds, None for pass

        # Staking and confidence
        "units":       units,        # 0 for pass/lean, 1/3 for bets
        "units_raw":   units_raw,    # original string ("PASS", "1", "LEAN", etc.)
        "edge":        edge,         # numeric gap string e.g. "6.2 pts"

        # The model's reasoning
        "reason":      reason,
        "data_gap":    data_gap,

        # Grading fields — populated later by grade_picks.py
        "result":        None,
        "profit_units":  None,
        "clv":           None,
        "closing_line":  None,

        # Parser health
        "parse_warning": parse_warning,
    }

    # Return side pick + optional total pick (caller decides how to store both)
    return side_pick, total_pick


# ─────────────────────────────────────────────────────────────────────────────
# PARLAY PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_parlay_block(block: str) -> dict | None:
    """
    Parse the optional ## PARLAY block.

    Format:
      LEG 1: SD ML +113
      LEG 2: ATL ML -128
      COMBINED PRICE: +279 (approximate)
      TRUE PROBABILITY ESTIMATE: ~31.7% (...)
      UNITS: 1
      REASON: ...
    """
    if not block.strip():
        return None

    fields = parse_fields(block)

    leg1      = fields.get("LEG 1", "").strip()
    leg2      = fields.get("LEG 2", "").strip()
    price_raw = fields.get("COMBINED PRICE", "").strip()
    prob_est  = fields.get("TRUE PROBABILITY ESTIMATE", "").strip()
    units_raw = fields.get("UNITS", "").strip()
    reason    = fields.get("REASON", "").strip()

    # Extract the last word/number from each leg as the price
    combined_price = parse_price(price_raw)

    return {
        "leg1":                   leg1,
        "leg2":                   leg2,
        "combined_price":         combined_price,
        "true_probability_est":   prob_est,
        "units":                  parse_units(units_raw),
        "reason":                 reason,
        # Grading
        "result":       None,
        "profit_units": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SLATE SUMMARY PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_summary_block(block: str) -> dict | None:
    """
    Parse the ## SLATE SUMMARY block.

    Returns one of three things:
      - None                        if the block is empty or has no BEST BET line
      - {"best_bet": ..., "why_this": ...}   if a real 3-unit best bet was identified
      - {"no_best_bet": True, "raw": ...}    if the model output the NO BEST BET sentinel
    """
    if not block.strip():
        return None
    fields = parse_fields(block)
    best = fields.get("BEST BET", "").strip()
    why  = fields.get("WHY THIS ONE", "").strip()
    if not best:
        return None
    # Detect the v3.1+ sentinel: "NO BEST BET -- no 3-unit play identified today"
    if re.search(r"NO BEST BET", best, re.IGNORECASE):
        return {"no_best_bet": True, "raw": best}
    return {"best_bet": best, "why_this": why}


def parse_best_bet_fallback(raw_text: str) -> dict | None:
    """
    Full-text scan for a BEST BET: line when the SLATE SUMMARY block was not
    cleanly parsed (e.g. PARLAY/SUMMARY content bled into a game block in
    bare format, so summary was never routed to parse_summary_block).

    Scans every line of the raw text and returns the first BEST BET: match,
    plus the WHY THIS ONE: line if it appears within the next 5 lines.
    """
    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^BEST BET\s*:", stripped, re.IGNORECASE):
            best_bet_val = re.sub(r"^BEST BET\s*:\s*", "", stripped, flags=re.IGNORECASE)
            why_this = ""
            for j in range(i + 1, min(i + 6, len(lines))):
                next_stripped = lines[j].strip()
                if re.match(r"^WHY THIS ONE\s*:", next_stripped, re.IGNORECASE):
                    why_this = re.sub(r"^WHY THIS ONE\s*:\s*", "", next_stripped,
                                      flags=re.IGNORECASE)
                    break
            if re.search(r"NO BEST BET", best_bet_val, re.IGNORECASE):
                return {"no_best_bet": True, "raw": best_bet_val}
            return {"best_bet": best_bet_val, "why_this": why_this}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PARSER — splits raw text into sections and parses each
# ─────────────────────────────────────────────────────────────────────────────

def parse_response(raw_text: str, game_lookup: dict) -> tuple[list, dict | None, dict | None]:
    """
    Split the full model response into sections and parse each one.

    Handles four header formats observed across models:
      Standard:  ## GAME: DET @ TB   (our prompt spec — ## markers separate all sections)
      Bold:      **## GAME: DET @ TB**  (Grok sometimes wraps headers in bold markdown)
      Bare:      GAME: DET @ TB      (some models drop the ## marker)
      Numbered:  GAME N: DET @ TB    (e.g. Kimi's thinking-mode format: GAME 1:, GAME 7:)

    The bare-format path explicitly locates PARLAY and SLATE SUMMARY before
    splitting game blocks, so those sections never bleed into the last game.
    """
    # Strip bold markdown wrapping from headers (e.g. **## GAME:** -> ## GAME:)
    raw_text = re.sub(r"\*\*(## (?:GAME|SLATE SUMMARY|PARLAY)[^*]*)\*\*", r"\1", raw_text)

    uses_headers = bool(re.search(r"^## GAME:", raw_text, re.MULTILINE))

    if uses_headers:
        # ── Standard format ───────────────────────────────────────────────────
        # ## markers cleanly separate every section; a simple split handles all.
        picks   = []
        parlay  = None
        summary = None

        for part in re.split(r"(?=^## )", raw_text, flags=re.MULTILINE):
            part = part.strip()
            if not part:
                continue
            if part.startswith("## GAME:"):
                body = part[len("## GAME:"):].strip().replace("\n---", "").strip()
                result = parse_game_block(body, game_lookup)
                if result:
                    side_pick, total_pick = result
                    picks.append(side_pick)
                    if total_pick:
                        picks.append(total_pick)
            elif part.startswith("## PARLAY"):
                parlay = parse_parlay_block(part[len("## PARLAY"):].strip())
            elif part.startswith("## SLATE SUMMARY"):
                summary = parse_summary_block(part[len("## SLATE SUMMARY"):].strip())

        return picks, parlay, summary

    else:
        # ── Bare format ───────────────────────────────────────────────────────
        # PARLAY and SLATE SUMMARY appear as bare keywords on their own lines.
        # We must locate them first and slice the text so game blocks are parsed
        # only from the prefix — preventing parlay/summary content bleeding in.

        parlay_m  = re.search(r"^PARLAY\s*$",        raw_text, re.MULTILINE)
        summary_m = re.search(r"^SLATE SUMMARY\s*$", raw_text, re.MULTILINE)

        # Game text = everything before the first non-game section
        first_section = min(
            parlay_m.start()  if parlay_m  else len(raw_text),
            summary_m.start() if summary_m else len(raw_text),
        )
        game_text = raw_text[:first_section]
        tail_text = raw_text[first_section:]

        # Parse game blocks from the clean prefix only.
        # Split on GAME: (bare) or GAME N: (numbered, e.g. Kimi's thinking format).
        # The lookahead anchors to line-start via the preceding \n so mid-line
        # "GAME 7:" text in prose fields cannot trigger a false split.
        picks = []
        for part in re.split(r"\n(?=GAME(?: \d+)?:)", game_text):
            part = part.strip()
            m = re.match(r"GAME(?: \d+)?:\s*", part)
            if not m:
                continue
            body = part[m.end():].strip().replace("\n---", "").strip()
            result = parse_game_block(body, game_lookup)
            if result:
                side_pick, total_pick = result
                picks.append(side_pick)
                if total_pick:
                    picks.append(total_pick)

        # Parse PARLAY from the tail (between PARLAY and SLATE SUMMARY)
        parlay = None
        if parlay_m:
            pm = re.search(r"^PARLAY\s*$", tail_text, re.MULTILINE)
            if pm:
                parlay_body = tail_text[pm.end():]
                sm_in_tail  = re.search(r"^SLATE SUMMARY\s*$", parlay_body, re.MULTILINE)
                if sm_in_tail:
                    parlay_body = parlay_body[:sm_in_tail.start()]
                parlay = parse_parlay_block(parlay_body.strip())

        # Parse SLATE SUMMARY from the tail
        summary = None
        if summary_m:
            sm = re.search(r"^SLATE SUMMARY\s*$", tail_text, re.MULTILINE)
            if sm:
                summary = parse_summary_block(tail_text[sm.end():].strip())

        return picks, parlay, summary


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def log_picks(model: str, sport: str, date: str, input_path: Path):
    """
    Parse a raw model response file and write structured JSON picks.
    """
    target_date = date or today_et()

    print(f"\n{'='*55}")
    print(f"  LOG PICKS")
    print(f"  Model : {model}")
    print(f"  Date  : {target_date}")
    print(f"  Sport : {sport}")
    print(f"  Input : {input_path}")
    print(f"{'='*55}\n")

    project_root = Path(__file__).parent.parent

    # ── Load raw text ─────────────────────────────────────────────────────────
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    raw_text = input_path.read_text(encoding="utf-8", errors="replace")

    # Detect if the file is already parsed JSON — if so, warn and exit
    try:
        maybe_json = json.loads(raw_text)
        if isinstance(maybe_json, dict) and "picks" in maybe_json and "model" in maybe_json:
            print(f"  File already contains parsed JSON. Nothing to do.")
            print(f"  To re-parse, delete {input_path} and run with the raw text file.")
            sys.exit(0)
    except json.JSONDecodeError:
        pass  # Not JSON — that's expected, it's raw model response text

    # ── Back up raw text before overwriting ───────────────────────────────────
    picks_dir = project_root / "picks" / sport / target_date
    picks_dir.mkdir(parents=True, exist_ok=True)

    raw_backup = picks_dir / f"{model}_raw.txt"
    if not raw_backup.exists():
        raw_backup.write_text(raw_text, encoding="utf-8")
        print(f"  Backed up raw text -> {raw_backup.relative_to(project_root)}")
    else:
        print(f"  Raw backup already exists: {raw_backup.relative_to(project_root)}")

    # ── Load game lookup from games.json ──────────────────────────────────────
    print(f"\nStep 1: Loading game lookup from games.json...")
    game_lookup = load_game_lookup(sport, target_date, project_root)
    print(f"  {len(game_lookup)} games in lookup")

    # ── Parse the response ────────────────────────────────────────────────────
    print(f"\nStep 2: Parsing model response...")
    picks, parlay, summary = parse_response(raw_text, game_lookup)
    print(f"  Parsed {len(picks)} game blocks")

    # Loud-fail if a non-empty raw file produced zero game blocks.
    # This catches unrecognised output formats (e.g. empty content field fallback
    # to reasoning trace, which has no PICK:/UNITS:/EDGE: fields) before they
    # silently write an empty picks JSON with counts.games=0.
    # exit(2) distinguishes format/parse failure from a normal crash (exit 1).
    # Do NOT re-call the API — fix the underlying cause, then re-run log_picks.
    raw_size = len(raw_text)
    if len(picks) == 0 and raw_size > 0:
        print(f"\nERROR: non-empty raw file ({raw_size:,} bytes) parsed to 0 game blocks.")
        print(f"  Possible causes:")
        print(f"    - Empty content field: model returned reasoning trace only (no PICK:/UNITS:/EDGE: fields)")
        print(f"    - Unrecognised format: check {model}_raw.txt and extend parse_response() if needed")
        print(f"  Do NOT re-call the API to fix this — re-parse after resolving the format issue.")
        sys.exit(2)

    # Deduplicate: keep the LAST occurrence of each matchup.
    # Sonnet does a self-audit pass that emits revised GAME blocks after the
    # initial output — later blocks supersede earlier ones for the same game.
    seen: dict[str, int] = {}
    for i, p in enumerate(picks):
        # Key by matchup + market so side and total picks coexist for the same game
        market = p.get("pick_market") or ("total" if p.get("_is_total") else "ml")
        seen[(p["matchup"], market)] = i   # last index wins
    deduped = [picks[i] for i in sorted(seen.values())]
    if len(deduped) < len(picks):
        dropped = len(picks) - len(deduped)
        print(f"  NOTE: {dropped} duplicate game block(s) removed — kept last occurrence")
    picks = deduped

    # Fallback: if SLATE SUMMARY wasn't cleanly parsed (e.g. it bled into a
    # game block in bare format), scan the full raw text for a BEST BET: line.
    if not summary or not summary.get("best_bet"):
        summary = parse_best_bet_fallback(raw_text)
        if summary:
            print(f"  NOTE: SLATE SUMMARY not cleanly parsed — "
                  f"used BEST BET: line fallback: {summary.get('best_bet', '')[:60]}")
        else:
            print(f"  WARNING: could not parse best bet for {model} — check raw file")

    # ── Compute summary counts ────────────────────────────────────────────────
    bets         = [p for p in picks if p["action"] == "bet"]
    leans        = [p for p in picks if p["action"] == "lean"]
    passes       = [p for p in picks if p["action"] == "pass"]
    units_risked = sum(p["units"] for p in bets)
    # Parlay units are separate from singles
    parlay_units = parlay["units"] if parlay else 0

    # ── Resolve best bet / no-best-bet sentinel ───────────────────────────────
    # summary can be:
    #   None                          -> no SLATE SUMMARY parsed at all
    #   {"best_bet": ..., "why": ...} -> real 3-unit best bet identified
    #   {"no_best_bet": True, "raw":} -> model explicitly skipped (v3.1+)
    if summary and summary.get("no_best_bet"):
        best_bet_out    = None
        best_bet_skip   = True
        skip_reason     = "no 3-unit play identified"
        print(f"  SKIP: model reported no 3-unit best bet — {summary.get('raw', '')[:60]}")
    else:
        best_bet_out    = summary
        best_bet_skip   = False
        skip_reason     = None

    # ── Build final JSON document ─────────────────────────────────────────────
    output = {
        "model":      model,
        "date":       target_date,
        "sport":      sport,
        "logged_at":  now_utc(),
        "picks":      picks,
        "parlay":     parlay,
        "best_bet":          best_bet_out,
        "best_bet_skip":     best_bet_skip,
        "best_bet_skip_reason": skip_reason,
        "counts": {
            "games":        len({p["matchup"] for p in picks}),
            "bets":         len(bets),
            "leans":        len(leans),
            "passes":       len(passes),
            "units_risked": units_risked,
            "parlay_units": parlay_units,
        },
    }

    # ── Write structured JSON ─────────────────────────────────────────────────
    out_path = picks_dir / f"{model}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nStep 3: Saved -> {out_path.relative_to(project_root)}")

    # ── Print pick summary ────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  PICK SUMMARY  {model}  {target_date}")
    print(f"{'='*55}")
    print()
    print(f"  {'Matchup':<12}  {'Action':<5}  {'Pick':<16}  {'Price':>6}  {'Units':>5}  {'Edge'}")
    print(f"  {'-'*12}  {'-'*5}  {'-'*16}  {'-'*6}  {'-'*5}  {'-'*6}")

    for p in picks:
        action_str = p["action"].upper()[:4]   # BET / LEA / PAS
        # Label totals picks so they're visually distinct from side picks
        label_prefix = "[TOT] " if p.get("_is_total") else ""
        pick_str   = (label_prefix + (p["pick_raw"] or ""))[:16]
        price_str  = str(p["price"]) if p["price"] is not None else "N/A"
        units_str  = str(p["units"]) if p["units"] else p["units_raw"]
        edge_str   = (p["edge"] or "").upper()[:6]
        print(f"  {p['matchup']:<12}  {action_str:<5}  {pick_str:<16}  {price_str:>6}  {units_str:>5}  {edge_str}")

    print()
    print(f"  Bets: {len(bets)}  |  Leans: {len(leans)}  |  Passes: {len(passes)}")
    print(f"  Units risked: {units_risked}")
    if parlay:
        print(f"  Parlay: {parlay.get('leg1')} + {parlay.get('leg2')}  ({parlay.get('units')} unit)")
    if best_bet_skip:
        print(f"  Best bet: SKIP — no 3-unit play identified")
    elif best_bet_out:
        print(f"  Best bet: {best_bet_out.get('best_bet', '')[:60]}")
    print(f"\n{'='*55}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a model's raw response text into structured picks JSON."
    )
    parser.add_argument(
        "--model", required=True,
        help="Short model identifier, e.g. sonnet, chatgpt, gemini, grok, deepseek"
    )
    parser.add_argument(
        "--date", default=None,
        help="Slate date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--sport", default="mlb",
        help="Sport code (default: mlb)"
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to the raw model response text file"
    )
    args = parser.parse_args()

    log_picks(
        model      = args.model,
        sport      = args.sport,
        date       = args.date,
        input_path = Path(args.input),
    )

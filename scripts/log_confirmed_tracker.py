#!/usr/bin/env python
"""
scripts/log_confirmed_tracker.py

Parse the CONFIRMED DATA EVALUATION section from each model's post-mortem
and append one row per bet/lean game to picks/trackers/confirmed_data_tracker.csv.

Run AFTER run_postmortem_all.py completes for a date.

TRACKER RULE (critical):
  The headline metric is hypothetical_unit_delta summed ONLY over rows where
  reason_supported = YES. Rows where WOULD CHANGE ≠ "no change" but no specific
  pre-game reason is given are marked UNSUPPORTED and excluded from the total.
  This prevents outcome-fitted reasoning from inflating the apparent benefit.

Two totals are always printed:
  supported_delta   — real signal (reason_supported = YES only)
  unsupported_delta — logged but discarded

Usage:
    python scripts/log_confirmed_tracker.py mlb --date 2026-06-15
    python scripts/log_confirmed_tracker.py mlb --date 2026-06-15 --models sonnet opus
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tz_util import ET

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACKER_PATH = PROJECT_ROOT / "picks" / "trackers" / "confirmed_data_tracker.csv"

TRACKER_COLS = [
    "date", "model", "game", "original_call", "original_stake",
    "original_result",       # WIN / LOSS / PUSH / N/A (lean)
    "would_change",          # no change / lean→bet / bet→pass / bet→other side / etc.
    "pre_game_reason",
    "reason_supported",      # YES / NO (UNSUPPORTED)
    "umpire_would_change",   # yes / no
    "umpire_pre_game_reason",
    "actual_game_result",    # final score string e.g. "NYM 3 CIN 5"
    "hypothetical_result",   # WIN / LOSS / N/A / PUSH if change applied
    "hypothetical_unit_delta",  # float: P&L of the change vs actuality
]

ALL_MODELS = [
    "chatgpt", "deepseek", "gemini", "grok", "kimi", "opus", "qwen", "sonnet",
]

WOULD_CHANGE_OPTIONS = {
    "no change", "lean→bet", "bet→pass", "bet→other side",
    "bet→higher stake", "bet→lower stake",
}


# ─────────────────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────────────────

def _parse_confirmed_blocks(postmortem_text: str) -> list[dict]:
    """
    Extract per-game CONFIRMED DATA EVALUATION blocks from a model's post-mortem.
    Returns list of dicts with raw field values.

    Looks for the section header and then per-game blocks starting with '### GAME:'.
    Each block is parsed for the 4 structured response fields.
    """
    # Find the confirmed data evaluation section
    section_match = re.search(
        r"## CONFIRMED DATA EVALUATION.*?(?=\n##|\Z)",
        postmortem_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not section_match:
        return []

    section_text = section_match.group(0)

    # Split on per-game blocks
    game_blocks = re.split(r"\n### GAME:", section_text)
    # First element is the section header — skip
    game_blocks = game_blocks[1:]

    results = []
    for block in game_blocks:
        # First line is "MATCHUP — YOUR CALL: ..."
        first_line = block.split("\n")[0].strip()
        matchup_match = re.match(r"(.+?)\s*[—–-]+\s*YOUR CALL:\s*(.+)", first_line)
        if not matchup_match:
            continue
        matchup   = matchup_match.group(1).strip()
        your_call = matchup_match.group(2).strip()

        def _extract(pattern, text, default=""):
            m = re.search(pattern, text, re.IGNORECASE)
            return m.group(1).strip() if m else default

        confirmed_lineup = _extract(
            r"CONFIRMED LINEUP vs YOUR ASSUMPTION:\s*(.+?)(?:\n|$)", block
        )
        would_change = _extract(
            r"WOULD CHANGE\?\s*(.+?)(?:\n|$)", block
        )
        pre_game_reason = _extract(
            r"PRE-GAME REASON[^:]*:\s*(.+?)(?:\n|UMPIRE|$)", block
        )
        umpire_line = _extract(
            r"UMPIRE WOULD CHANGE\?\s*(.+?)(?:\n|$)", block
        )

        # Parse umpire_would_change and its reason from the combined field
        # Format: "yes/no — pre-game reason: ..."
        ump_change = "no"
        ump_reason = ""
        ump_match = re.match(r"(yes|no)\s*[—–-]+\s*pre-game reason:\s*(.*)", umpire_line, re.IGNORECASE)
        if ump_match:
            ump_change = ump_match.group(1).lower()
            ump_reason = ump_match.group(2).strip()
        elif umpire_line.lower().startswith("yes"):
            ump_change = "yes"
            ump_reason = re.sub(r"^yes\s*[—–-]*\s*", "", umpire_line, flags=re.IGNORECASE).strip()
        elif umpire_line.lower().startswith("no"):
            ump_change = "no"

        # Normalise would_change to known options (strip brackets if unfilled)
        wc_clean = would_change.strip("[]").lower()
        for opt in WOULD_CHANGE_OPTIONS:
            if opt in wc_clean:
                wc_clean = opt
                break
        else:
            wc_clean = wc_clean if wc_clean else "no change"

        results.append({
            "matchup":          matchup,
            "your_call":        your_call,
            "confirmed_lineup": confirmed_lineup,
            "would_change":     wc_clean,
            "pre_game_reason":  pre_game_reason,
            "ump_would_change": ump_change,
            "ump_reason":       ump_reason,
        })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# RESULT & DELTA CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def _load_picks(model: str, sport: str, date: str) -> list[dict]:
    p = PROJECT_ROOT / "picks" / sport / date / f"{model}.json"
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    # picks JSON is {"picks": [...], ...} — extract the list
    return raw.get("picks", raw) if isinstance(raw, dict) else raw


def _load_results(sport: str, date: str) -> dict:
    """Return dict keyed by matchup string → result record."""
    p = PROJECT_ROOT / "results" / sport / date / "results.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    results = {}
    for r in (data if isinstance(data, list) else data.get("results", [])):
        key = f"{r.get('away_abbr', '')} @ {r.get('home_abbr', '')}"
        results[key] = r
    return results


def _score_string(result_rec: dict) -> str:
    if not result_rec:
        return "N/A"
    away = result_rec.get("away_abbr", "?")
    home = result_rec.get("home_abbr", "?")
    a_score = result_rec.get("away_score")
    h_score = result_rec.get("home_score")
    if a_score is None or h_score is None:
        return "N/A"
    return f"{away} {a_score}  {home} {h_score}"


def _compute_delta(
    would_change: str,
    original_action: str,
    original_result: str,     # WIN / LOSS / PUSH / N/A
    original_stake: float,
    original_price: int | None,
    hypo_result: str,         # WIN / LOSS / PUSH / N/A
) -> float:
    """
    Compute the hypothetical unit delta: how much better or worse the changed
    bet would have performed vs what actually happened.

    Delta is relative to the actual P&L that occurred:
      - lean→bet win:  +implied_profit (we would have won a bet we didn't make)
      - lean→bet loss: -stake (we would have lost a bet we didn't make)
      - bet→pass loss: +original_stake (we saved a loss)
      - bet→pass win:  -implied_profit (we gave up a win)
      - no change:     0
      - bet→other side / stake changes: approximated
    """
    if would_change == "no change":
        return 0.0

    stake = original_stake if original_stake else 1.0

    def _implied_profit(price: int | None, s: float) -> float:
        if price is None:
            return round(s * 0.909, 2)   # assume -110 if unknown
        if price > 0:
            return round(s * price / 100, 2)
        else:
            return round(s * 100 / abs(price), 2)

    if would_change == "lean→bet":
        # Lean → 1u bet (stakes the standard 1u regardless of original lean unit)
        if hypo_result == "WIN":
            return _implied_profit(original_price, 1.0)
        elif hypo_result == "LOSS":
            return -1.0
        return 0.0

    if would_change == "bet→pass":
        if original_result == "LOSS":
            return +stake      # saved
        elif original_result == "WIN":
            return -_implied_profit(original_price, stake)   # gave up win
        return 0.0

    if would_change == "bet→other side":
        # Lost original + would have won other side (or vice versa).
        # Delta vs actual: actual was -stake (loss) or +profit (win).
        if original_result == "LOSS":
            # Changed pick would have won the other side
            return stake + _implied_profit(original_price, stake)
        elif original_result == "WIN":
            # Changed pick would have lost the other side
            return -_implied_profit(original_price, stake) - stake
        return 0.0

    if would_change == "bet→higher stake":
        # Assume upgrading to 3u from 1u
        extra = 2.0
        if original_result == "WIN":
            return _implied_profit(original_price, extra)
        elif original_result == "LOSS":
            return -extra
        return 0.0

    if would_change == "bet→lower stake":
        # Assume downgrading to 1u from 3u (saves 2u on a loss, gives up 2u profit on win)
        saved = stake - 1.0 if stake > 1 else 0
        if original_result == "LOSS":
            return +saved
        elif original_result == "WIN":
            return -_implied_profit(original_price, saved)
        return 0.0

    return 0.0


def _hypo_result(would_change: str, original_action: str, original_result: str) -> str:
    """Determine the hypothetical outcome if the change had been applied."""
    if would_change == "no change":
        return "N/A"
    if would_change == "lean→bet":
        return original_result  # same game, same side, result is same
    if would_change == "bet→pass":
        return "N/A (would not have bet)"
    if would_change == "bet→other side":
        if original_result == "WIN":
            return "LOSS"
        elif original_result == "LOSS":
            return "WIN"
        return "PUSH"
    if would_change in ("bet→higher stake", "bet→lower stake"):
        return original_result  # same side, same result
    return "N/A"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run(sport: str, date: str, models: list[str]):
    results_db = _load_results(sport, date)

    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not TRACKER_PATH.exists()

    rows_to_append = []
    supported_delta   = 0.0
    unsupported_delta = 0.0
    total_rows = 0

    for model in models:
        pm_path = PROJECT_ROOT / "picks" / sport / date / f"{model}_postmortem.txt"
        if not pm_path.exists():
            print(f"  {model}: no postmortem file — skipping")
            continue

        pm_text = pm_path.read_text(encoding="utf-8")
        blocks  = _parse_confirmed_blocks(pm_text)
        if not blocks:
            print(f"  {model}: no CONFIRMED DATA EVALUATION section found")
            continue

        # Build a lookup of this model's picks by matchup
        picks_list = _load_picks(model, sport, date)
        picks_by_matchup = {p.get("matchup", ""): p for p in picks_list}

        model_rows = 0
        for b in blocks:
            matchup    = b["matchup"]
            pick       = picks_by_matchup.get(matchup, {})
            action     = (pick.get("action") or "").upper()
            stake      = pick.get("units")
            try:
                stake_f = float(stake) if stake not in (None, "LEAN", "PASS") else 1.0
            except (ValueError, TypeError):
                stake_f = 1.0
            price_raw = pick.get("price")
            try:
                price_int = int(price_raw) if price_raw and price_raw != "N/A" else None
            except (ValueError, TypeError):
                price_int = None

            pick_result = (pick.get("result") or "").upper()
            if not pick_result or pick_result == "NONE":
                pick_result = "N/A"

            result_rec     = results_db.get(matchup, {})
            actual_score   = _score_string(result_rec)
            would_change   = b["would_change"]
            pre_reason     = b["pre_game_reason"]

            # Determine reason_supported: YES only when would_change != "no change"
            # AND a non-empty specific reason was given.
            if would_change == "no change":
                reason_supported = "YES"   # no change claims need no justification
            elif pre_reason and len(pre_reason) > 5:
                reason_supported = "YES"
            else:
                reason_supported = "NO (UNSUPPORTED)"

            hypo = _hypo_result(would_change, action, pick_result)
            delta = _compute_delta(
                would_change, action, pick_result, stake_f, price_int, hypo
            )

            if reason_supported == "YES":
                supported_delta += delta
            else:
                unsupported_delta += delta

            rows_to_append.append({
                "date":                   date,
                "model":                  model,
                "game":                   matchup,
                "original_call":          b["your_call"],
                "original_stake":         stake_f,
                "original_result":        pick_result,
                "would_change":           would_change,
                "pre_game_reason":        pre_reason,
                "reason_supported":       reason_supported,
                "umpire_would_change":    b["ump_would_change"],
                "umpire_pre_game_reason": b["ump_reason"],
                "actual_game_result":     actual_score,
                "hypothetical_result":    hypo,
                "hypothetical_unit_delta": round(delta, 2),
            })
            model_rows += 1
            total_rows += 1

        print(f"  {model}: {model_rows} row(s) parsed")

    # Write to tracker CSV
    with open(TRACKER_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKER_COLS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows_to_append)

    print(f"\nTracker: {TRACKER_PATH.relative_to(PROJECT_ROOT)}")
    print(f"  Rows appended:     {total_rows}")
    print(f"  Supported delta:   {supported_delta:+.2f}u  (reason_supported=YES — real signal)")
    print(f"  Unsupported delta: {unsupported_delta:+.2f}u  (no pre-game reason — discarded)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse confirmed-data evaluation from post-mortems and update tracker CSV."
    )
    parser.add_argument("sport", help="Sport code: mlb")
    parser.add_argument("--date",   default=None, help="YYYY-MM-DD (default: today ET)")
    parser.add_argument("--models", nargs="+",    help="Model(s) to process (default: all)")
    args = parser.parse_args()

    date   = args.date or datetime.now(ET).strftime("%Y-%m-%d")
    models = args.models or ALL_MODELS

    print(f"\n{'='*55}")
    print(f"  LOG CONFIRMED TRACKER  {args.sport.upper()}  {date}")
    print(f"  Models: {', '.join(models)}")
    print(f"{'='*55}\n")

    run(args.sport, date, models)

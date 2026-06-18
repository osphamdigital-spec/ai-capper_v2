#!/usr/bin/env python
"""
scripts/compare_lineups.py

Sideline accuracy report — compares three lineup sources for a slate:

  1. EXPECTED  — Rotowire morning projection  (data/{sport}/{date}/rotowire_lineups.json)
  2. ACTUAL    — MLB Stats API confirmed lineup (games.json context.lineups, status=confirmed)
  3. REGULARS  — recent-actuals pattern         (lineup_tracker.txt via load_lineup_tracker)

It measures how well EXPECTED and REGULARS predicted the ACTUAL starting nine,
per team and across the slate. This is purely diagnostic — it never modifies
games.json and never affects picks/grading.

TIMING NOTE:
  Rotowire only serves the CURRENT day's lineups (its ?date param falls back to
  today for past dates), so the EXPECTED snapshot must be captured live pre-game
  by run_daily.py. This comparison (run post-game by run_daily_2.py) reads that
  pre-captured file. If it is missing, the EXPECTED leg is simply reported as
  unavailable.

Output:
    data/{sport}/{date}/lineup_comparison.json

Usage:
    python scripts/compare_lineups.py --sport mlb --date 2026-06-18
"""

import argparse
import json
import sys
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from load_static_data import load_lineup_tracker
    _TRACKER_AVAILABLE = True
except ImportError as _e:
    _TRACKER_AVAILABLE = False
    print(f"  NOTE: load_lineup_tracker import failed ({_e}) -- REGULARS leg disabled")


# ─────────────────────────────────────────────────────────────────────────────
# NAME NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def _norm(name: str) -> str:
    """
    Normalize a player name for cross-source matching:
      - strip accents (Peña -> Pena)
      - lowercase
      - drop punctuation
      - drop generational suffixes (Jr., III, ...)
    Rotowire drops suffixes ('Vladimir Guerrero') while MLB keeps them
    ('Vladimir Guerrero Jr.'), so suffix removal is essential.
    """
    if not name:
        return ""
    # Decompose accents and drop combining marks
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in decomposed if not unicodedata.combining(c))
    ascii_name = ascii_name.lower()
    # Keep only letters and spaces
    cleaned = "".join(c if (c.isalpha() or c.isspace()) else " " for c in ascii_name)
    tokens = [t for t in cleaned.split() if t and t not in _SUFFIXES]
    return " ".join(tokens)


def _norm_set(names: list[str]) -> set[str]:
    return {n for n in (_norm(x) for x in names) if n}


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE LOADERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_rotowire(sport: str, date: str) -> dict:
    """
    Return {frozenset({away_abbr, home_abbr}): {abbr: [names]}} from rotowire_lineups.json.
    Empty dict if the file is absent.
    """
    path = PROJECT_ROOT / "data" / sport / date / "rotowire_lineups.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        games = json.load(f)

    out = {}
    for g in games:
        key = frozenset({g["away_abbr"], g["home_abbr"]})
        out[key] = {
            g["away_abbr"]: [p["name"] for p in g.get("away_order", [])],
            g["home_abbr"]: [p["name"] for p in g.get("home_order", [])],
            "_status": {
                g["away_abbr"]: g.get("away_status", "unknown"),
                g["home_abbr"]: g.get("home_status", "unknown"),
            },
        }
    return out


def _load_mlb_actual(sport: str, date: str) -> dict:
    """
    Return {frozenset({away_abbr, home_abbr}): {abbr: [names]}} from games.json,
    only for sides whose lineup status == 'confirmed'.
    """
    path = PROJECT_ROOT / "data" / sport / date / "games.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        games = json.load(f)

    out = {}
    for g in games:
        away_abbr = g["away"]["abbr"]
        home_abbr = g["home"]["abbr"]
        lineups = (g.get("context", {}) or {}).get("lineups", {}) or {}
        entry = {}
        for side, abbr in (("away", away_abbr), ("home", home_abbr)):
            side_lu = lineups.get(side) or {}
            if side_lu.get("status") == "confirmed":
                entry[abbr] = [p["name"] for p in side_lu.get("order", [])]
        if entry:
            out[frozenset({away_abbr, home_abbr})] = entry
    return out


def _load_regulars(date: str) -> dict:
    """
    Return {team_abbr: [starter names]} from lineup_tracker.txt.
    Uses the Role-based regular nine (predictive 'who normally starts').
    """
    if not _TRACKER_AVAILABLE:
        return {}
    tracker = load_lineup_tracker(date)
    out = {}
    for team, info in tracker.items():
        if team == "_meta":
            continue
        out[team] = [p["name"] for p in info.get("starters", [])]
    return out


# ─────────────────────────────────────────────────────────────────────────────
# COMPARISON
# ─────────────────────────────────────────────────────────────────────────────

def _compare_pair(predicted: list[str], actual: list[str]) -> dict | None:
    """
    Compare a predicted starting nine against the actual one.
    Returns match count, total, pct, and the symmetric differences (by name),
    or None if either side is empty.
    """
    if not predicted or not actual:
        return None
    pset = _norm_set(predicted)
    aset = _norm_set(actual)
    matched = pset & aset
    return {
        "match": len(matched),
        "of": len(aset),
        "pct": round(100 * len(matched) / len(aset), 1) if aset else 0.0,
        "missed": sorted(aset - pset),    # actual starters the prediction lacked
        "extra":  sorted(pset - aset),    # predicted starters who did not start
    }


def run(sport: str, date: str) -> dict:
    rotowire = _load_rotowire(sport, date)
    mlb      = _load_mlb_actual(sport, date)
    regulars = _load_regulars(date)

    # Coverage counts
    n_games = len(set(rotowire) | set(mlb))
    coverage = {
        "rotowire_games":      len(rotowire),
        "mlb_confirmed_games": len(mlb),
        "tracker_teams":       len(regulars),
    }

    games_out = []
    # Accumulators for slate-level accuracy
    rw_match, rw_total = 0, 0
    tr_match, tr_total = 0, 0

    all_keys = set(rotowire) | set(mlb)
    for key in all_keys:
        abbrs = sorted(key)
        team_results = {}
        for abbr in abbrs:
            actual_names = (mlb.get(key) or {}).get(abbr)
            if not actual_names:
                continue  # no confirmed actual -> can't score this team

            entry = {"actual_n": len(actual_names)}

            # EXPECTED (Rotowire) vs ACTUAL
            rw_names = (rotowire.get(key) or {}).get(abbr)
            rw_cmp = _compare_pair(rw_names, actual_names) if rw_names else None
            if rw_cmp:
                entry["rotowire_vs_actual"] = rw_cmp
                rw_match += rw_cmp["match"]
                rw_total += rw_cmp["of"]

            # REGULARS (tracker) vs ACTUAL
            tr_names = regulars.get(abbr)
            tr_cmp = _compare_pair(tr_names, actual_names) if tr_names else None
            if tr_cmp:
                entry["tracker_vs_actual"] = tr_cmp
                tr_match += tr_cmp["match"]
                tr_total += tr_cmp["of"]

            team_results[abbr] = entry

        if team_results:
            games_out.append({"matchup": "@".join(abbrs), "teams": team_results})

    summary = {
        "rotowire_vs_actual_pct": round(100 * rw_match / rw_total, 1) if rw_total else None,
        "tracker_vs_actual_pct":  round(100 * tr_match / tr_total, 1) if tr_total else None,
        "rotowire_scored_slots":  rw_total,
        "tracker_scored_slots":   tr_total,
    }

    report = {
        "sport":    sport,
        "date":     date,
        "games":    n_games,
        "coverage": coverage,
        "summary":  summary,
        "detail":   games_out,
    }

    # Write JSON
    out_dir = PROJECT_ROOT / "data" / sport / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "lineup_comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # ASCII-safe console summary
    print(f"\n{'-' * 55}")
    print(f"  LINEUP ACCURACY  {sport.upper()}  {date}")
    print(f"{'-' * 55}")
    print(f"  Coverage: rotowire={coverage['rotowire_games']}g, "
          f"mlb_confirmed={coverage['mlb_confirmed_games']}g, "
          f"tracker={coverage['tracker_teams']}teams")
    if summary["rotowire_vs_actual_pct"] is not None:
        print(f"  Rotowire (expected) vs actual: {summary['rotowire_vs_actual_pct']}% "
              f"over {summary['rotowire_scored_slots']} slots")
    else:
        print(f"  Rotowire vs actual: no overlap to score "
              f"(need pre-game rotowire capture + confirmed MLB lineups)")
    if summary["tracker_vs_actual_pct"] is not None:
        print(f"  Tracker (regulars) vs actual:  {summary['tracker_vs_actual_pct']}% "
              f"over {summary['tracker_scored_slots']} slots")
    else:
        print(f"  Tracker vs actual: no confirmed MLB lineups to score against")
    print(f"  Wrote -> {out_path.relative_to(PROJECT_ROOT)}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Compare lineup sources (sideline accuracy report).")
    parser.add_argument("--sport", default="mlb", help="Sport code (default: mlb)")
    parser.add_argument("--date",  required=True, help="Slate date YYYY-MM-DD")
    args = parser.parse_args()
    run(sport=args.sport, date=args.date)
    # Sideline diagnostic — never break the pipeline.
    sys.exit(0)


if __name__ == "__main__":
    main()

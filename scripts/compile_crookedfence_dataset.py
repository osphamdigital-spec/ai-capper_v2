#!/usr/bin/env python
"""
scripts/compile_crookedfence_dataset.py

Flattens every archived CrookedFence results file into ONE growing master
dataset for reverse-engineering their HR / runs edge model.

Each archived results file (data/{sport}/crookedfence_archive/YYYY-MM-DD_results.json)
already contains, per game, the full input features AND the graded outcome:
  - inputs:    weather (temp/wind/humidity/precip), stadium dimensions,
               both starters (hr9, era, whip, goao, k9, bb9, profile)
  - predicted: CrookedFence's signal, hr_edge %, runs_edge %
  - actual:    final HRs, total runs, away/home runs, status
  - verdict:   correct / partial / wrong

This script walks all those files and writes one row per game to:
  data/{sport}/crookedfence_dataset.csv    (flat, analysis-ready)
  data/{sport}/crookedfence_dataset.jsonl  (full nested records, lossless)

Rows are de-duplicated on (game_date, away, home) so re-running is safe and
idempotent as the archive grows. Once enough rows accumulate, this dataset is
what we use to model their edge (or to feed raw inputs to our own models).

Usage:
    python scripts/compile_crookedfence_dataset.py
    python scripts/compile_crookedfence_dataset.py --sport mlb
"""

import argparse
import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Flat CSV column order. Nested JSONL keeps everything; CSV is the analysis view.
CSV_COLUMNS = [
    "game_date", "away", "home", "stadium", "roof",
    # CrookedFence prediction
    "signal", "pred_hr_edge", "pred_runs_edge",
    # Actual outcome
    "actual_hrs", "actual_runs", "actual_away_runs", "actual_home_runs",
    "status", "verdict",
    # Weather inputs
    "temp_f", "wind_mph", "wind_from", "wind_effect", "humidity_pct",
    "pressure_hpa", "precip_pct",
    # Stadium dimensions
    "lf_ft", "cf_ft", "rf_ft",
    # Away starter
    "away_pitcher", "away_throws", "away_hr9", "away_era", "away_whip",
    "away_goao", "away_k9", "away_bb9", "away_profile",
    # Home starter
    "home_pitcher", "home_throws", "home_hr9", "home_era", "home_whip",
    "home_goao", "home_k9", "home_bb9", "home_profile",
]


def _flatten_game(game_date: str, g: dict) -> dict:
    """Flatten one nested results game into a single flat row dict."""
    wx   = g.get("weather") or {}
    dims = g.get("stadium_profile") or {}
    ap   = g.get("away_pitcher") or {}
    hp   = g.get("home_pitcher") or {}
    pred = g.get("predicted") or {}
    act  = g.get("actual") or {}

    return {
        "game_date":        game_date,
        "away":             g.get("away"),
        "home":             g.get("home"),
        "stadium":          g.get("stadium"),
        "roof":             g.get("roof"),
        "signal":           g.get("signal"),
        # prefer top-level edge, fall back to nested predicted{}
        "pred_hr_edge":     g.get("hr_edge",   pred.get("hr_edge")),
        "pred_runs_edge":   g.get("runs_edge", pred.get("runs_edge")),
        "actual_hrs":       act.get("hrs"),
        "actual_runs":      act.get("runs"),
        "actual_away_runs": act.get("away_runs"),
        "actual_home_runs": act.get("home_runs"),
        "status":           act.get("status"),
        "verdict":          g.get("verdict"),
        "temp_f":           wx.get("temp_f"),
        "wind_mph":         wx.get("wind_speed_mph"),
        "wind_from":        wx.get("wind_from"),
        "wind_effect":      wx.get("wind_effect"),
        "humidity_pct":     wx.get("humidity_pct"),
        "pressure_hpa":     wx.get("pressure_hpa"),
        "precip_pct":       wx.get("precip_pct"),
        "lf_ft":            dims.get("lf_ft"),
        "cf_ft":            dims.get("cf_ft"),
        "rf_ft":            dims.get("rf_ft"),
        "away_pitcher":     ap.get("name"),
        "away_throws":      ap.get("throws"),
        "away_hr9":         ap.get("hr9"),
        "away_era":         ap.get("era"),
        "away_whip":        ap.get("whip"),
        "away_goao":        ap.get("goao"),
        "away_k9":          ap.get("k9"),
        "away_bb9":         ap.get("bb9"),
        "away_profile":     ap.get("profile"),
        "home_pitcher":     hp.get("name"),
        "home_throws":      hp.get("throws"),
        "home_hr9":         hp.get("hr9"),
        "home_era":         hp.get("era"),
        "home_whip":        hp.get("whip"),
        "home_goao":        hp.get("goao"),
        "home_k9":          hp.get("k9"),
        "home_bb9":         hp.get("bb9"),
        "home_profile":     hp.get("profile"),
    }


def compile_dataset(sport: str):
    archive_dir = PROJECT_ROOT / "data" / sport / "crookedfence_archive"
    if not archive_dir.exists():
        print(f"  No archive directory at {archive_dir} — nothing to compile.")
        return

    results_files = sorted(archive_dir.glob("*_results.json"))
    if not results_files:
        print(f"  No *_results.json files in {archive_dir} yet.")
        return

    # De-dupe on (game_date, away, home). Later files overwrite earlier (in case
    # a result was corrected on a later fetch).
    rows: dict[tuple, dict] = {}      # flat rows for CSV
    records: dict[tuple, dict] = {}   # full nested records for JSONL

    for f in results_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  WARNING: could not parse {f.name}: {e}")
            continue

        game_date = data.get("date", f.stem.replace("_results", ""))
        for g in data.get("games", []):
            if not isinstance(g, dict):
                continue
            key = (game_date, g.get("away"), g.get("home"))
            rows[key]    = _flatten_game(game_date, g)
            records[key] = {"game_date": game_date, **g}

    # Sort by date then matchup for stable output
    ordered_keys = sorted(rows.keys(), key=lambda k: (k[0] or "", k[1] or "", k[2] or ""))

    # ── Write CSV ──────────────────────────────────────────────────────────────
    csv_path = PROJECT_ROOT / "data" / sport / "crookedfence_dataset.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for key in ordered_keys:
            writer.writerow(rows[key])

    # ── Write JSONL (lossless) ─────────────────────────────────────────────────
    jsonl_path = PROJECT_ROOT / "data" / sport / "crookedfence_dataset.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for key in ordered_keys:
            fh.write(json.dumps(records[key], ensure_ascii=False) + "\n")

    # ── Summary ────────────────────────────────────────────────────────────────
    dates = sorted({k[0] for k in ordered_keys})
    verdicts = {}
    for key in ordered_keys:
        v = rows[key].get("verdict")
        verdicts[v] = verdicts.get(v, 0) + 1

    print(f"  Compiled {len(ordered_keys)} games from {len(results_files)} results file(s)")
    print(f"  Date range : {dates[0]} .. {dates[-1]}" if dates else "  (no dates)")
    print(f"  Verdicts   : {verdicts}")
    print(f"  CSV   -> {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"  JSONL -> {jsonl_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compile archived CrookedFence results into a master reverse-engineering dataset."
    )
    parser.add_argument("--sport", default="mlb", help="Sport code (default: mlb)")
    args = parser.parse_args()
    compile_dataset(sport=args.sport)

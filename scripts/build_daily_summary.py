#!/usr/bin/env python3
"""
scripts/build_daily_summary.py

For each date in picks/mlb/YYYY-MM-DD/, produce a single combined text file:
  picks/mlb/YYYY-MM-DD/combined_YYYY-MM-DD.txt

The file contains:
  1. A header with the date
  2. Every model's raw picks (from *_raw.txt files), labelled clearly
  3. A results summary from results/mlb/YYYY-MM-DD/grades.json (if it exists)

Usage:
    python scripts/build_daily_summary.py               # all dates
    python scripts/build_daily_summary.py --date 2026-06-07
    python scripts/build_daily_summary.py --sport mlb   # default is mlb
"""

import argparse
import json
from pathlib import Path

# ── Path helpers ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent


def picks_dir(sport: str, date: str) -> Path:
    return PROJECT_ROOT / "picks" / sport / date


def results_dir(sport: str, date: str) -> Path:
    return PROJECT_ROOT / "results" / sport / date


# ── Formatting helpers ────────────────────────────────────────────────────────

DIVIDER      = "=" * 70
THIN_DIVIDER = "-" * 70


def fmt_grades(grades_path: Path) -> str:
    """
    Format the grades.json results block for one day.
    Shows overall record + best bet result for each model, then a summary table.
    """
    if not grades_path.exists():
        return "(no grades.json found for this date — run fetch_results.py)\n"

    with open(grades_path, encoding="utf-8") as f:
        data = json.load(f)

    lines = []
    models = data.get("models", {})

    # ── Per-model row ─────────────────────────────────────────────────────────
    lines.append(f"{'MODEL':<16} {'BETS':>4} {'W-L':>6} {'WIN%':>6} "
                 f"{'UNITS NET':>10} {'ROI':>7}  BEST BET")
    lines.append(THIN_DIVIDER)

    total_bets = total_wins = total_losses = 0
    total_units_net = 0.0

    for model, m in sorted(models.items()):
        bets   = m.get("bets", 0)
        wins   = m.get("wins", 0)
        losses = m.get("losses", 0)
        roi    = m.get("roi")
        u_net  = m.get("units_net", 0.0)
        bb_raw = m.get("best_bet_raw") or "—"
        bb_res = m.get("best_bet_wins", 0)
        bb_los = m.get("best_bet_losses", 0)
        bb_tag = ""
        if bb_res > 0:
            bb_tag = " [W]"
        elif bb_los > 0:
            bb_tag = " [L]"

        win_pct = f"{wins/bets:.0%}" if bets else "—"
        roi_str = f"{roi:+.0%}" if roi is not None else "—"
        u_str   = f"{u_net:+.2f}u"

        lines.append(
            f"{model:<16} {bets:>4} {wins}-{losses:>2}  {win_pct:>5} "
            f"  {u_str:>9}  {roi_str:>6}  {bb_raw}{bb_tag}"
        )

        total_bets   += bets
        total_wins   += wins
        total_losses += losses
        total_units_net += u_net

    # ── Totals row ────────────────────────────────────────────────────────────
    lines.append(THIN_DIVIDER)
    n_models = len(models)
    avg_roi  = (total_units_net / total_bets) if total_bets else 0
    lines.append(
        f"{'TOTAL / AVG':<16} {total_bets:>4} {total_wins}-{total_losses:<2}  "
        f"{'—':>5}   {total_units_net:>+8.2f}u  {avg_roi:>+6.0%}"
    )

    return "\n".join(lines) + "\n"


def fmt_raw_picks(date_picks_dir: Path) -> str:
    """
    Concatenate every *_raw.txt file in the picks folder, with clear separators.
    Files are sorted alphabetically by model name.
    """
    raw_files = sorted(date_picks_dir.glob("*_raw.txt"))
    if not raw_files:
        return "(no raw pick files found)\n"

    sections = []
    for f in raw_files:
        # Derive a clean model name from the filename (strip _raw.txt)
        model_name = f.stem.replace("_raw", "")
        header = f"\n{DIVIDER}\n  MODEL: {model_name.upper()}\n{DIVIDER}\n"
        content = f.read_text(encoding="utf-8").strip()
        sections.append(header + content)

    return "\n".join(sections) + "\n"


# ── Main builder ──────────────────────────────────────────────────────────────

def build_summary(sport: str, date: str) -> Path:
    """
    Build the combined summary file for one sport/date.
    Returns the path of the file written.
    """
    p_dir = picks_dir(sport, date)
    r_dir = results_dir(sport, date)

    output_path = p_dir / f"combined_{date}.txt"

    lines = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append(DIVIDER)
    lines.append(f"  {sport.upper()} PICKS & RESULTS — {date}")
    lines.append(DIVIDER)
    lines.append("")

    # ── Results section ───────────────────────────────────────────────────────
    lines.append("RESULTS SUMMARY")
    lines.append(THIN_DIVIDER)
    lines.append(fmt_grades(r_dir / "grades.json"))

    # ── Raw picks section ─────────────────────────────────────────────────────
    lines.append("")
    lines.append("RAW MODEL PICKS")
    lines.append(THIN_DIVIDER)
    lines.append(fmt_raw_picks(p_dir))

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build combined daily pick+result summaries.")
    parser.add_argument("--sport", default="mlb")
    parser.add_argument("--date",  default=None,
                        help="Single date YYYY-MM-DD. Omit to process all available dates.")
    args = parser.parse_args()

    if args.date:
        dates = [args.date]
    else:
        # Discover all date folders under picks/{sport}/
        base = PROJECT_ROOT / "picks" / args.sport
        dates = sorted(d.name for d in base.iterdir() if d.is_dir() and d.name[:4].isdigit())

    print(f"\nBuilding combined summaries for {args.sport.upper()} — {len(dates)} date(s)\n")

    for date in dates:
        p = picks_dir(args.sport, date)
        if not p.exists():
            print(f"  SKIP {date} — picks folder not found")
            continue
        out = build_summary(args.sport, date)
        print(f"  {date} -> {out.relative_to(PROJECT_ROOT)}")

    print("\nDone.\n")


if __name__ == "__main__":
    main()

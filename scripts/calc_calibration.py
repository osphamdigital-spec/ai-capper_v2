"""
calc_calibration.py — model calibration calculator

Reads all graded picks across every date for a given model (or all models)
and produces a one-paragraph calibration summary per model saved to
picks/calibration/{model}_calibration.md.

Usage:
  python scripts/calc_calibration.py --sport mlb
  python scripts/calc_calibration.py --sport mlb --model deepseek

Outputs:
  picks/calibration/{model}_calibration.md  (one file per model, refreshed on run)

Does NOT wire into post-mortems yet — standalone calculator only.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Minimum graded bets before calibration is considered reliable
MIN_SAMPLE = 20

# All known models — used when --model is not specified
ALL_MODELS = [
    "chatgpt", "deepseek", "gemini", "grok",
    "kimi", "opus", "qwen", "sonnet",
    # Legacy names that appear in early dates
    "chatgpt5.5", "gpt-5.2-high", "manus", "fable",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def parse_edge_pts(edge_str: str) -> float | None:
    """
    Parse the model's stated edge into a float number of percentage points.

    Two formats exist:
      New (Jun 10+): "8.1 pts", "6.2 pts"  → 8.1, 6.2
      Old (pre-Jun 10): "strong", "real", "medium" → mapped to rough equivalents
        for continuity; flagged as estimated.
    Returns None when edge is "none" or absent.
    """
    if not edge_str:
        return None
    s = edge_str.strip().lower()
    if s in ("none", "n/a", "pass"):
        return None
    # Numeric format: "8.1 pts" or "8.1"
    m = re.search(r"(\d+\.?\d*)\s*pt", s)
    if m:
        return float(m.group(1))
    # Legacy word labels — rough midpoint estimates for continuity
    label_map = {
        "strong": 9.0,    # historically labelled "strong" = large edge
        "real":   5.5,    # "real" = meaningful but not huge
        "medium": 4.5,
        "slight": 3.5,
    }
    for label, val in label_map.items():
        if label in s:
            return val
    return None


def load_picks_for_model(sport: str, model: str) -> list[dict]:
    """
    Walk picks/{sport}/*/  and collect all picks from {model}.json files.
    Returns a flat list of pick dicts, each augmented with 'date' and 'model'.
    """
    picks_dir = PROJECT_ROOT / "picks" / sport
    if not picks_dir.exists():
        return []

    all_picks = []
    # Iterate dates in chronological order
    for date_dir in sorted(picks_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        picks_file = date_dir / f"{model}.json"
        if not picks_file.exists():
            continue
        try:
            data = json.loads(picks_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"  WARN: could not read {picks_file}")
            continue
        date_str = data.get("date", date_dir.name)
        for p in data.get("picks", []):
            p = dict(p)            # shallow copy so we don't mutate the source
            p["_date"]  = date_str
            p["_model"] = model
            all_picks.append(p)

    return all_picks


def compute_calibration(model: str, picks: list[dict]) -> dict:
    """
    Compute calibration stats from a flat list of picks for one model.

    A pick counts as 'graded' when action == 'bet' AND result in
    ('win', 'loss', 'push').  Voids are excluded from win/loss counting
    but noted.  Leans and passes are excluded entirely.

    Returns a stats dict.
    """
    graded = [
        p for p in picks
        if p.get("action") == "bet"
        and p.get("result") in ("win", "loss", "push")
    ]
    voids = [
        p for p in picks
        if p.get("action") == "bet" and p.get("result") == "void"
    ]
    ungraded = [
        p for p in picks
        if p.get("action") == "bet"
        and p.get("result") not in ("win", "loss", "push", "void")
    ]

    wins   = [p for p in graded if p.get("result") == "win"]
    losses = [p for p in graded if p.get("result") == "loss"]
    pushes = [p for p in graded if p.get("result") == "push"]

    # Unit-weighted ROI: profit / units_risked
    units_risked = sum(p.get("units", 0) or 0 for p in graded)
    units_net    = sum(p.get("profit_units", 0) or 0 for p in graded)
    roi_pct      = (units_net / units_risked * 100) if units_risked > 0 else None

    # Average stated edge (numeric pts) — parse from edge field
    edge_values = []
    edge_estimated_count = 0
    for p in graded:
        raw = p.get("edge", "")
        val = parse_edge_pts(raw)
        if val is not None:
            # Flag if derived from old word label rather than numeric
            if raw and not re.search(r"\d", raw):
                edge_estimated_count += 1
            edge_values.append(val)
    avg_edge = (sum(edge_values) / len(edge_values)) if edge_values else None

    # CLV: pick_price - closing_price in American-odds cents, positive = beating market
    # Only available when grade_picks.py has run with a closing snapshot
    clv_values = [
        p["clv"] for p in graded
        if p.get("clv") is not None
    ]
    avg_clv    = (sum(clv_values) / len(clv_values)) if clv_values else None
    clv_count  = len(clv_values)

    return {
        "model":               model,
        "total_graded":        len(graded),
        "wins":                len(wins),
        "losses":              len(losses),
        "pushes":              len(pushes),
        "voids":               len(voids),
        "ungraded_bets":       len(ungraded),
        "units_risked":        round(units_risked, 2),
        "units_net":           round(units_net, 4),
        "roi_pct":             round(roi_pct, 1) if roi_pct is not None else None,
        "avg_edge_pts":        round(avg_edge, 1) if avg_edge is not None else None,
        "edge_sample":         len(edge_values),
        "edge_has_estimates":  edge_estimated_count > 0,
        "avg_clv":             round(avg_clv, 1) if avg_clv is not None else None,
        "clv_count":           clv_count,
    }


def build_summary_paragraph(stats: dict) -> str:
    """
    Build the one-paragraph calibration summary string for one model.
    This is what gets injected into post-mortems once the mechanism is wired in.
    """
    n        = stats["total_graded"]
    model    = stats["model"]
    wins     = stats["wins"]
    losses   = stats["losses"]
    pushes   = stats["pushes"]
    voids    = stats["voids"]
    ungraded = stats["ungraded_bets"]

    if n == 0:
        lines = [
            f"CALIBRATION — {model.upper()}",
            "",
            "No graded bets on record yet. Calibration will be available once bets are graded.",
        ]
        if ungraded:
            lines.append(f"({ungraded} bet(s) pending grading.)")
        return "\n".join(lines)

    # ── Record and ROI line ────────────────────────────────────────────────
    record_str = f"{wins}-{losses}"
    if pushes:
        record_str += f"-{pushes}P"

    roi = stats["roi_pct"]
    roi_str = f"{roi:+.1f}%" if roi is not None else "N/A"

    units_net = stats["units_net"]
    units_net_str = f"{units_net:+.2f}u"

    line1 = (
        f"Across your last {n} graded bet(s): record {record_str}, "
        f"unit-weighted ROI {roi_str} ({units_net_str} on {stats['units_risked']}u risked)."
    )

    # ── Edge calibration line ──────────────────────────────────────────────
    avg_edge = stats["avg_edge_pts"]
    if avg_edge is not None:
        est_note = " (some values estimated from pre-Jun-10 word labels)" if stats["edge_has_estimates"] else ""
        line2 = f"Average stated edge: {avg_edge} pts{est_note}."
    else:
        line2 = "Average stated edge: not yet computable (edge field absent or all non-numeric)."

    # ── CLV line ──────────────────────────────────────────────────────────
    avg_clv   = stats["avg_clv"]
    clv_count = stats["clv_count"]
    if avg_clv is not None:
        clv_sign = "+" if avg_clv >= 0 else ""
        line3 = (
            f"Closing line value (pick price vs closing snapshot): "
            f"avg {clv_sign}{avg_clv:.1f} cents over {clv_count} bet(s). "
            f"{'Positive CLV = buying better than closing price on average.' if avg_clv > 0 else 'Negative CLV = closing price moved against picks on average.'}"
        )
    else:
        line3 = "CLV: not yet available (closing line data absent or grade_picks.py not run)."

    # ── Sample size warning ────────────────────────────────────────────────
    if n < MIN_SAMPLE:
        sample_note = (
            f"PROVISIONAL — sample too small for reliable calibration "
            f"({n} of ~{MIN_SAMPLE} minimum graded bets). "
            f"Treat all figures as directional only."
        )
    else:
        sample_note = None

    # ── Void / ungraded footnote ───────────────────────────────────────────
    footnotes = []
    if voids:
        footnotes.append(f"{voids} void(s) excluded from record")
    if ungraded:
        footnotes.append(f"{ungraded} bet(s) pending grading")

    # ── Assemble ──────────────────────────────────────────────────────────
    lines = [
        f"CALIBRATION — {model.upper()}",
        "",
        line1,
        line2,
        line3,
    ]
    if sample_note:
        lines.append(sample_note)
    if footnotes:
        lines.append("(" + "; ".join(footnotes) + ".)")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run(sport: str, model: str | None = None):
    out_dir = PROJECT_ROOT / "picks" / "calibration"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Decide which models to process
    if model:
        models = [model]
    else:
        # Discover models that actually have picks files for this sport
        picks_dir = PROJECT_ROOT / "picks" / sport
        found = set()
        if picks_dir.exists():
            for date_dir in picks_dir.iterdir():
                if date_dir.is_dir():
                    for f in date_dir.glob("*.json"):
                        # Exclude calibration/ and non-pick files
                        if f.stem not in ("grades", "results"):
                            found.add(f.stem)
        # Canonical models first, then any others discovered
        ordered = [m for m in ALL_MODELS if m in found]
        ordered += sorted(found - set(ALL_MODELS))
        models = ordered

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for m in models:
        picks  = load_picks_for_model(sport, m)
        stats  = compute_calibration(m, picks)
        para   = build_summary_paragraph(stats)

        # ── Save to file ──────────────────────────────────────────────────
        out_path = out_dir / f"{m}_calibration.md"
        roi_str2    = f"{stats['roi_pct']:+.1f}%"    if stats['roi_pct']    is not None else "N/A"
        edge_str2   = f"{stats['avg_edge_pts']} pts" if stats['avg_edge_pts'] is not None else "N/A"
        clv_str2    = f"{stats['avg_clv']:+.1f}"     if stats['avg_clv']     is not None else "N/A"
        content = (
            f"# Calibration — {m} ({sport.upper()})\n"
            f"Generated: {now_str}\n\n"
            f"{para}\n\n"
            f"---\n\n"
            f"## Raw stats\n\n"
            f"| Metric | Value |\n"
            f"|---|---|\n"
            f"| Graded bets | {stats['total_graded']} |\n"
            f"| Record (W-L-P) | {stats['wins']}-{stats['losses']}-{stats['pushes']} |\n"
            f"| Units risked | {stats['units_risked']} |\n"
            f"| Units net | {stats['units_net']:+.4f} |\n"
            f"| Unit-weighted ROI | {roi_str2} |\n"
            f"| Avg stated edge | {edge_str2} |\n"
            f"| Avg CLV (cents) | {clv_str2} |\n"
            f"| CLV sample | {stats['clv_count']} bets |\n"
            f"| Voids | {stats['voids']} |\n"
            f"| Ungraded bets | {stats['ungraded_bets']} |\n"
        )
        out_path.write_text(content, encoding="utf-8")

        # ── Print to console ──────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(para)
        print(f"{'='*60}")

    print(f"\nCalibration files saved to {out_dir}/")


def main():
    parser = argparse.ArgumentParser(description="Compute model calibration from graded picks history.")
    parser.add_argument("--sport",  default="mlb",  help="Sport code (default: mlb)")
    parser.add_argument("--model",  default=None,   help="Single model (default: all)")
    args = parser.parse_args()
    run(sport=args.sport, model=args.model)


if __name__ == "__main__":
    main()

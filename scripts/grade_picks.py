#!/usr/bin/env python
"""
scripts/grade_picks.py

Grade all model picks for a given date against final results.

For each real bet (units >= 1):
  - Determines WIN / LOSS / PUSH from the game result
  - Calculates profit/loss in units using standard sports betting payout formula
  - Calculates CLV (our pick price vs current_snapshot — best proxy without
    a paid closing line feed)

Also tracks each model's ## SLATE SUMMARY best bet separately.

Writes:
  picks/{sport}/{date}/{model}.json      -- updated with graded fields per pick
  results/{sport}/{date}/grades.json     -- per-model leaderboard summary
  results/{sport}/{date}/best_bets.json  -- per-model best bet results

Usage:
  python scripts/grade_picks.py --date 2026-06-02
  python scripts/grade_picks.py --sport mlb --date 2026-06-02

Run after fetch_results.py (games need result blocks) and log_picks.py
(picks need to be parsed JSON — not raw text).
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

def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def win_profit(price: int, units: int | float) -> float:
    """
    Profit in units for a winning bet.
    +130 on 1u → +1.30u.  -150 on 1u → +0.667u.
    """
    if price > 0:
        return round(units * (price / 100), 4)
    else:
        return round(units * (100 / abs(price)), 4)


def fmt_record(wins: int, losses: int) -> str:
    """
    Format a W-L record with win percentage.
    Pushes are excluded from the percentage (they don't affect edge).
    Returns '—' when no graded bets exist yet.

    Examples:
      fmt_record(3, 1) -> "3-1 (75.0%)"
      fmt_record(0, 0) -> "—"
    """
    total = wins + losses
    if total == 0:
        return "—"
    pct = wins / total * 100
    return f"{wins}-{losses} ({pct:.1f}%)"


def find_best_bet_pick(best_bet_raw: str, picks: list, name_to_abbr: dict | None = None) -> dict | None:
    """
    Match a model's SLATE SUMMARY best bet string to its graded pick object.

    Strategy 1 (reliable): extract the game matchup from the "(AWAY @ HOME)"
    parenthetical that all models include, then find that game's pick.

    Strategy 2 (fallback): scan the first few tokens for a team abbreviation
    and match to any bet pick where that abbr is the picked side.

    Examples of best_bet_raw strings across models:
      "MIL -1.5 +118 — Game 9 (SF @ MIL), 3 units"
      "PIT ML — Game 13 (PIT @ HOU), 1 unit"
      "CHW ML -118 3u — Game 8 (CHW @ MIN)"
    """
    if not best_bet_raw:
        return None

    # Strategy 1 — look for "AWAY @ HOME" inside parentheses (ignores any prefix like "GAME:")
    m = re.search(r'\([^)]*\b([A-Z]{1,5})\s*@\s*([A-Z]{1,5})\b[^)]*\)', best_bet_raw)
    if m:
        matchup = f"{m.group(1)} @ {m.group(2)}"
        for pick in picks:
            if pick.get("matchup") == matchup and pick.get("action") == "bet":
                return pick

    # Strategy 2 — scan first 4 tokens for a recognisable team abbreviation
    tokens = best_bet_raw.upper().split()[:4]
    for pick in picks:
        if pick.get("action") != "bet":
            continue
        away = (pick.get("away_abbr") or "").upper()
        home = (pick.get("home_abbr") or "").upper()
        if away in tokens or home in tokens:
            return pick

    # Strategy 3 — match on full team name using the name->abbr map.
    # Some models write "Los Angeles Dodgers ML" instead of "LAD ML".
    # Translate any known full name found in the string to its abbreviation,
    # then re-run the abbreviation check against bet picks.
    if name_to_abbr:
        raw_upper = best_bet_raw.upper()
        matched_abbrs = {abbr for name, abbr in name_to_abbr.items() if name in raw_upper}
        for pick in picks:
            if pick.get("action") != "bet":
                continue
            away = (pick.get("away_abbr") or "").upper()
            home = (pick.get("home_abbr") or "").upper()
            if away in matched_abbrs or home in matched_abbrs:
                return pick

    return None


# ─────────────────────────────────────────────────────────────────────────────
# GAME INDEX — keyed by game_id, built from games.json
# ─────────────────────────────────────────────────────────────────────────────

def build_game_index(sport: str, date: str, root: Path) -> dict:
    """
    Build a lookup keyed by game_id containing result + odds data.
    Includes final games (gradeable) and postponed/cancelled/suspended games
    (so grade_picks can mark those picks VOID rather than silently skipping them).
    """
    path = root / "data" / sport / date / "games.json"
    if not path.exists():
        print(f"ERROR: {path} not found.")
        print("  Run fetch_results.py first to populate result blocks.")
        sys.exit(1)

    # Statuses treated as VOID — no result, units returned
    VOID_STATUSES = {"postponed", "cancelled", "suspended"}

    games = json.loads(path.read_text(encoding="utf-8"))
    idx   = {}
    for g in games:
        r      = g.get("result", {})
        status = r.get("status")
        if status != "final" and status not in VOID_STATUSES:
            continue
        idx[g["game_id"]] = {
            "matchup":    f"{g['away']['abbr']} @ {g['home']['abbr']}",
            "away_abbr":  g["away"]["abbr"],
            "home_abbr":  g["home"]["abbr"],
            "away_score": r.get("away_score"),
            "home_score": r.get("home_score"),
            "winner":     r.get("winner"),
            "status":     status,       # "final" | "postponed" | "cancelled" | "suspended"
            "odds":       g.get("odds", {}),
        }
    return idx


# ─────────────────────────────────────────────────────────────────────────────
# OUTCOME DETERMINATION
# ─────────────────────────────────────────────────────────────────────────────

def determine_outcome(
    pick_side: str | None,
    pick_market: str | None,
    pick_raw: str,
    away_score: int,
    home_score: int,
    winner: str,
    odds: dict,
) -> str | None:
    """
    Determine WIN / LOSS / PUSH. Returns None if the pick can't be resolved.

    ML  — straight win/loss based on which team won.
    RL  — always ±1.5 in MLB; infer which side from "-1.5"/"+1.5" in pick_raw.
    Total — compare combined runs to the opening total line from games.json.
    """
    if pick_market == "ml":
        if pick_side == "away":
            return "win" if winner == "away" else "loss"
        elif pick_side == "home":
            return "win" if winner == "home" else "loss"

    elif pick_market == "rl":
        run_diff = away_score - home_score   # positive = away won
        if pick_side == "away":
            if "-1.5" in pick_raw:
                return "win" if run_diff >= 2 else "loss"
            else:
                return "win" if run_diff > -2 else "loss"
        elif pick_side == "home":
            if "-1.5" in pick_raw:
                return "win" if run_diff <= -2 else "loss"
            else:
                return "win" if run_diff < 2 else "loss"

    elif pick_market == "total":
        total_line = (
            odds.get("opening_snapshot", {})
                .get("total", {})
                .get("line")
        )
        if total_line is None:
            return None
        total_runs = away_score + home_score
        if total_runs > total_line:
            return "win" if pick_side == "over" else "loss"
        elif total_runs < total_line:
            return "win" if pick_side == "under" else "loss"
        else:
            return "push"

    return None


def get_closing_price(pick_side: str, pick_market: str, odds: dict) -> int | None:
    """
    Retrieve the closing price for CLV calculation from current_snapshot.
    CLV = pick_price - closing_price (positive = we beat the market).
    """
    snap = odds.get("current_snapshot", {})
    if not snap:
        return None
    if pick_market == "ml":
        return snap.get("moneyline", {}).get(pick_side)
    elif pick_market == "rl":
        key = "away_price" if pick_side == "away" else "home_price"
        return snap.get("runline", {}).get(key)
    elif pick_market == "total":
        key = "over_price" if pick_side == "over" else "under_price"
        return snap.get("total", {}).get(key)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE BET GRADER
# ─────────────────────────────────────────────────────────────────────────────

def grade_single(pick: dict, game: dict) -> tuple:
    """Grade one pick. Returns (outcome, profit_units, clv, closing_line)."""
    if pick.get("action") != "bet":
        return None, 0.0, None, None

    pick_side   = pick.get("pick_side")
    pick_market = pick.get("pick_market")
    pick_raw    = pick.get("pick_raw", "")
    price       = pick.get("price")
    units       = pick.get("units", 0)

    if not pick_side or not pick_market:
        return None, 0.0, None, None

    outcome = determine_outcome(
        pick_side, pick_market, pick_raw,
        game["away_score"], game["home_score"],
        game["winner"], game["odds"],
    )
    if outcome is None:
        return None, 0.0, None, None

    if outcome == "win" and price is not None:
        profit = win_profit(price, units)
    elif outcome == "loss":
        profit = -float(units)
    else:
        profit = 0.0

    closing = get_closing_price(pick_side, pick_market, game["odds"])
    clv     = (price - closing) if (price is not None and closing is not None) else None

    return outcome, round(profit, 4), clv, closing


# ─────────────────────────────────────────────────────────────────────────────
# PARLAY GRADER
# ─────────────────────────────────────────────────────────────────────────────

def grade_parlay(parlay: dict, picks: list) -> tuple[str | None, float]:
    """
    Grade a parlay by checking if all legs won.
    Matches legs to graded singles by team abbreviation.
    """
    if not parlay:
        return None, 0.0

    units = parlay.get("units", 1)
    legs  = [parlay.get("leg1", ""), parlay.get("leg2", "")]

    abbr_outcome = {}
    for p in picks:
        if p.get("action") != "bet":
            continue
        side = p.get("pick_side")
        abbr = p.get("away_abbr") if side == "away" else p.get("home_abbr")
        if abbr and p.get("result"):
            abbr_outcome[abbr.upper()] = p["result"]

    leg_outcomes = []
    for leg in legs:
        if not leg:
            continue
        leg_upper = leg.upper()
        matched   = False
        for abbr, outcome in abbr_outcome.items():
            if abbr in leg_upper.split():
                leg_outcomes.append(outcome)
                matched = True
                break
        if not matched:
            return "void", 0.0

    if len(leg_outcomes) < 2:
        return "void", 0.0
    if any(o == "loss" for o in leg_outcomes):
        return "loss", -float(units)
    if all(o == "win" for o in leg_outcomes):
        combined = parlay.get("combined_price")
        profit   = win_profit(combined, units) if (combined and combined > 0) else float(units)
        return "win", round(profit, 4)

    return "void", 0.0


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def grade_picks(sport: str = "mlb", date: str = None):
    target_date = date or today_et()

    print(f"\n{'='*55}")
    print(f"  GRADE PICKS  {sport.upper()}  {target_date}")
    print(f"{'='*55}\n")

    root      = Path(__file__).parent.parent
    picks_dir = root / "picks" / sport / target_date

    if not picks_dir.exists():
        print(f"ERROR: {picks_dir} not found.")
        print("  Run log_picks.py first.")
        sys.exit(1)

    print("Step 1: Loading game results from games.json...")
    game_index = build_game_index(sport, target_date, root)
    print(f"  {len(game_index)} final game(s) available for grading\n")

    # Build full-name -> abbr map for Strategy 3 best-bet resolution.
    # Covers cases where a model writes "Los Angeles Dodgers ML" instead of "LAD ML".
    _games_raw = json.loads(
        (root / "data" / sport / target_date / "games.json").read_text(encoding="utf-8")
    )
    name_to_abbr: dict[str, str] = {}
    for _g in _games_raw:
        name_to_abbr[_g["away"]["name"].upper()] = _g["away"]["abbr"].upper()
        name_to_abbr[_g["home"]["name"].upper()] = _g["home"]["abbr"].upper()

    pick_files = sorted(
        f for f in picks_dir.glob("*.json") if "_raw" not in f.name
    )
    if not pick_files:
        print("ERROR: no parsed pick JSON files found. Run log_picks.py first.")
        sys.exit(1)

    print(f"Step 2: Grading {len(pick_files)} model file(s)...\n")

    graded_at      = now_utc()
    all_stats      = {}
    best_bets_list = []   # one entry per model, for best_bets.json
    model_lines    = []   # buffered per-model one-liners, printed after all models graded

    for pf in pick_files:
        try:
            doc = json.loads(pf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  SKIP {pf.name} — not valid JSON (run log_picks.py first)")
            continue
        if "picks" not in doc or "model" not in doc:
            print(f"  SKIP {pf.name} — missing 'picks' or 'model' field")
            continue

        model  = doc["model"]
        picks  = doc.get("picks", [])
        parlay = doc.get("parlay")

        # ── Grade singles ─────────────────────────────────────────────────────
        wins = losses = pushes = voids = 0
        units_risked = units_net = 0.0
        clv_values   = []
        # Per-tier accumulators: [wins, losses, units_risked, units_net]
        unit_records = {1: [0, 0, 0.0, 0.0], 3: [0, 0, 0.0, 0.0]}

        for pick in picks:
            game = game_index.get(pick.get("game_id"))
            if not game:
                continue

            # Postponed/cancelled/suspended — VOID: units returned, no win/loss
            if game.get("status") != "final":
                pick["result"]       = "void"
                pick["profit_units"] = 0.0
                pick["reason"]       = game["status"]   # "postponed" / "cancelled" etc.
                pick["clv"]          = None
                pick["closing_line"] = None
                pick["graded_at"]    = graded_at
                if pick.get("action") == "bet":
                    voids += 1
                continue

            outcome, profit, clv, closing = grade_single(pick, game)

            pick["result"]       = outcome
            pick["profit_units"] = profit
            pick["clv"]          = clv
            pick["closing_line"] = closing
            pick["graded_at"]    = graded_at

            if outcome is None:
                continue

            u = pick.get("units", 0)
            units_risked += u
            units_net    += profit

            if outcome == "win":
                wins += 1
                if u in unit_records:
                    unit_records[u][0] += 1
                    unit_records[u][2] += u
                    unit_records[u][3] += profit
            elif outcome == "loss":
                losses += 1
                if u in unit_records:
                    unit_records[u][1] += 1
                    unit_records[u][2] += u
                    unit_records[u][3] += profit
            elif outcome == "push":
                pushes += 1

            if clv is not None:
                clv_values.append(clv)

        # ── Grade parlay ──────────────────────────────────────────────────────
        if parlay:
            p_outcome, p_profit = grade_parlay(parlay, picks)
            parlay["result"]       = p_outcome
            parlay["profit_units"] = p_profit
            parlay["graded_at"]    = graded_at
            pu = parlay.get("units", 0)
            units_risked += pu
            units_net    += p_profit
            if p_outcome == "win":
                wins += 1
            elif p_outcome == "loss":
                losses += 1

        # ── Resolve best bet ──────────────────────────────────────────────────
        # Each model's ## SLATE SUMMARY declares their highest-conviction pick.
        # We find the matching graded single and record it separately so we can
        # track whether models' stated best bets outperform their full card.
        #
        # v3.1+: if the model found no 3-unit play, best_bet_skip=True in the doc.
        # Treat that as an explicit skip — do not count as unresolved.
        is_best_bet_skip = bool(doc.get("best_bet_skip"))

        best_bet_doc     = (doc.get("best_bet") or {}) if not is_best_bet_skip else {}
        best_bet_raw_str = best_bet_doc.get("best_bet", "")
        best_pick        = find_best_bet_pick(best_bet_raw_str, picks, name_to_abbr) if not is_best_bet_skip else None
        best_bet_result  = best_pick.get("result")       if best_pick else None
        best_bet_profit  = best_pick.get("profit_units", 0.0) if best_pick else 0.0
        best_bet_units   = best_pick.get("units", 0)    if best_pick else 0

        # A voided best bet (postponed game) is unresolved — counts neither W nor L
        bb_w = 1 if best_bet_result == "win"  else 0
        bb_l = 1 if best_bet_result == "loss" else 0
        bb_p = 1 if best_bet_result == "push" else 0

        # Collect for best_bets.json
        best_bets_list.append({
            "model":          model,
            "skip":           is_best_bet_skip,
            "skip_reason":    doc.get("best_bet_skip_reason") if is_best_bet_skip else None,
            "best_bet_raw":   best_bet_raw_str,
            "why_this":       best_bet_doc.get("why_this", ""),
            "resolved_game":  best_pick.get("matchup")   if best_pick else None,
            "resolved_pick":  best_pick.get("pick_raw")  if best_pick else None,
            "resolved_price": best_pick.get("price")     if best_pick else None,
            "resolved_units": best_bet_units,
            "result":         best_bet_result,
            "profit_units":   best_bet_profit,
        })

        # ── Save graded picks back to file ────────────────────────────────────
        doc["parlay"]    = parlay
        doc["graded_at"] = graded_at
        pf.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

        # ── Compute per-model stats ───────────────────────────────────────────
        total_bets  = wins + losses + pushes
        win_rate    = round(wins / total_bets, 4) if total_bets > 0 else 0.0
        roi         = round(units_net / units_risked, 4) if units_risked > 0 else 0.0
        avg_clv     = round(sum(clv_values) / len(clv_values), 1) if clv_values else None
        pos_clv_pct = (
            round(sum(1 for c in clv_values if c > 0) / len(clv_values), 4)
            if clv_values else None
        )
        # Guard against None profit (e.g. best bet was voided) and zero units
        bb_roi = (
            round(best_bet_profit / best_bet_units, 4)
            if (best_bet_units > 0 and best_bet_profit is not None)
            else None
        )

        counts = doc.get("counts", {})
        stats  = {
            "model":            model,
            "bets":             total_bets,
            "bets_placed":      counts.get("bets", total_bets),
            "leans":            counts.get("leans", 0),
            "passes":           counts.get("passes", 0),
            "wins":             wins,
            "losses":           losses,
            "pushes":           pushes,
            "voids":            voids,
            "units_risked":     round(units_risked, 2),
            "units_net":        round(units_net, 4),
            "win_rate":         win_rate,
            "roi":              roi,
            "avg_clv":          avg_clv,
            "positive_clv_pct": pos_clv_pct,
            # Nested tier breakdown (v3.1 schema — 5u tier removed)
            "tiers": {
                "1u": {
                    "wins":           unit_records[1][0],
                    "losses":         unit_records[1][1],
                    "pushes":         0,
                    "units_risked":   round(unit_records[1][2], 2),
                    "units_returned": round(unit_records[1][2] + unit_records[1][3], 4),
                    "roi_pct":        round(unit_records[1][3] / unit_records[1][2] * 100, 2) if unit_records[1][2] > 0 else None,
                },
                "3u": {
                    "wins":           unit_records[3][0],
                    "losses":         unit_records[3][1],
                    "pushes":         0,
                    "units_risked":   round(unit_records[3][2], 2),
                    "units_returned": round(unit_records[3][2] + unit_records[3][3], 4),
                    "roi_pct":        round(unit_records[3][3] / unit_records[3][2] * 100, 2) if unit_records[3][2] > 0 else None,
                },
                "best_bet": {
                    "wins":           bb_w,
                    "losses":         bb_l,
                    "pushes":         bb_p,
                    "units_risked":   float(best_bet_units),
                    "units_returned": round(float(best_bet_units) + (best_bet_profit or 0.0), 4),
                    "roi_pct":        round(bb_roi * 100, 2) if bb_roi is not None else None,
                    "skips":          1 if is_best_bet_skip else 0,
                },
            },
            "overall": {
                "wins":           wins,
                "losses":         losses,
                "pushes":         pushes,
                "units_risked":   round(units_risked, 2),
                "units_returned": round(units_risked + units_net, 4),
                "roi_pct":        round(roi * 100, 2) if units_risked > 0 else None,
            },
            # Flat best_bet fields used by display and aggregate calculations below
            "best_bet_raw":           best_bet_raw_str,
            "best_bet_skip":          is_best_bet_skip,
            "best_bet_wins":          bb_w,
            "best_bet_losses":        bb_l,
            "best_bet_pushes":        bb_p,
            "best_bet_units_wagered": float(best_bet_units),
            "best_bet_units_result":  best_bet_profit,
            "best_bet_roi":           bb_roi,
        }
        all_stats[model] = stats

        # Buffer per-model one-liner — printed after all models so we can
        # conditionally show the V column only when the slate had voids.
        net_s    = f"+{units_net:.2f}" if units_net >= 0 else f"{units_net:.2f}"
        roi_s    = f"+{roi*100:.1f}%" if roi >= 0 else f"{roi*100:.1f}%"
        if best_bet_result == "void":
            bb_res_s = "unresolved"
        elif is_best_bet_skip:
            bb_res_s = "SKIP"
        elif best_bet_result:
            bb_res_s = best_bet_result.upper()
        elif total_bets == 0 and not best_bet_raw_str:
            bb_res_s = "—"          # model submitted no picks at all
        else:
            bb_res_s = "unresolved"  # picks exist but best bet couldn't be matched
        model_lines.append({
            "model": model, "wins": wins, "losses": losses,
            "pushes": pushes, "voids": voids,
            "units_risked": units_risked, "net_s": net_s,
            "roi_s": roi_s, "bb_res_s": bb_res_s,
        })

    # ── Write grades.json ─────────────────────────────────────────────────────
    results_dir = root / "results" / sport / target_date
    results_dir.mkdir(parents=True, exist_ok=True)
    grades_path = results_dir / "grades.json"
    total_bb_skips = sum(1 for s in all_stats.values() if s.get("best_bet_skip"))
    grades_doc  = {
        "date":             target_date,
        "sport":            sport,
        "graded_at":        graded_at,
        "best_bet_skips":   total_bb_skips,
        "models":           all_stats,
    }
    grades_path.write_text(json.dumps(grades_doc, indent=2), encoding="utf-8")
    print(f"\nStep 3: Saved -> {grades_path.relative_to(root)}")

    # ── Write best_bets.json ──────────────────────────────────────────────────
    bb_wins   = sum(1 for b in best_bets_list if b["result"] == "win")
    bb_losses = sum(1 for b in best_bets_list if b["result"] == "loss")
    bb_skips  = sum(1 for b in best_bets_list if b.get("skip"))
    bb_path   = results_dir / "best_bets.json"
    bb_doc    = {
        "date":      target_date,
        "sport":     sport,
        "graded_at": graded_at,
        "best_bets": best_bets_list,
        "summary": {
            "wins":    bb_wins,
            "losses":  bb_losses,
            "skips":   bb_skips,
            "record":  fmt_record(bb_wins, bb_losses),
        },
    }
    bb_path.write_text(json.dumps(bb_doc, indent=2), encoding="utf-8")
    print(f"         Saved -> {bb_path.relative_to(root)}\n")

    # ── Flush per-model one-liners ────────────────────────────────────────────
    # Printed here so we can conditionally include the V column based on slate data
    any_voids = any(m["voids"] > 0 for m in model_lines)
    for m in model_lines:
        if any_voids:
            print(f"  {m['model']:<20}  {m['wins']}W {m['losses']}L {m['pushes']}P {m['voids']}V  "
                  f"{m['units_risked']:.0f}u  {m['net_s']}u  {m['roi_s']}  "
                  f"best bet: {m['bb_res_s']}")
        else:
            print(f"  {m['model']:<20}  {m['wins']}W {m['losses']}L {m['pushes']}P  "
                  f"{m['units_risked']:.0f}u  {m['net_s']}u  {m['roi_s']}  "
                  f"best bet: {m['bb_res_s']}")

    # ── Leaderboard ───────────────────────────────────────────────────────────
    ranked = sorted(all_stats.values(), key=lambda s: s["units_net"], reverse=True)

    if any_voids:
        hdr = (f"  {'Model':<18}  {'Bets':>4}  {'Record':<17}  {'Win%':>8}  "
               f"{'Risked':>6}  {'Net':>7}  {'ROI':>7}  {'Best Bet':<14}")
        sep = (f"  {'-'*18}  {'-'*4}  {'-'*17}  {'-'*8}  "
               f"{'-'*6}  {'-'*7}  {'-'*7}  {'-'*14}")
    else:
        hdr = (f"  {'Model':<18}  {'Bets':>4}  {'Record':<14}  {'Win%':>8}  "
               f"{'Risked':>6}  {'Net':>7}  {'ROI':>7}  {'Best Bet':<14}")
        sep = (f"  {'-'*18}  {'-'*4}  {'-'*14}  {'-'*8}  "
               f"{'-'*6}  {'-'*7}  {'-'*7}  {'-'*14}")

    print(f"{'='*len(hdr.rstrip())}")
    print(f"  LEADERBOARD  {sport.upper()}  {target_date}")
    if any_voids:
        print(f"  NOTE: V = void (postponed game, units returned)")
    print(f"{'='*len(hdr.rstrip())}")
    print()
    print(hdr)
    print(sep)

    for s in ranked:
        net    = s["units_net"]
        roi    = s["roi"]
        ns     = f"+{net:.2f}" if net >= 0 else f"{net:.2f}"
        rs     = f"+{roi*100:.1f}%" if roi >= 0 else f"{roi*100:.1f}%"
        win_p  = f"{s['win_rate']*100:.1f}%" if (s["wins"] + s["losses"]) > 0 else "—"
        bb_rec = fmt_record(s["best_bet_wins"], s["best_bet_losses"])

        if any_voids:
            record = f"{s['wins']}W {s['losses']}L {s['pushes']}P {s.get('voids', 0)}V"
            print(
                f"  {s['model']:<18}  {s['bets']:>4}  {record:<17}  {win_p:>8}  "
                f"{s['units_risked']:>6.1f}  {ns:>7}  {rs:>7}  {bb_rec:<14}"
            )
        else:
            record = fmt_record(s["wins"], s["losses"])
            print(
                f"  {s['model']:<18}  {s['bets']:>4}  {record:<14}  {win_p:>8}  "
                f"{s['units_risked']:>6.1f}  {ns:>7}  {rs:>7}  {bb_rec:<14}"
            )

    print()
    tw  = sum(s["wins"]           for s in ranked)
    tl  = sum(s["losses"]         for s in ranked)
    tv  = sum(s.get("voids", 0)   for s in ranked)
    tr  = sum(s["units_risked"]   for s in ranked)
    tn  = sum(s["units_net"]      for s in ranked)
    ar  = tn / tr if tr > 0 else 0
    ns  = f"+{tn:.2f}" if tn >= 0 else f"{tn:.2f}"
    rs  = f"+{ar*100:.1f}%" if ar >= 0 else f"{ar*100:.1f}%"
    all_wp = f"{tw/(tw+tl)*100:.1f}%" if (tw + tl) > 0 else "—"
    bbw    = sum(s["best_bet_wins"]   for s in ranked)
    bbl    = sum(s["best_bet_losses"] for s in ranked)
    all_bb = fmt_record(bbw, bbl)
    if any_voids:
        all_rec = f"{tw}W {tl}L 0P {tv}V"
        print(
            f"  {'ALL MODELS':<18}  {tw+tl:>4}  {all_rec:<17}  {all_wp:>8}  "
            f"{tr:>6.1f}  {ns:>7}  {rs:>7}  {all_bb:<14}"
        )
    else:
        all_rec = fmt_record(tw, tl)
        print(
            f"  {'ALL MODELS':<18}  {tw+tl:>4}  {all_rec:<14}  {all_wp:>8}  "
            f"{tr:>6.1f}  {ns:>7}  {rs:>7}  {all_bb:<14}"
        )
    print(f"\n{'='*len(hdr.rstrip())}\n")

    # ── Per-model tier table ──────────────────────────────────────────────────
    # Shows each model's record broken down by unit tier and best bet.
    # Only models with at least one graded bet are shown.
    active = [s for s in ranked if s["wins"] + s["losses"] > 0]
    if active:
        print(f"  PER-MODEL TIER BREAKDOWN")
        th = (f"  {'Model':<18}  {'1-unit':^12}  {'3-unit':^12}  {'Best Bet':^12}  {'Overall':^12}")
        print(th)
        print(f"  {'-'*18}  {'-'*12}  {'-'*12}  {'-'*12}  {'-'*12}")
        for s in active:
            def tier_cell(t):
                w = t["wins"]; l = t["losses"]
                if w + l == 0:
                    return "—".center(12)
                rp = t.get("roi_pct")
                roi_s = f"{'+' if rp >= 0 else ''}{rp:.0f}%" if rp is not None else ""
                return f"{w}-{l} {roi_s}".center(12)
            bb_w2 = s["best_bet_wins"]; bb_l2 = s["best_bet_losses"]
            if s.get("best_bet_skip"):
                bb_cell = "SKIP".center(12)
            elif bb_w2 + bb_l2 == 0:
                bb_cell = "—".center(12)
            else:
                bb_roi2 = s.get("best_bet_roi")
                bb_roi_s = f"{'+' if bb_roi2 >= 0 else ''}{bb_roi2*100:.0f}%" if bb_roi2 is not None else ""
                bb_cell = f"{bb_w2}-{bb_l2} {bb_roi_s}".center(12)
            ov_roi = f"{'+' if s['roi'] >= 0 else ''}{s['roi']*100:.0f}%"
            ov_cell = f"{s['wins']}-{s['losses']} {ov_roi}".center(12)
            print(f"  {s['model']:<18}  {tier_cell(s['tiers']['1u'])}  {tier_cell(s['tiers']['3u'])}  {bb_cell}  {ov_cell}")
        print()

    # ── Aggregate tier breakdown table ───────────────────────────────────────
    print(f"  ALL-MODEL TIER SUMMARY  (1 unit = $100 minimum bet)")
    print(f"  {'Tier':<8}  {'Record':<14}  {'Win%':>7}  {'W/L Ratio':>9}  {'Risked':>8}  {'Net $':>8}  {'ROI':>7}")
    print(f"  {'-'*8}  {'-'*14}  {'-'*7}  {'-'*9}  {'-'*8}  {'-'*8}  {'-'*7}")

    def tier_row(label, tier_key):
        # Aggregate tier stats across all models using the nested tiers dict
        tw_ = sum(s["tiers"][tier_key]["wins"]           for s in ranked if tier_key in s.get("tiers", {}))
        tl_ = sum(s["tiers"][tier_key]["losses"]         for s in ranked if tier_key in s.get("tiers", {}))
        tr_ = sum(s["tiers"][tier_key]["units_risked"]   for s in ranked if tier_key in s.get("tiers", {}))
        tu_ = sum(s["tiers"][tier_key]["units_returned"] for s in ranked if tier_key in s.get("tiers", {}))
        tn_ = tu_ - tr_   # net = returned - risked
        total_ = tw_ + tl_
        wp_    = f"{tw_/total_*100:.1f}%" if total_ > 0 else "—"
        wl_r   = f"{tw_/tl_:.2f}" if tl_ > 0 else ("INF" if tw_ > 0 else "—")
        roi_   = f"{'+' if tn_ >= 0 else ''}{tn_/tr_*100:.1f}%" if tr_ > 0 else "—"
        net_d  = f"{'+' if tn_ >= 0 else ''}${tn_*100:.0f}"
        rec_   = fmt_record(tw_, tl_)
        print(f"  {label:<8}  {rec_:<14}  {wp_:>7}  {wl_r:>9}  ${tr_*100:>7.0f}  {net_d:>8}  {roi_:>7}")

    tier_row("1-unit", "1u")
    tier_row("3-unit", "3u")

    # Best bet row
    bb_net  = sum(s["best_bet_units_result"] or 0 for s in ranked)
    bb_risk = sum(s["best_bet_units_wagered"]     for s in ranked)
    bb_wp   = f"{bbw/(bbw+bbl)*100:.1f}%" if (bbw + bbl) > 0 else "—"
    bb_wlr  = f"{bbw/bbl:.2f}" if bbl > 0 else ("INF" if bbw > 0 else "—")
    bb_roi  = f"{'+' if bb_net >= 0 else ''}${bb_net*100:.0f}"
    bb_roip = f"{'+' if bb_net >= 0 else ''}{bb_net/bb_risk*100:.1f}%" if bb_risk > 0 else "—"
    print(f"  {'Best Bet':<8}  {all_bb:<14}  {bb_wp:>7}  {bb_wlr:>9}  ${bb_risk*100:>7.0f}  {bb_roi:>8}  {bb_roip:>7}")

    # Overall row
    all_wp2 = f"{tw/(tw+tl)*100:.1f}%" if (tw + tl) > 0 else "—"
    all_wlr = f"{tw/tl:.2f}" if tl > 0 else ("INF" if tw > 0 else "—")
    all_net_d = f"{'+' if tn >= 0 else ''}${tn*100:.0f}"
    all_roi_p = f"{'+' if tn >= 0 else ''}{tn/tr*100:.1f}%" if tr > 0 else "—"
    print(f"  {'-'*8}  {'-'*14}  {'-'*7}  {'-'*9}  {'-'*8}  {'-'*8}  {'-'*7}")
    print(f"  {'OVERALL':<8}  {fmt_record(tw,tl):<14}  {all_wp2:>7}  {all_wlr:>9}  ${tr*100:>7.0f}  {all_net_d:>8}  {all_roi_p:>7}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Grade model picks against final results and print leaderboard."
    )
    parser.add_argument("--sport", default="mlb")
    parser.add_argument("--date",  default=None)
    args = parser.parse_args()
    grade_picks(sport=args.sport, date=args.date)

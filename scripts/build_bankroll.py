#!/usr/bin/env python
"""
scripts/build_bankroll.py

v3 BANKROLL BUILDER. Downstream aggregator -- NOT a data source.

Reads the already-graded per-model pick files
(picks/{sport}/{date}/{model}.json, which grade_picks.py fills with
result/clv/closing_line) for every slate date >= V3_START_DATE, replays each
model's settled bets in date order, and writes:

  bankroll/{sport}/{model}.json    -- per-model account + full bet history
  bankroll/{sport}/_leaderboard.json -- ranks, balances, gap-to-leader

DESIGN PRINCIPLES (v3):
  - Idempotent. Rebuilds every account from scratch on each run by re-reading
    the graded picks. Re-running never double-counts.
  - Clean baseline. Only dates >= v3_start_date are ingested. v2 slates are
    NEVER counted toward the bankroll (v2 stays archived as the first
    experiment).
  - Settled bets only. A pick affects the balance only when result is one of
    win / loss / push / void. Ungraded picks are skipped and picked up on the
    next run after grading -- the balance only ever reflects settled results.
  - Dollars computed HERE from price + units using the to-win unit convention
    (see _bet_dollars). profit_units from grade_picks is intentionally ignored
    so the balance matches the staking convention exactly.

THE UNIT CONVENTION (1 unit = unit_base_usd, default $100):
  Underdog (+odds): stake = N x base ;          win_profit = N x base x (odds/100)
  Favorite (-odds): stake = N x base x (|odds|/100) ; win_profit = N x base
  WIN  -> balance += win_profit
  LOSS -> balance -= stake
  PUSH / VOID -> balance unchanged

Config (bankroll/{sport}/_config.json): v3_start_date, unit_base_usd, starting_balance.

Usage:
    python scripts/build_bankroll.py --sport mlb
    python scripts/build_bankroll.py            # defaults to mlb
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG + ROSTER
# ─────────────────────────────────────────────────────────────────────────────

def load_config(sport: str) -> dict:
    """Load the per-sport bankroll config (the single source of truth)."""
    cfg_path = PROJECT_ROOT / "bankroll" / sport / "_config.json"
    if not cfg_path.exists():
        print(f"ERROR: missing config {cfg_path}")
        print("       Create it with v3_start_date, unit_base_usd, starting_balance.")
        sys.exit(1)
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    for key in ("v3_start_date", "unit_base_usd", "starting_balance"):
        if key not in cfg:
            print(f"ERROR: config {cfg_path} is missing required key '{key}'")
            sys.exit(1)
    return cfg


def load_roster(sport: str) -> list[str]:
    """
    Read the active model names for a sport from docs/model_roster.md.
    Names live one-per-line under the '## {SPORT}' heading, stopping at the
    next '##' heading. Mirrors how fetch_results.py reads the roster.
    """
    roster_path = PROJECT_ROOT / "docs" / "model_roster.md"
    names: list[str] = []
    in_section = False
    target = f"## {sport.upper()}"
    for line in roster_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = (stripped == target)
            continue
        if in_section and stripped and not stripped.startswith("#"):
            names.append(stripped)
    return names


# ─────────────────────────────────────────────────────────────────────────────
# DOLLAR MATH (to-win unit convention)
# ─────────────────────────────────────────────────────────────────────────────

def _bet_dollars(units: int, price: int, base: float) -> tuple[float, float]:
    """
    Return (stake_usd, to_win_usd) for a bet at N units and American odds.

    Underdog (+odds): stake = N*base ; to_win = N*base*(odds/100)
    Favorite (-odds): stake = N*base*(|odds|/100) ; to_win = N*base
    """
    if price > 0:
        stake = units * base
        to_win = units * base * (price / 100.0)
    else:
        stake = units * base * (abs(price) / 100.0)
        to_win = units * base
    return round(stake, 2), round(to_win, 2)


def _profit_for_result(result: str, stake: float, to_win: float) -> float:
    """Signed dollar profit/loss for a settled bet."""
    if result == "win":
        return round(to_win, 2)
    if result == "loss":
        return round(-stake, 2)
    # push / void -> no money changes hands
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# AGGREGATION
# ─────────────────────────────────────────────────────────────────────────────

SETTLED = ("win", "loss", "push", "void")

# The three overlapping "views" used in the by_type breakdown. Each view's
# buckets are mutually exclusive and independently sum to the total bet count.
def _empty_bucket() -> dict:
    return {"bets": 0, "w": 0, "l": 0, "dollars_net": 0.0}


def _new_by_type() -> dict:
    return {
        "favorite": _empty_bucket(),   # price < 0  (odds-sign split, blunt by design)
        "underdog": _empty_bucket(),   # price > 0
        "1u":       _empty_bucket(),
        "3u":       _empty_bucket(),
        "ml":       _empty_bucket(),
        "rl":       _empty_bucket(),
        "total":    _empty_bucket(),
    }


def _bump(bucket: dict, result: str, profit: float):
    bucket["bets"] += 1
    if result == "win":
        bucket["w"] += 1
    elif result == "loss":
        bucket["l"] += 1
    bucket["dollars_net"] = round(bucket["dollars_net"] + profit, 2)


def build_model_account(model: str, sport: str, cfg: dict) -> dict:
    """
    Replay one model's settled bets (dates >= v3_start_date) into an account
    dict. Returns the full account record ready to write.
    """
    base = float(cfg["unit_base_usd"])
    start = float(cfg["starting_balance"])
    v3_start = cfg["v3_start_date"]

    picks_root = PROJECT_ROOT / "picks" / sport
    # Slate folders are named YYYY-MM-DD; string compare works for ISO dates.
    date_dirs = sorted(
        d for d in picks_root.glob("*")
        if d.is_dir() and d.name >= v3_start
    )

    history: list[dict] = []
    by_type = _new_by_type()
    balance = start

    for ddir in date_dirs:
        pick_file = ddir / f"{model}.json"
        if not pick_file.exists():
            continue
        try:
            doc = json.loads(pick_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        for p in doc.get("picks", []):
            if p.get("action") != "bet":
                continue
            result = p.get("result")
            if result not in SETTLED:
                continue  # exclude ungraded -- picked up next run after grading
            units = int(p.get("units") or 0)
            price = p.get("price")
            if units not in (1, 3) or price is None:
                continue  # malformed -- skip rather than corrupt the balance

            stake, to_win = _bet_dollars(units, int(price), base)
            profit = _profit_for_result(result, stake, to_win)
            balance = round(balance + profit, 2)
            fav_or_dog = "favorite" if int(price) < 0 else "underdog"
            market = p.get("pick_market") or "ml"

            history.append({
                "date":          ddir.name,
                "game_id":       p.get("game_id"),
                "matchup":       p.get("matchup"),
                "market":        market,
                "pick_raw":      p.get("pick_raw"),
                "pick_side":     p.get("pick_side"),
                "fav_or_dog":    fav_or_dog,
                "units":         units,
                "price":         int(price),
                "stake_usd":     stake,
                "to_win_usd":    to_win,
                "result":        result,
                "profit_usd":    profit,
                "balance_after": balance,
                "clv":           p.get("clv"),
                "closing_line":  p.get("closing_line"),
                "edge":          p.get("edge"),
            })

            # by_type: three overlapping views, each sums to total bet count
            _bump(by_type[fav_or_dog], result, profit)
            _bump(by_type["3u" if units == 3 else "1u"], result, profit)
            if market in by_type:
                _bump(by_type[market], result, profit)

    # ── summary ──
    settled = [h for h in history if h["result"] in SETTLED]
    money = [h for h in settled if h["result"] in ("win", "loss")]
    wins = sum(1 for h in settled if h["result"] == "win")
    losses = sum(1 for h in settled if h["result"] == "loss")
    pushes = sum(1 for h in settled if h["result"] == "push")
    voids = sum(1 for h in settled if h["result"] == "void")
    dollars_risked = round(sum(h["stake_usd"] for h in money), 2)
    dollars_net = round(balance - start, 2)
    roi = round(100.0 * dollars_net / dollars_risked, 1) if dollars_risked else None

    clv_vals = [h["clv"] for h in settled if isinstance(h.get("clv"), (int, float))]
    avg_clv = round(sum(clv_vals) / len(clv_vals), 1) if clv_vals else None

    return {
        "model": model,
        "sport": sport,
        "v3_start_date": v3_start,
        "unit_base_usd": cfg["unit_base_usd"],
        "starting_balance": start,
        "current_balance": balance,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "bets": len(money) + pushes + voids,
            "wins": wins, "losses": losses, "pushes": pushes, "voids": voids,
            "dollars_risked": dollars_risked,
            "dollars_net": dollars_net,
            "roi_pct": roi,
            "avg_clv": avg_clv,
            "clv_count": len(clv_vals),
            "by_type": by_type,
        },
        "history": history,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def build_bankroll(sport: str):
    cfg = load_config(sport)
    roster = load_roster(sport)
    if not roster:
        print(f"ERROR: no models found for sport '{sport}' in docs/model_roster.md")
        sys.exit(1)

    out_dir = PROJECT_ROOT / "bankroll" / sport
    out_dir.mkdir(parents=True, exist_ok=True)

    accounts = []
    for model in roster:
        acct = build_model_account(model, sport, cfg)
        (out_dir / f"{model}.json").write_text(
            json.dumps(acct, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        accounts.append(acct)

    # Deprecated models: read their frozen account file (do NOT rewrite it),
    # include in leaderboard so their historical record stays visible and ranked.
    for dep_model in cfg.get("deprecated_models", []):
        dep_path = out_dir / f"{dep_model}.json"
        if dep_path.exists():
            dep_acct = json.loads(dep_path.read_text(encoding="utf-8"))
            dep_acct["deprecated"] = True
            accounts.append(dep_acct)

    # ── leaderboard: rank by current balance, descending ──
    ranked = sorted(accounts, key=lambda a: a["current_balance"], reverse=True)
    leaderboard = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "v3_start_date": cfg["v3_start_date"],
        "ranks": [
            {
                "rank": i + 1,
                "model": a["model"],
                "balance": a["current_balance"],
                "bets": a["summary"]["bets"],
                "deprecated": a.get("deprecated", False),
            }
            for i, a in enumerate(ranked)
        ],
    }
    (out_dir / "_leaderboard.json").write_text(
        json.dumps(leaderboard, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ── console summary (ASCII only -- Windows cp1252 safe) ──
    print(f"v3 bankroll built for {sport} (since {cfg['v3_start_date']})")
    print(f"  unit base ${cfg['unit_base_usd']}  |  start ${cfg['starting_balance']:.0f}")
    print(f"  {'rank':<5}{'model':<12}{'balance':>12}{'bets':>7}")
    for r in leaderboard["ranks"]:
        print(f"  {r['rank']:<5}{r['model']:<12}{r['balance']:>12.2f}{r['bets']:>7}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the v3 per-model bankroll accounts and leaderboard.")
    parser.add_argument("--sport", default="mlb", help="Sport code (default: mlb)")
    args = parser.parse_args()
    build_bankroll(sport=args.sport)

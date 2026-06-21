#!/usr/bin/env python
"""
scripts/watch_set.py

Build the confirm-check watch set for a given date.

Reads:
  picks/{sport}/{date}/{model}.json  -- all model picks
  data/{sport}/{date}/games.json     -- for mlb_game_pk and commence_et

Writes:
  daily/{sport}/{date}/_watch.json   -- wagered game_ids + per-model pick entries

Run immediately after run_daily.py --with-picks completes.

Usage:
  python scripts/watch_set.py
  python scripts/watch_set.py --date 2026-06-20
  python scripts/watch_set.py --sport mlb --date 2026-06-20
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from tz_util import ET


def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def build_watch_set(sport: str, date: str) -> None:
    picks_dir  = PROJECT_ROOT / "picks" / sport / date
    data_dir   = PROJECT_ROOT / "data"  / sport / date
    daily_dir  = PROJECT_ROOT / "daily" / sport / date
    games_path = data_dir / "games.json"
    out_path   = daily_dir / "_watch.json"

    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        sys.exit(1)
    if not picks_dir.exists():
        print(f"ERROR: picks directory not found at {picks_dir}")
        sys.exit(1)

    # Build lookup: game_id -> {mlb_game_pk, commence_et, matchup}
    games = json.loads(games_path.read_text(encoding="utf-8"))
    game_meta: dict = {}
    for g in games:
        gid = g.get("game_id")
        if gid:
            # games.json stores away/home as full team dicts, not strings.
            # Build a short "ABR @ ABR" matchup string from the abbr fields.
            away = g.get("away") or {}
            home = g.get("home") or {}
            away_abbr = (away.get("abbr") or away.get("name", "?")
                         if isinstance(away, dict) else str(away))
            home_abbr = (home.get("abbr") or home.get("name", "?")
                         if isinstance(home, dict) else str(home))
            game_meta[gid] = {
                "mlb_game_pk": g.get("mlb_game_pk"),
                "commence_et": g.get("commence_et"),
                "matchup":     f"{away_abbr} @ {home_abbr}",
            }

    pick_files = sorted(picks_dir.glob("*.json"))
    if not pick_files:
        print(f"WARNING: no model pick files found in {picks_dir}")

    # Build watch_games: one models[] entry per model+market pair (ML and Total
    # on the same game_id each get their own entry)
    watch_games: dict = {}

    for pick_file in pick_files:
        model = pick_file.stem    # "chatgpt", "opus", etc.
        try:
            doc   = json.loads(pick_file.read_text(encoding="utf-8"))
            picks = doc.get("picks", [])
        except Exception as e:
            print(f"  WARNING: could not read {pick_file.name}: {e}")
            continue

        for pick in picks:
            action = (pick.get("action") or "").lower()
            if action not in ("bet", "lean"):
                continue

            gid  = pick.get("game_id")
            if not gid:
                continue
            meta = game_meta.get(gid)
            if not meta:
                print(f"  WARNING: {model} pick game_id {gid!r} not in games.json — skipped")
                continue

            if gid not in watch_games:
                watch_games[gid] = {
                    "game_id":      gid,
                    "mlb_game_pk":  meta["mlb_game_pk"],
                    "matchup":      meta["matchup"],
                    "commence_et":  meta["commence_et"],
                    "confirmed":    False,
                    "confirmed_at": None,
                    "models":       [],
                }

            watch_games[gid]["models"].append({
                "model":       model,
                "action":      action,
                "pick_side":   pick.get("pick_side"),
                "pick_market": pick.get("pick_market"),
                "pick_raw":    pick.get("pick_raw"),    # e.g. "SF ML", "OVER 8.5"
                "units":       pick.get("units"),
                "price":       pick.get("price"),
                "reason":      pick.get("reason", ""),
            })

    n_games   = len(watch_games)
    n_entries = sum(len(e["models"]) for e in watch_games.values())

    doc = {
        "date":     date,
        "sport":    sport,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "games":    watch_games,
    }

    daily_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Written: {out_path.relative_to(PROJECT_ROOT)}")
    print(f"  {n_games} game(s)  |  {n_entries} model-pick pair(s)")
    for entry in sorted(watch_games.values(), key=lambda e: e["commence_et"] or ""):
        tags = [f"{me['model']}({me['pick_market']}:{me['action']})"
                for me in entry["models"]]
        print(f"  {entry['matchup']:<22}  {(entry['commence_et'] or '')[:19]}  {tags}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build confirm-check watch set")
    parser.add_argument("--sport", default="mlb")
    parser.add_argument("--date",  default=None)
    args = parser.parse_args()
    date = args.date or today_et()
    print(f"watch_set.py  sport={args.sport}  date={date}\n")
    build_watch_set(args.sport, date)

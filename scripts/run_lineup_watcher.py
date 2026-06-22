#!/usr/bin/env python
"""
scripts/run_lineup_watcher.py

Continuous loop — polls MLB lineups, fires AI confirm-checks when clusters
of wagered games confirm, and writes auto-HOLDs for any that never do.

Reads:
  daily/{sport}/{date}/_watch.json        (built by watch_set.py)
  daily/{sport}/{date}/_fired.json        (dedup ledger — created here)
  data/{sport}/{date}/games.json          (updated here with confirmed lineups)

Writes:
  daily/{sport}/{date}/_fired.json        (crash-safe, append-on-fire)
  daily/{sport}/{date}/_watch.json        (updated confirmed/confirmed_at fields)
  data/{sport}/{date}/games.json          (context.lineups added on confirmation)
  daily/{sport}/{date}/{model}_confirm.json  (via query_model.py or direct auto-HOLD)

Usage:
  python scripts/run_lineup_watcher.py
  python scripts/run_lineup_watcher.py --date 2026-06-20
  python scripts/run_lineup_watcher.py --sport mlb --date 2026-06-20 --poll 90
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR  = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from tz_util import ET

# Same Windows Python path used by all other orchestrators in this project
PYTHON = r"C:\Users\marko\AppData\Local\Programs\Python\Python312\python.exe"

MLB_API_BASE        = "https://statsapi.mlb.com/api/v1"
POLL_INTERVAL_SECS  = 120   # 2 min between MLB API polls (free; no throttle needed)
CLUSTER_WINDOW_MINS = 40    # games whose first pitch is within 40 min -> same cluster
FIRE_BEFORE_MINS    = 60    # fire each cluster at T-60 of its earliest game


# ── MLB API ───────────────────────────────────────────────────────────────────

def _api_get(url: str, params: dict = None) -> dict | None:
    """HTTP GET via stdlib urllib. Returns parsed JSON or None on error."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  [API] HTTP {e.code}")
        return None
    except urllib.error.URLError as e:
        print(f"  [API] connection error — {e.reason}")
        return None
    except Exception as e:
        print(f"  [API] error — {e}")
        return None


def _fetch_lineups_for_date(date: str) -> dict:
    """
    Poll schedule?hydrate=lineups for the date.
    Returns {gamePk (int): raw_lineups_dict} for every game MLB considers confirmed
    (i.e. awayPlayers or homePlayers lists are non-empty in the response).
    """
    data = _api_get(f"{MLB_API_BASE}/schedule", {
        "sportId": 1,
        "date":    date,
        "hydrate": "lineups",
    })
    if not data:
        return {}
    result: dict = {}
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            pk      = game.get("gamePk")
            lineups = game.get("lineups") or {}
            if pk and (lineups.get("awayPlayers") or lineups.get("homePlayers")):
                result[pk] = lineups
    return result


def _fetch_il_players(team_id: int, season: str) -> list:
    """Fetch IL roster for one team. Mirrors fetch_lineups.py."""
    data = _api_get(f"{MLB_API_BASE}/teams/{team_id}/roster", {
        "rosterType": "40Man",
        "season":     season,
    })
    if not data:
        return []
    il_kw = ("IL", "Injured List")
    out   = []
    for player in data.get("roster", []):
        desc = player.get("status", {}).get("description", "")
        if any(k in desc for k in il_kw):
            out.append({
                "name": player.get("person", {}).get("fullName", "Unknown"),
                "pos":  player.get("position", {}).get("abbreviation", ""),
            })
    return out


def _parse_batting_order(players: list) -> list:
    """Convert awayPlayers/homePlayers list to batting-order dicts. Mirrors fetch_lineups.py."""
    return [
        {
            "name":      p.get("fullName", "Unknown"),
            "pos":       p.get("primaryPosition", {}).get("abbreviation", ""),
            "bat_order": i,
        }
        for i, p in enumerate(players, start=1)
    ]


# ── File I/O (atomic: write to .tmp then rename) ─────────────────────────────

def _save(path: Path, doc) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _load_watch(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: _watch.json not found at {path}")
        print("  Run:  python scripts/watch_set.py --date <date>  first")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def _load_fired(path: Path) -> dict:
    if not path.exists():
        return {"fired": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"fired": {}}


def _load_games(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Fired-set helpers ─────────────────────────────────────────────────────────

def _fkey(model: str, game_id: str) -> str:
    return f"{model}_{game_id}"


def _is_fired(fired_doc: dict, model: str, game_id: str) -> bool:
    return _fkey(model, game_id) in fired_doc.get("fired", {})


def _mark_fired(fired_path: Path, fired_doc: dict,
                model: str, game_id: str, reason: str) -> None:
    """Append to _fired.json and persist immediately — crash-safe dedup."""
    fired_doc.setdefault("fired", {})[_fkey(model, game_id)] = {
        "fired_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reason":   reason,
    }
    _save(fired_path, fired_doc)


# ── Cluster helpers ───────────────────────────────────────────────────────────

def _parse_dt(entry: dict) -> datetime:
    try:
        return datetime.fromisoformat(entry["commence_et"])
    except Exception:
        return datetime.max.replace(tzinfo=timezone.utc)


def _cluster_games(entries: list) -> list:
    """
    Group watch entries into time clusters using greedy left-anchored merge.
    Two games land in the same cluster when the gap from the cluster's
    EARLIEST game to any subsequent game is <= CLUSTER_WINDOW_MINS.
    Returns list of clusters (each a list of game entry dicts).
    """
    if not entries:
        return []
    sorted_entries = sorted(entries, key=_parse_dt)
    clusters: list = []
    cluster:  list = [sorted_entries[0]]
    anchor_t: datetime = _parse_dt(sorted_entries[0])

    for entry in sorted_entries[1:]:
        t = _parse_dt(entry)
        if (t - anchor_t).total_seconds() <= CLUSTER_WINDOW_MINS * 60:
            cluster.append(entry)
        else:
            clusters.append(cluster)
            cluster  = [entry]
            anchor_t = t

    clusters.append(cluster)
    return clusters


def _fire_time(cluster: list) -> datetime:
    """T-FIRE_BEFORE_MINS before the earliest first pitch in this cluster."""
    return min(_parse_dt(e) for e in cluster) - timedelta(minutes=FIRE_BEFORE_MINS)


# ── Auto-HOLD writer ──────────────────────────────────────────────────────────

def _write_auto_hold(
    model:       str,
    sport:       str,
    date:        str,
    model_entry: dict,   # one dict from game_entry["models"] for this model+market
    game_entry:  dict,
) -> None:
    """
    Write one HOLD entry for this model's pick directly to {model}_confirm.json.
    No API call. Merges with any existing entries for other game_ids or markets.
    """
    gid       = game_entry["game_id"]
    market    = model_entry.get("pick_market")
    daily_dir = PROJECT_ROOT / "daily" / sport / date
    out_path  = daily_dir / f"{model}_confirm.json"

    new_entry = {
        "game_id":          gid,
        "matchup":          game_entry.get("matchup"),
        "pick_raw":         model_entry.get("pick_raw"),
        "pick_market":      market,
        "pick_side":        model_entry.get("pick_side"),
        "original_action":  model_entry.get("action"),
        "original_units":   model_entry.get("units"),
        "original_price":   model_entry.get("price"),
        "original_edge":    None,
        "original_reason":  model_entry.get("reason"),
        "cc_outcome":        "HOLD",
        "cc_driver":         "none",
        "cc_cited_fact":     "lineup never confirmed pre-lock",
        "cc_new_units":      model_entry.get("units"),
        "cc_new_units_raw":  None,
        "cc_guard_override": None,
        "cc_parse_warning":  None,
    }

    # Keep existing entries for other game_ids or other markets on same game
    existing: list = []
    if out_path.exists():
        try:
            old      = json.loads(out_path.read_text(encoding="utf-8"))
            existing = [
                e for e in old.get("picks", [])
                if not (e.get("game_id") == gid and e.get("pick_market") == market)
            ]
        except Exception:
            existing = []

    daily_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "model":        model,
        "date":         date,
        "sport":        sport,
        "checked_at":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "picks":        existing + [new_entry],
        "raw_response": None,
    }
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Exit condition ────────────────────────────────────────────────────────────

def _all_resolved(watch_doc: dict, fired_doc: dict) -> bool:
    """True when every model+game_id pair in the watch set has an entry in _fired.json."""
    for entry in watch_doc.get("games", {}).values():
        gid = entry["game_id"]
        for me in entry.get("models", []):
            if not _is_fired(fired_doc, me["model"], gid):
                return False
    return True


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_watcher(sport: str, date: str, poll_secs: int) -> None:
    daily_dir  = PROJECT_ROOT / "daily" / sport / date
    data_dir   = PROJECT_ROOT / "data"  / sport / date
    watch_path = daily_dir / "_watch.json"
    fired_path = daily_dir / "_fired.json"
    games_path = data_dir  / "games.json"
    season     = date[:4]

    print(f"\n{'=' * 55}")
    print(f"  LINEUP WATCHER  {sport.upper()}  {date}")
    print(f"  Poll: {poll_secs}s  |  Cluster window: {CLUSTER_WINDOW_MINS}min  |  Fire: T-{FIRE_BEFORE_MINS}min")
    print(f"{'=' * 55}\n")

    watch_doc = _load_watch(watch_path)
    fired_doc = _load_fired(fired_path)
    n_watch   = len(watch_doc.get("games", {}))

    print(f"Watch set: {n_watch} game(s) with wagered/lean picks\n")
    if n_watch == 0:
        print("Watch set is empty — nothing to do.")
        return

    # ── Startup reconciliation ────────────────────────────────────────────────
    # If games.json already has confirmed lineups for any watch-set game (e.g.
    # from a prior fetch_lineups.py run, or a partial prior watcher run),
    # mark them confirmed now so the first poll tick doesn't re-fetch needlessly.
    if games_path.exists():
        games     = _load_games(games_path)
        ctx_by_pk = {
            g.get("mlb_game_pk"): g.get("context") or {}
            for g in games
            if g.get("mlb_game_pk")
        }
        reconciled = 0
        for entry in watch_doc["games"].values():
            if entry.get("confirmed"):
                continue
            ctx = ctx_by_pk.get(entry.get("mlb_game_pk"), {})
            lu  = ctx.get("lineups") or {}
            if (lu.get("away", {}).get("status") == "confirmed"
                    and lu.get("home", {}).get("status") == "confirmed"):
                entry["confirmed"]    = True
                entry["confirmed_at"] = (
                    lu.get("fetched_at")
                    or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                )
                reconciled += 1
                print(f"  Startup reconcile: already confirmed — {entry['matchup']}")
        if reconciled:
            _save(watch_path, watch_doc)

    if _all_resolved(watch_doc, fired_doc):
        print("\nAll picks already resolved (prior run). Exiting cleanly.")
        return

    calls_fired = 0
    auto_holds  = 0
    tick        = 0

    while True:
        tick   += 1
        now     = datetime.now(timezone.utc)
        now_str = now.strftime("%H:%M:%S UTC")

        # ── Auto-HOLD pass ────────────────────────────────────────────────────
        # Any unconfirmed game whose first pitch has passed -> HOLD all wagering models.
        for entry in watch_doc["games"].values():
            if entry.get("confirmed"):
                continue
            try:
                commence = datetime.fromisoformat(entry["commence_et"])
            except Exception:
                continue
            if now < commence:
                continue

            print(f"[{now_str}] AUTO-HOLD  {entry['matchup']}  (lineup never confirmed pre-lock)")

            # Group by model before marking fired: a model with ML + Total on the
            # same game needs both HOLDs written before the game_id is marked fired.
            models_for_hold: dict = {}   # model -> [model_entry, ...]
            for me in entry.get("models", []):
                model = me["model"]
                if _is_fired(fired_doc, model, entry["game_id"]):
                    continue
                models_for_hold.setdefault(model, []).append(me)

            for model, model_entries in models_for_hold.items():
                for me in model_entries:
                    _write_auto_hold(model, sport, date, me, entry)
                _mark_fired(fired_path, fired_doc, model, entry["game_id"],
                            "auto-hold:never-confirmed")
                auto_holds += len(model_entries)
                picks_str = ", ".join(me.get("pick_raw", "?") for me in model_entries)
                print(f"  -> {model}: HOLD written ({picks_str})")

            # Sentinel so this branch doesn't repeat on the next tick
            entry["confirmed"]    = True
            entry["confirmed_at"] = f"AUTO-HOLD:{now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            _save(watch_path, watch_doc)

        # ── Poll MLB API for unconfirmed games ────────────────────────────────
        unconfirmed = [e for e in watch_doc["games"].values() if not e.get("confirmed")]

        if unconfirmed:
            lineup_by_pk    = _fetch_lineups_for_date(date)
            newly_confirmed = []

            games     = _load_games(games_path) if games_path.exists() else []
            games_map = {g["game_id"]: g for g in games}

            for entry in unconfirmed:
                pk  = entry.get("mlb_game_pk")
                raw = lineup_by_pk.get(pk) if pk else None
                if not raw:
                    continue

                away_players = raw.get("awayPlayers") or []
                home_players = raw.get("homePlayers") or []
                # Require both sides to have batting orders before treating as confirmed
                if not away_players or not home_players:
                    continue

                away_order = _parse_batting_order(away_players)
                home_order = _parse_batting_order(home_players)

                # Fetch IL rosters using team_ids already stored in games.json
                away_il  = []
                home_il  = []
                game_obj = games_map.get(entry["game_id"])
                if game_obj:
                    ctx          = game_obj.get("context") or {}
                    away_team_id = (ctx.get("team_away") or {}).get("team_id")
                    home_team_id = (ctx.get("team_home") or {}).get("team_id")
                    if away_team_id:
                        away_il = _fetch_il_players(int(away_team_id), season)
                    if home_team_id:
                        home_il = _fetch_il_players(int(home_team_id), season)

                    # Write confirmed lineups into games.json context — same shape
                    # that build_confirm_check_prompt reads (away/home -> status/order/il_absences)
                    ctx["lineups"] = {
                        "away":       {"status": "confirmed", "order": away_order,
                                       "il_absences": away_il},
                        "home":       {"status": "confirmed", "order": home_order,
                                       "il_absences": home_il},
                        "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                    game_obj["context"] = ctx

                entry["confirmed"]    = True
                entry["confirmed_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
                newly_confirmed.append(entry)

                il_note = f"  {len(away_il)+len(home_il)} IL" if (away_il or home_il) else ""
                print(f"[{now_str}] CONFIRMED  {entry['matchup']}  "
                      f"({len(away_order)} away / {len(home_order)} home batters{il_note})")

            if newly_confirmed:
                if games_map:
                    _save(games_path, list(games_map.values()))
                _save(watch_path, watch_doc)

        # ── Cluster fire pass ─────────────────────────────────────────────────
        # Only games that are genuinely confirmed (not the AUTO-HOLD sentinel)
        # and still have at least one unfired model pick.
        ready = [
            entry for entry in watch_doc["games"].values()
            if entry.get("confirmed")
            and not (entry.get("confirmed_at") or "").startswith("AUTO-HOLD")
            and any(
                not _is_fired(fired_doc, me["model"], entry["game_id"])
                for me in entry.get("models", [])
            )
        ]

        for cluster in _cluster_games(ready):
            ft = _fire_time(cluster)
            if now < ft:
                continue   # not time yet

            cluster_gids = [e["game_id"] for e in cluster]
            matchup_str  = ", ".join(e["matchup"] for e in cluster)

            # Build per-model list of unfired game_ids in this cluster
            models_in_cluster: dict = {}   # model -> [game_id, ...]
            for entry in cluster:
                gid = entry["game_id"]
                for me in entry.get("models", []):
                    model = me["model"]
                    if _is_fired(fired_doc, model, gid):
                        continue
                    models_in_cluster.setdefault(model, []).append(gid)

            # Dedup: model with ML+total on same game produces gid twice (one entry per pick)
            models_in_cluster = {m: list(dict.fromkeys(gids)) for m, gids in models_in_cluster.items()}

            if not models_in_cluster:
                continue

            ft_str = ft.strftime("%H:%M UTC")
            print(f"\n[{now_str}] CLUSTER FIRE")
            print(f"  Games   : {matchup_str}")
            print(f"  Sched   : {ft_str}  |  Models: {list(models_in_cluster.keys())}")

            for model, model_gids in models_in_cluster.items():

                # Rebuild confirm-check prompt immediately before every cluster fire.
                # build_confirm_check_prompt only includes games confirmed at call time,
                # so an earlier-built prompt would be missing later-cluster games.
                print(f"  [{model}] Building confirm-check prompt...")
                bp = subprocess.run(
                    [PYTHON, str(SCRIPTS_DIR / "build_prompt.py"),
                     "--confirm-check", "--model", model,
                     "--sport", sport, "--date", date],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True, text=True,
                )
                if bp.returncode != 0:
                    print(f"  [{model}] WARNING: build_prompt.py failed "
                          f"(will attempt query with any existing prompt file):")
                    print(f"    {(bp.stderr or '')[-300:]}")
                else:
                    print(f"  [{model}] Prompt built OK")

                # Fire confirm-check API call for this model's cluster games
                gids_str = ",".join(model_gids)
                print(f"  [{model}] Calling --confirm-check  game_ids={model_gids}...")
                qm = subprocess.run(
                    [PYTHON, str(SCRIPTS_DIR / "query_model.py"),
                     "--model", model, "--sport", sport, "--date", date,
                     "--confirm-check", "--game-ids", gids_str],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True, text=True,
                )

                if qm.returncode != 0:
                    print(f"  [{model}] ERROR from query_model.py:")
                    print(f"    {(qm.stderr or '')[-400:]}")
                    # If every game in model_gids is past first pitch, write auto-HOLDs
                    # rather than leaving picks unresolved indefinitely.
                    all_past = all(
                        now >= _parse_dt(next(e for e in cluster if e["game_id"] == gid))
                        for gid in model_gids
                    )
                    if all_past:
                        print(f"  [{model}] All games past first pitch — writing auto-HOLDs")
                        for gid in model_gids:
                            game_entry = watch_doc["games"][gid]
                            for me in game_entry.get("models", []):
                                if me["model"] == model:
                                    _write_auto_hold(model, sport, date, me, game_entry)
                            _mark_fired(fired_path, fired_doc, model, gid, "api-error:auto-hold")
                            auto_holds += 1
                    else:
                        print(f"  [{model}] Will retry on next tick")
                else:
                    for gid in model_gids:
                        _mark_fired(fired_path, fired_doc, model, gid, "confirm-check")
                    calls_fired += 1
                    print(f"  [{model}] Done -> {model}_confirm.json")
                    # Echo decision-table lines from the subprocess stdout
                    for line in (qm.stdout or "").splitlines():
                        if any(tok in line for tok in
                               ("→", "HOLD", "CANCEL", "UPGRADE", "DOWNGRADE", "GUARD")):
                            print(f"    {line.strip()}")

        # ── Exit check ────────────────────────────────────────────────────────
        if _all_resolved(watch_doc, fired_doc):
            print(f"\n{'=' * 55}")
            print(f"  SLATE WATCHER COMPLETE  {sport.upper()}  {date}")
            print(f"  Games watched   : {n_watch}")
            print(f"  API calls fired : {calls_fired}")
            print(f"  Auto-HOLDs      : {auto_holds}")
            print(f"{'=' * 55}\n")
            return

        n_pending = sum(
            1
            for e in watch_doc["games"].values()
            for me in e.get("models", [])
            if not _is_fired(fired_doc, me["model"], e["game_id"])
        )
        print(f"[{now_str}] tick={tick}  pending={n_pending} pair(s)  "
              f"sleeping {poll_secs}s...", end="\r", flush=True)
        time.sleep(poll_secs)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Watch for confirmed MLB lineups and fire confirm-check calls"
    )
    parser.add_argument("--sport", default="mlb")
    parser.add_argument("--date",  default=None,
                        help="Date YYYY-MM-DD (default: today in US Eastern Time)")
    parser.add_argument("--poll",  default=POLL_INTERVAL_SECS, type=int,
                        help=f"Poll interval seconds (default: {POLL_INTERVAL_SECS})")
    args = parser.parse_args()
    date = args.date or datetime.now(ET).strftime("%Y-%m-%d")

    try:
        run_watcher(sport=args.sport, date=date, poll_secs=args.poll)
    except KeyboardInterrupt:
        print("\n\nInterrupted. _fired.json is up to date — safe to restart.")
        sys.exit(0)

#!/usr/bin/env python
"""
scripts/fetch_results.py

Fetch final scores for a completed slate from the MLB Stats API.

One API call fetches all game results for the date. Scores are matched back
to games.json by mlb_game_pk (already stored there by fetch_pitchers.py).

Usage:
    python scripts/fetch_results.py --date 2026-06-02
    python scripts/fetch_results.py --sport mlb --date 2026-06-02

Writes:
    results/{sport}/{date}/results.json  -- canonical scores file
    data/{sport}/{date}/games.json       -- updates result block per game

Run this the morning after a slate completes.
"""

import argparse
import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tz_util import ET


MLB_API_BASE = "https://statsapi.mlb.com/api/v1"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(url: str, params: dict = None) -> dict | None:
    """HTTP GET with stdlib urllib. No API key required for MLB Stats API."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  ERROR: HTTP {e.code} -- {url}")
        return None
    except urllib.error.URLError as e:
        print(f"  ERROR: Connection failed -- {e.reason}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MLB STATS API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_schedule_results(date: str) -> list[dict]:
    """
    Fetch all games for a date with their final scores.

    Uses the schedule endpoint which returns status + scores in one call.
    No per-game looping needed — one request covers the whole slate.

    Returns a list of dicts, each containing:
      gamePk, away_name, home_name, away_score, home_score, status, is_winner_away
    """
    data = api_get(f"{MLB_API_BASE}/schedule", {
        "sportId": 1,
        "date":    date,
    })

    if not data or not data.get("dates"):
        return []

    results = []
    for date_block in data["dates"]:
        for g in date_block.get("games", []):
            away = g["teams"]["away"]
            home = g["teams"]["home"]

            # Scores are present on the game object for completed games
            away_score = away.get("score")  # None if game not yet started/postponed
            home_score = home.get("score")

            # detailedState tells us: "Final", "In Progress", "Postponed", etc.
            status_raw = g["status"]["detailedState"]

            # Normalise to a simple status string for our schema
            # "Game Over" = completed but not yet officially logged as "Final" — treat as final
            if status_raw in ("Final", "Game Over", "Completed Early"):
                status = "final"
            elif "Progress" in status_raw:
                status = "in_progress"
            elif "Postponed" in status_raw:
                status = "postponed"
            elif "Cancelled" in status_raw or "Canceled" in status_raw:
                status = "cancelled"
            elif "Suspended" in status_raw:
                status = "suspended"
            else:
                status = status_raw.lower().replace(" ", "_")

            # Determine winner from isWinner flag
            if status == "final" and away_score is not None and home_score is not None:
                if away.get("isWinner"):
                    winner = "away"
                elif home.get("isWinner"):
                    winner = "home"
                elif away_score == home_score:
                    winner = "tie"  # extremely rare in MLB
                else:
                    winner = None
            else:
                winner = None

            results.append({
                "mlb_game_pk":  g["gamePk"],
                "away_name":    away["team"]["name"],
                "home_name":    home["team"]["name"],
                "away_score":   away_score,
                "home_score":   home_score,
                "winner":       winner,
                "status":       status,
                "status_raw":   status_raw,
            })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def fetch_results(sport: str = "mlb", date: str = None):
    """
    Fetch final scores for all games on the slate and write them to disk.

    Flow:
      1. Load games.json to get the list of games + their mlb_game_pks
      2. Fetch the MLB schedule for the date (one call, all scores)
      3. Match schedule results back to games.json by mlb_game_pk
      4. Write results/{sport}/{date}/results.json
      5. Update the result block in each game in games.json
      6. Print summary table
    """
    target_date = date or today_et()

    print(f"\n{'='*55}")
    print(f"  FETCH RESULTS  {sport.upper()}")
    print(f"  Slate date (US ET): {target_date}")
    print(f"{'='*55}\n")

    project_root = Path(__file__).parent.parent

    # ── Load games.json ───────────────────────────────────────────────────────
    games_path = project_root / "data" / sport / target_date / "games.json"
    if not games_path.exists():
        print(f"ERROR: games.json not found at {games_path}")
        print("  Run fetch_odds.py first.")
        sys.exit(1)

    with open(games_path, encoding="utf-8") as f:
        games = json.load(f)

    print(f"Loaded {len(games)} games from games.json")

    # Build lookup: mlb_game_pk -> game object (for fast matching)
    # mlb_game_pk is stored by fetch_pitchers.py as an integer
    pk_to_game = {}
    missing_pk = []
    for g in games:
        pk = g.get("mlb_game_pk")
        if pk:
            pk_to_game[int(pk)] = g
        else:
            missing_pk.append(f"{g['away']['abbr']} @ {g['home']['abbr']}")

    if missing_pk:
        print(f"  WARNING: {len(missing_pk)} game(s) have no mlb_game_pk — run fetch_pitchers.py first")
        for m in missing_pk:
            print(f"    {m}")

    # ── Fetch scores ──────────────────────────────────────────────────────────
    print(f"\nStep 1: Fetching MLB schedule scores for {target_date}...")
    fetched_at = now_utc()
    mlb_results = fetch_schedule_results(target_date)

    if not mlb_results:
        print("ERROR: No results returned from MLB Stats API. Check date and connection.")
        sys.exit(1)

    print(f"  API returned {len(mlb_results)} game(s)\n")

    # ── Match and update games.json ───────────────────────────────────────────
    print("Step 2: Matching results to games and updating games.json...")

    matched   = 0
    unmatched = []
    results_list = []  # for results.json

    for mlb_r in mlb_results:
        pk   = mlb_r["mlb_game_pk"]
        game = pk_to_game.get(pk)

        if not game:
            # gamePk not found — log it but don't stop
            print(f"  WARNING: gamePk {pk} ({mlb_r['away_name']} @ {mlb_r['home_name']}) not in games.json")
            unmatched.append(pk)
            continue

        # Write result block into games.json game object
        game["result"] = {
            "away_score":      mlb_r["away_score"],
            "home_score":      mlb_r["home_score"],
            "winner":          mlb_r["winner"],
            "status":          mlb_r["status"],
            "fetched_at":      fetched_at,
            "source":          "mlb_official",
            "source_priority": 1,
            "verified":        False,  # set True after manual confirmation
        }

        # Build entry for results.json (includes game_id for joining to picks)
        results_list.append({
            "game_id":      game["game_id"],        # TheOddsAPI join key
            "mlb_game_pk":  pk,
            "matchup":      f"{game['away']['abbr']} @ {game['home']['abbr']}",
            "away_abbr":    game["away"]["abbr"],
            "home_abbr":    game["home"]["abbr"],
            "away_score":   mlb_r["away_score"],
            "home_score":   mlb_r["home_score"],
            "winner":       mlb_r["winner"],
            "status":       mlb_r["status"],
        })

        matched += 1

    # ── Save games.json ───────────────────────────────────────────────────────
    with open(games_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)

    # ── Write results.json ────────────────────────────────────────────────────
    results_dir  = project_root / "results" / sport / target_date
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / "results.json"

    results_doc = {
        "date":       target_date,
        "sport":      sport,
        "fetched_at": fetched_at,
        "games":      results_list,
        "summary": {
            "final":       sum(1 for r in results_list if r["status"] == "final"),
            "in_progress": sum(1 for r in results_list if r["status"] == "in_progress"),
            "postponed":   sum(1 for r in results_list if r["status"] == "postponed"),
            "unmatched":   len(unmatched),
        },
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results_doc, f, indent=2)

    print(f"Step 3: Saved -> {results_path.relative_to(project_root)}\n")

    # ── Summary table ─────────────────────────────────────────────────────────
    # Build the summary as a string first so it can be pasted into the post mortem
    summary_lines = []
    summary_lines.append(f"{'='*66}")
    summary_lines.append(f"  RESULTS SUMMARY  MLB  {target_date}")
    summary_lines.append(f"{'='*55}")
    summary_lines.append("")

    for r in results_list:
        away = r["away_abbr"]
        home = r["home_abbr"]
        a_s  = r["away_score"] if r["away_score"] is not None else "?"
        h_s  = r["home_score"] if r["home_score"] is not None else "?"
        won   = " <--" if r["winner"] == "away" else ""
        won_h = " <--" if r["winner"] == "home" else ""
        status_tag = "" if r["status"] == "final" else f"  [{r['status']}]"
        summary_lines.append(f"  {away:4} {a_s:>3}{won}  @  {home:4} {h_s:>3}{won_h}{status_tag}")

    summary_lines.append("")
    final_count = results_doc["summary"]["final"]
    summary_lines.append(f"  Final:    {final_count}/{matched} games")
    if results_doc["summary"]["postponed"]:
        summary_lines.append(f"  Postponed: {results_doc['summary']['postponed']}")
    if results_doc["summary"]["in_progress"]:
        summary_lines.append(f"  In progress: {results_doc['summary']['in_progress']}")
    if unmatched:
        summary_lines.append(f"  Unmatched: {len(unmatched)} gamePk(s) not in games.json")
    summary_lines.append(f"{'='*66}")

    summary_text = "\n".join(summary_lines)

    # Print to terminal
    print(summary_text)
    print()

    return summary_text


# ─────────────────────────────────────────────────────────────────────────────
# POST-MORTEM FILE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def load_model_roster(project_root: Path, sport: str) -> list[str]:
    """
    Read docs/model_roster.md and return the list of model names for the given sport.

    Looks for a line like "## MLB" then collects non-empty, non-heading lines
    until the next heading or end of file. Returns an empty list if the sport
    section is not found or has no entries.
    """
    roster_path = project_root / "docs" / "model_roster.md"
    if not roster_path.exists():
        print(f"  WARNING: docs/model_roster.md not found — no raw.txt files will be created")
        return []

    lines       = roster_path.read_text(encoding="utf-8").splitlines()
    target      = f"## {sport.upper()}"
    in_section  = False
    models      = []

    for line in lines:
        if line.strip() == target:
            in_section = True
            continue
        if in_section:
            if line.startswith("##"):  # next section — stop
                break
            name = line.strip()
            if name:
                models.append(name)

    return models


def create_post_mortem_files(sport: str, results_date: str, results_summary_text: str):
    """
    Four things happen after results are fetched:

    3a — Paste the results summary into today's post_mortem file.
         Today's post_mortem was created yesterday when the previous
         date's fetch_results.py ran. We find the FINAL RESULTS
         placeholder block and replace it with the real scores.

    3b — Create tomorrow's picks folder.

    3c — Copy the blank template into tomorrow's folder as
         post_mortem_{tomorrow}.txt with the date filled in.

    3d — Create empty {model}_raw.txt files in tomorrow's folder,
         one per model listed under the sport in docs/model_roster.md.
    """
    project_root  = Path(__file__).parent.parent
    template_path = project_root / "docs" / "post_mortem_template.txt"

    # Compute tomorrow's date from the results date
    results_dt    = datetime.strptime(results_date, "%Y-%m-%d")
    tomorrow_dt   = results_dt + timedelta(days=1)
    tomorrow_date = tomorrow_dt.strftime("%Y-%m-%d")

    print(f"\n{'-'*55}")
    print(f"  POST-MORTEM FILE MANAGEMENT")
    print(f"{'-'*55}")

    # ── 3a: Paste results into today's post mortem ────────────────────────────
    today_pm_path = project_root / "picks" / sport / results_date / f"post_mortem_{results_date}.txt"

    if not today_pm_path.exists():
        print(f"  WARNING: {today_pm_path.relative_to(project_root)} not found — skipping results paste")
        print(f"  (Create it manually from docs/post_mortem_template.txt first)")
    else:
        content = today_pm_path.read_text(encoding="utf-8")

        # Replace the FINAL RESULTS placeholder block with actual results.
        # The placeholder sits between two ══════ dividers.
        # We match the exact text that appears in the template.
        placeholder = "FINAL RESULTS\n[OPERATOR WILL PASTE RESULTS HERE]"
        if placeholder in content:
            content = content.replace(placeholder, results_summary_text.strip())
            # Also fill in the date in the SLATE header
            content = content.replace(
                "SLATE: MLB — [date will be filled by operator]",
                f"SLATE: MLB — {results_date}",
                1  # only replace first occurrence (the header line)
            )
            today_pm_path.write_text(content, encoding="utf-8")
            print(f"  Results pasted into post_mortem_{results_date}.txt")
        else:
            print(f"  WARNING: Placeholder not found in {today_pm_path.name} — already filled in? Skipping.")

    # ── 3b: Create tomorrow's picks folder ────────────────────────────────────
    tomorrow_dir = project_root / "picks" / sport / tomorrow_date
    tomorrow_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Tomorrow's folder ready: picks/{sport}/{tomorrow_date}/")

    # ── 3c: Create tomorrow's blank post mortem from template ─────────────────
    tomorrow_pm_path = tomorrow_dir / f"post_mortem_{tomorrow_date}.txt"

    if tomorrow_pm_path.exists():
        print(f"  post_mortem_{tomorrow_date}.txt already exists — skipping")
    else:
        if not template_path.exists():
            print(f"  WARNING: Template not found at {template_path} — cannot create tomorrow's post mortem")
        else:
            template = template_path.read_text(encoding="utf-8")
            # Fill in tomorrow's date in the SLATE header
            filled = template.replace(
                "SLATE: MLB — [date will be filled by operator]",
                f"SLATE: MLB — {tomorrow_date}",
                1
            )
            tomorrow_pm_path.write_text(filled, encoding="utf-8")
            print(f"  Blank post mortem created: picks/{sport}/{tomorrow_date}/post_mortem_{tomorrow_date}.txt")

    # ── 3d: Create empty raw.txt files for each model in the roster ───────────
    models = load_model_roster(project_root, sport)
    if models:
        created  = []
        skipped  = []
        for model in models:
            raw_path = tomorrow_dir / f"{model}_raw.txt"
            if raw_path.exists():
                skipped.append(model)
            else:
                raw_path.touch()   # zero-byte file
                created.append(model)
        if created:
            print(f"  Created empty raw.txt files: {', '.join(created)}")
        if skipped:
            print(f"  raw.txt already existed (skipped): {', '.join(skipped)}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch final MLB game scores and write into results.json and games.json."
    )
    parser.add_argument(
        "--sport", default="mlb",
        help="Sport code (default: mlb). NBA/NHL to be added when those seasons start."
    )
    parser.add_argument(
        "--date", default=None,
        help="Slate date (YYYY-MM-DD). Default: today in US Eastern Time."
    )
    parser.add_argument(
        "--no-grade", action="store_true",
        help="Skip auto-running grade_picks.py after fetching results."
    )
    args = parser.parse_args()
    summary_text = fetch_results(sport=args.sport, date=args.date)
    create_post_mortem_files(
        sport=args.sport,
        results_date=args.date or today_et(),
        results_summary_text=summary_text,
    )

    # Auto-chain into grade_picks unless suppressed with --no-grade
    if not args.no_grade:
        import importlib.util
        grade_path = Path(__file__).parent / "grade_picks.py"
        spec = importlib.util.spec_from_file_location("grade_picks", grade_path)
        gm   = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gm)
        gm.grade_picks(sport=args.sport, date=args.date or today_et())

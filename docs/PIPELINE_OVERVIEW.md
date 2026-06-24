# PIPELINE OVERVIEW — AI CAPPER

End-to-end workflow from data fetch to graded results.
Updated: 2026-06-21

---

## PHASE 1 — DATA FETCH & PROMPT BUILD (automated via run_daily.py)

Run once each morning during the golden window (Australian evening = US 4–9 AM ET).
Run again ~2 hours before first pitch to capture umpires, lineups, and line movement.

```
python scripts/run_daily.py mlb
python scripts/run_daily.py mlb --date 2026-06-03   # override date
```

| Step | Script | Required? | Output | Notes |
|------|--------|-----------|--------|-------|
| 1 | `fetch_odds.py` | **Required** | `data/mlb/{date}/games.json` created | Morning run locks opening_snapshot. Afternoon run captures line movement. |
| 2 | `fetch_pitchers.py` | **Required** | `games.json` → pitcher_away/home + gamePk | Adds ERA, WHIP, W-L, IP, hand, FIP components. |
| 3 | `fetch_pitcher_advanced.py` | Optional | `games.json` → xERA, FIP, HH%, Brl%, K/9, last-3-starts | pybaseball + MLB Stats API game log. Skip if pybaseball unavailable. |
| 4 | `fetch_weather.py` | **Required** | `games.json` → weather per stadium | Open-Meteo. Dome stadiums get a one-line note. |
| 5 | `fetch_teamstats.py` | **Required** | `games.json` → team form, record, RS/G, RA/G | MLB Stats API standings. |
| 6 | `fetch_bullpen.py` | Optional | `games.json` → bullpen ERA, closer, taxed relievers | Boxscores last 3 days. |
| 7 | `fetch_lineups.py` | Optional | `games.json` → confirmed batting order + IL absences | Only confirmed ~2-3h before first pitch. Morning run shows "not yet confirmed". |
| 8 | `fetch_umpires.py` | Optional | `games.json` → plate umpire name | MLB posts ~1-2h before first pitch. |
| 9 | `build_prompt.py` | **Required** | `daily/mlb/{date}/prompt.md` | Base prompt for any model. |
| 9b | *(auto)* | — | `daily/mlb/{date}/prompt_{model}.md` × 8 | Per-model prompts with model-specific instruction appended. run_daily.py triggers these automatically after step 9. |

---

## PHASE 2 — MODEL PICKS (automated for 6 models)

Phase 2 is fully automated via query_model.py for all 8 models.

AUTOMATED MODELS (all API connected):
  chatgpt   gpt-5.4           web search OFF  medium reasoning
  grok      grok-4.3          web search OFF  medium reasoning
  deepseek  deepseek-v4-pro   web search OFF  thinking enabled
  kimi      kimi-k2.6         web search OFF  thinking enabled
  qwen      qwen3.7-max       web search OFF  thinking enabled
  gemini    gemini-3.5-flash  web search OFF  medium thinking_level
  opus      claude-opus-4-8   web search OFF  medium reasoning
  sonnet    claude-sonnet-4-6 web search OFF  medium reasoning

PICKS QUERY COMMAND (run once per model per slate):
  python scripts/query_model.py --model grok --date 2026-06-10
  python scripts/query_model.py --model chatgpt --date 2026-06-10
  python scripts/query_model.py --model deepseek --date 2026-06-10
  python scripts/query_model.py --model kimi --date 2026-06-10
  python scripts/query_model.py --model qwen --date 2026-06-10
  python scripts/query_model.py --model gemini --date 2026-06-10

OR run all 8 at once:
  python scripts/run_picks_all.py --date 2026-06-10
  python scripts/run_picks_all.py   # uses today's date automatically

OR use the integrated pre-game orchestrator (recommended):
  python scripts/run_daily.py mlb --with-picks
  python scripts/run_daily.py mlb --date 2026-06-10 --with-picks

  This chains: fetch pipeline → build prompts → run_picks_all → log_all_picks →
  watch_set → run_lineup_watcher (auto-spawned in a new detached console window).
  The watcher is launched automatically with no prompt and no countdown.
  It runs in its own window and survives the parent terminal closing.
  To launch it manually instead: python scripts/run_lineup_watcher.py --date {date}
  Without --with-picks: stops after prompts (preserves the pre-send prompt-review checkpoint).

FLAGS:
  --reasoning low/medium/high   override default reasoning effort
  --dry-run                     reads files, prints what would be sent, no API call
  --postmortem                  send post-mortem instead of picks query

Output saved to: picks/mlb/{date}/{model}_raw.txt

All 7 active models run via API (run_picks_all.py). No manual paste required.

After all raw.txt files are saved, parse into structured JSON:

```
python scripts/log_all_picks.py mlb --date 2026-06-04
```

Output: `picks/mlb/{date}/{model}.json` -- structured record with one entry per game:
`game_id, pick, price, units, edge (numeric pts gap e.g. "6.2 pts"), reason, looked_up, best_bet, best_bet_skip (true if no 3-unit play)`

Best bet skip: if no model identified a 3-unit play on a given day, the SLATE SUMMARY will contain "NO BEST BET -- no 3-unit play identified today". log_picks.py captures this as `best_bet_skip: true` in the model's JSON. grade_picks.py counts these as `best_bet_skips` in grades.json. Skip days are a valid and expected outcome -- do not treat them as parse errors.

Repeat for all 7 active models. Or use `log_all_picks.py` to batch-process all raw.txt files in a date folder.

---

## PHASE 2b — CONFIRM-CHECK WATCHER (run after log_all_picks.py, before results)

The confirm-check layer re-evaluates every wagered pick once the official batting lineup is confirmed. Each model gets a chance to HOLD, CANCEL, DOWNGRADE, or UPGRADE its pick based on the confirmed order vs the projected order used at pick time.

**Step 1 — Build the watch set** (run once, immediately after log_all_picks.py):
```
python scripts/watch_set.py --date 2026-06-10
```
Output: `daily/mlb/{date}/_watch.json` — one entry per model+market pair on every bet or lean pick.

**Step 2 — Lineup watcher** (auto-spawned by --with-picks; or launch manually):
```
python scripts/run_lineup_watcher.py --date 2026-06-10
```
When launched via `--with-picks`, this opens in a **new detached console window** and
runs independently — it is not a child of run_daily.py and survives the parent terminal
closing. A heartbeat file is written every poll tick:
  `daily/mlb/{date}/_watcher_heartbeat.json`  — contains PID, last_tick (ISO UTC), date

What it does:
- Polls the MLB Stats API (`/api/v1/schedule?hydrate=lineups`) every 2 minutes
- Groups games into 40-minute time clusters; fires the confirm-check round at T-60 of the earliest game in each cluster
- For each cluster: calls `build_prompt.py --confirm-check` (assembles before/after wRC+ prompt), then `query_model.py --confirm-check --game-ids <ids>` for each model with picks on that cluster
- Each model's response (HOLD / CANCEL / DOWNGRADE / UPGRADE) is written to `daily/{sport}/{date}/{model}_confirm.json`
- Games still unconfirmed at first pitch receive an automatic HOLD (no API call fired)
- Dedup via `_fired.json` — crash-safe; safe to restart mid-day
- Exits when all model+game_id pairs are resolved

**Output files:**
```
daily/mlb/{date}/_watch.json                 watch set (built by watch_set.py)
daily/mlb/{date}/_fired.json                 dedup log (written by run_lineup_watcher.py)
daily/mlb/{date}/_watcher_heartbeat.json     liveness file (PID + last_tick timestamp)
daily/mlb/{date}/{model}_confirm.json        confirm-check results per model
daily/mlb/{date}/confirm_system_{model}.md   system prompt used for confirm-check call
daily/mlb/{date}/confirm_prompt_{model}.md   user prompt used for confirm-check call
```

**Confirm-check outcomes:**
| Outcome | Effect |
|---------|--------|
| HOLD | Proceed at original stake |
| CANCEL | Pick voided — zero profit/loss, logged as cancelled (not a loss) |
| DOWNGRADE | Stake reduced to cc_new_units |
| UPGRADE | Stake increased to cc_new_units (subject to slate ceiling + 3u cap guards) |

**If you don't run the watcher:** Grade as normal — `grade_picks.py` checks for `{model}_confirm.json` and skips cc logic if absent. No confirm-check on a given date means all picks are graded at original stake.

---

## PHASE 3 — RESULTS & GRADING (semi-automated, Phase 3 in roadmap)

After games finish (usually next morning AEST):

| Step | Script | Status | Output |
|------|--------|--------|--------|
| 1 | `fetch_results.py` | *Built* | `results/mlb/{date}/results.json` — final scores from MLB Stats API |
| 2 | `grade_picks.py` | *Built* | `results/mlb/{date}/grades.json` — W/L per pick, units won/lost |
| 3 | Stats engine | *Not yet built (Phase 4)* | Per-model ROI, calibration, leaderboard |

```
python scripts/fetch_results.py --date 2026-06-06
python scripts/grade_picks.py --date 2026-06-06
```

`grade_picks.py` automatically reads `daily/{sport}/{date}/{model}_confirm.json` if it exists and
applies confirm-check adjustments before grading: CANCEL voids the pick (no stats contribution),
DOWNGRADE/UPGRADE changes the effective stake. If no confirm JSON exists, picks grade at original stake.

`grades.json` links back to `picks/{model}.json` via `game_id`. Each pick gets:
`result: WIN | LOSS | PUSH | VOID | cancelled`, `units_result: +2.73 | -1.0`, `closing_line` (for CLV, when added).
cc_* fields (cc_outcome, cc_driver, cc_new_units, cc_guard_override) are written onto every pick with a confirm-check entry.
Per-model tier breakdown: `1u/3u/best bet/overall` (5u tier removed as of v3.1).
Leaderboard one-liner shows a C column (e.g. `1C`) when any picks were cancelled on that date.

### fetch_results.py also manages post-mortem files automatically

When `fetch_results.py --date 2026-06-06` runs it does three additional things after saving scores:

1. **Pastes results into today's post mortem** — finds `picks/mlb/2026-06-06/post_mortem_2026-06-06.txt` (created the previous day) and replaces the `[OPERATOR WILL PASTE RESULTS HERE]` placeholder with the actual game scores. Also fills in the date in the SLATE header.
2. **Creates tomorrow's picks folder** — `picks/mlb/2026-06-07/` ready for the next slate.
3. **Creates tomorrow's blank post mortem** — copies `docs/post_mortem_template.txt` into `picks/mlb/2026-06-07/post_mortem_2026-06-07.txt` with the date pre-filled.
4. **Creates empty raw.txt stubs for each model** — touches `{model}_raw.txt` for every model in `docs/model_roster.md` in tomorrow's picks folder. These stubs are what `run_postmortem_all.py`'s 0-byte guard checks to confirm the pipeline ran for that date.

> **Date logic:** given `--date 2026-06-06`, today's post mortem = `picks/mlb/2026-06-06/`, tomorrow's folder = `picks/mlb/2026-06-07/`. The tomorrow folder was created by *yesterday's* run of this script.

---

## PHASE 4 — POST-MORTEM (semi-automated, after grading)

Each model gets the graded results pasted into its post-mortem file (now done automatically by `fetch_results.py` -- see above). The model then reviews its picks against the results.

Post-mortem queries are automated for all 8 models (grok, chatgpt, deepseek, kimi, qwen, gemini, opus, sonnet):
  python scripts/query_model.py --model grok --date 2026-06-10 --postmortem
  (repeat for each model)

OR use the integrated post-game orchestrator (recommended):
  python scripts/run_daily_2.py mlb
  python scripts/run_daily_2.py mlb --date 2026-06-10

  This chains: fetch_results → fetch_confirmed_data → run_postmortem_all.
  (grade_picks.py is run separately — see below — because it must consume {model}_confirm.json
  from the confirm-check watcher, which runs between pick logging and grading.)
  Guards:
    - Requires logged {model}.json pick files for the date.
    - fetch_results.py aborts if any game is still in progress or not yet started
      (safeguard added 2026-06-18). Wait until all games complete, then re-run.
      Bypass with: python scripts/fetch_results.py --force-results (use sparingly).
    - Halts if confirmed data is incomplete (boxscores not posted yet);
      use --skip-confirmed to override and proceed without it.
  Halt-then-rerun is safe: all steps are idempotent on re-run.

OR run post-mortems alone:
  python scripts/run_postmortem_all.py --date 2026-06-10
  python scripts/run_postmortem_all.py   # uses today's date automatically

All models use full context (original picks included in the post-mortem call).

Each model's response is written to TWO destinations:
  1. Per-model file (primary):  picks/{sport}/{date}/{model}_postmortem.txt
  2. Shared aggregate (review): picks/{sport}/{date}/post_mortem_{date}.txt

The "already done" guard checks for the per-model file's existence -- re-running
run_postmortem_all.py after a partial failure is safe.

Post-mortem output is NOT auto-injected into method docs, MODEL_INSTRUCTIONS.md, or
any prompt file. Routing responses into method updates or calibration changes is a
separate, manually-gated step (operator reviews, decides whether to promote). The
injection of calibration stats into future prompts is Phase 5b — not yet built.

Template: `docs/post_mortem_template.txt`
Saved to: `picks/mlb/{date}/post_mortem_{date}.txt` (auto-created by previous day's `fetch_results.py` run)

---

## STANDALONE OPERATOR-RUN SCRIPTS (not part of run_daily.py)

These are run manually, on your own schedule:

| Script | When to run | Output |
|--------|------------|--------|
| `fetch_wind_edge.py` | After crookedfence.org updates (~10 AM ET, unpredictable) | `data/mlb/crookedfence_archive/YYYY-MM-DD_{predictions,results}.json` + refreshes dataset |
| `compile_crookedfence_dataset.py` | Run automatically by fetch_wind_edge.py; or run standalone | `data/mlb/crookedfence_dataset.{csv,jsonl}` — growing reverse-engineering dataset |

```
python scripts/fetch_wind_edge.py            # fetch + archive + compile in one command
python scripts/compile_crookedfence_dataset.py  # recompile dataset only
```

The daily prompt does NOT depend on CrookedFence output. Stadium dimensions come from a static `STADIUM_DIMENSIONS` table in `build_prompt.py` (all 30 MLB parks). Wind comes from Open-Meteo via `fetch_weather.py`.

---

## DAILY TIMING GUIDE

| AEST | ET | Action |
|------|----|--------|
| 6–9 PM | 4–7 AM | Run `run_daily.py` — locks opening snapshot, builds morning prompt |
| 9 PM–midnight | 7–10 AM | Paste into models, save raw responses, run `log_picks.py` |
| ~2h before first pitch | varies | Re-run `fetch_lineups.py`, `fetch_umpires.py`, `build_prompt.py` for updated prompt |
| After log_all_picks.py | same day | Run `watch_set.py --date` then `run_lineup_watcher.py --date` (leave running — exits when all games resolve) |
| During game day | auto | `run_lineup_watcher.py` fires confirm-checks per cluster as lineups confirm; writes `{model}_confirm.json` |
| After watcher exits | same day | Run `grade_picks.py --date` (reads confirm JSON automatically) |
| Morning after games | varies | Run `run_daily_2.py mlb` — chains results → confirmed data → post-mortems |
| Morning after games | varies | If too early for boxscores: wait, then re-run same command (`--skip-confirmed` to override) |

---

## STATIC REFERENCE FILES (manual refresh — see update schedule)

Stored in `data/mlb/` — not date-partitioned, shared across all dates.
`build_prompt.py` reads these directly at prompt-build time via `scripts/load_static_data.py`.
`run_daily.py` checks all files are present and warns if any are older than 7 days.

| File | Contents | Update frequency |
|------|----------|-----------------|
| `splits_vs_LHP.txt` | Batter wRC+/wOBA/OPS vs LHP | Weekly |
| `splits_vs_RHP.txt` | Batter wRC+/wOBA/OPS vs RHP | Weekly |
| `splits_home.txt` | Batter stats in home games | Weekly |
| `splits_away.txt` | Batter stats in away games | Weekly |
| `pitchers_xfip_siera.txt` | Starter xFIP/SIERA/K-BB% (2025-26 blended) | Weekly |
| `pitchers_last14.txt` | Starter stats last 14 days | Every 2-3 days |
| `Bullpen.txt` | All relievers: role, last 6 days usage, ERA, K% | Daily |
| `park_factors_all.txt` | Park factors all conditions (3yr rolling) | Once per season |
| `park_factors_roof_closed.txt` | Park factors roof-closed only | Once per season |

**To refresh:** download the new file from FanGraphs, replace the file in `data/mlb/`,
then re-run `build_prompt.py`. No other pipeline step is needed — the new data is picked
up automatically on the next prompt build.

**FanGraphs download paths:**
- Batter splits: Splits Leaderboard → select stat type → export
- Pitcher stats: Pitching Leaderboard → xFIP/SIERA columns → export
- Bullpen: Bullpen Usage page → export (or copy-paste)
- Park factors: Park Factors page → export

---

## FILE MAP

```
data/mlb/{date}/games.json                  raw data (odds + all context; context.lineups updated by watcher)
daily/mlb/{date}/prompt.md                  base prompt (all models)
daily/mlb/{date}/prompt_{model}.md          per-model prompt (8 files, includes ML + totals methods)
daily/mlb/{date}/_watch.json                confirm-check watch set (built by watch_set.py)
daily/mlb/{date}/_fired.json                dedup log of fired confirm-checks (written by run_lineup_watcher.py)
daily/mlb/{date}/{model}_confirm.json       confirm-check results per model (HOLD/CANCEL/DOWNGRADE/UPGRADE per pick)
daily/mlb/{date}/confirm_system_{model}.md  system prompt used for the confirm-check API call
daily/mlb/{date}/confirm_prompt_{model}.md  user prompt used for the confirm-check API call
picks/mlb/{date}/{model}_raw.txt            raw model response (backup)
picks/mlb/{date}/{model}.json               parsed picks (structured; includes total_pick with _is_total:True)
picks/mlb/{date}/post_mortem_{date}.txt     post-mortem notes
results/mlb/{date}/results.json             final game scores
results/mlb/{date}/grades.json              W/L + units per pick; cc_* fields if confirm-check ran
results/mlb/{date}/best_bets.json           per-model best bet results; cancels field if any CANCELs
data/mlb/{date}/confirmed_data.json         confirmed lineups + HP umpire (post-game)
picks/mlb/{date}/{model}_postmortem.txt     individual post-mortem per model (x8)

data/mlb/crookedfence_archive/YYYY-MM-DD_predictions.json  CF today predictions (operator-fetched)
data/mlb/crookedfence_archive/YYYY-MM-DD_results.json      CF yesterday results (operator-fetched)
data/mlb/crookedfence_dataset.{csv,jsonl}                   reverse-engineering master dataset
```

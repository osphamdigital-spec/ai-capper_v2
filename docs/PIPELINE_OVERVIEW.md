# PIPELINE OVERVIEW — AI CAPPER

End-to-end workflow from data fetch to graded results.
Updated: 2026-06-10

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

Phase 2 is now automated via query_model.py for 6 of 8 models.

AUTOMATED MODELS (API connected):
  chatgpt   gpt-5.4          web search OFF  medium reasoning
  grok      grok-4.3         web search OFF  medium reasoning
  deepseek  deepseek-v4-pro  web search OFF  thinking enabled
  kimi      kimi-k2.6        web search OFF  thinking enabled
  qwen      qwen3.7-max      web search OFF  thinking enabled
  gemini    gemini-3.5-flash web search OFF  medium thinking_level

MANUAL MODELS (API not yet connected):
  opus      Claude Opus      paste into claude.ai manually
  sonnet    Claude Sonnet    paste into claude.ai manually

PICKS QUERY COMMAND (run once per model per slate):
  python scripts/query_model.py --model grok --date 2026-06-10
  python scripts/query_model.py --model chatgpt --date 2026-06-10
  python scripts/query_model.py --model deepseek --date 2026-06-10
  python scripts/query_model.py --model kimi --date 2026-06-10
  python scripts/query_model.py --model qwen --date 2026-06-10
  python scripts/query_model.py --model gemini --date 2026-06-10

OR run all 6 at once:
  python scripts/run_picks_all.py --date 2026-06-10
  python scripts/run_picks_all.py   # uses today's date automatically

FLAGS:
  --reasoning low/medium/high   override default reasoning effort
  --dry-run                     reads files, prints what would be sent, no API call
  --postmortem                  send post-mortem instead of picks query

Output saved to: picks/mlb/{date}/{model}_raw.txt

For manual models (opus, sonnet): open the matching prompt_{model}.md,
paste into claude.ai, copy the full response, and save it manually to
picks/mlb/{date}/{model}_raw.txt.

After all raw.txt files are saved, parse into structured JSON:

```
python scripts/log_picks.py --model sonnet --date 2026-06-04 --input picks/mlb/2026-06-04/sonnet_raw.txt
python scripts/log_all_picks.py
```

Output: `picks/mlb/{date}/{model}.json` -- structured record with one entry per game:
`game_id, pick, price, units, edge (numeric pts gap e.g. "6.2 pts"), reason, looked_up, best_bet, best_bet_skip (true if no 3-unit play)`

Best bet skip: if no model identified a 3-unit play on a given day, the SLATE SUMMARY will contain "NO BEST BET -- no 3-unit play identified today". log_picks.py captures this as `best_bet_skip: true` in the model's JSON. grade_picks.py counts these as `best_bet_skips` in grades.json. Skip days are a valid and expected outcome -- do not treat them as parse errors.

Repeat for all 8 models. Or use `log_all_picks.py` to batch-process all raw.txt files in a date folder.

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

`grades.json` links back to `picks/{model}.json` via `game_id`. Each pick gets:
`result: WIN | LOSS | PUSH | VOID`, `units_result: +2.73 | -1.0`, `closing_line` (for CLV, when added).
Per-model tier breakdown: `1u/3u/best bet/overall` (5u tier removed as of v3.1).

### fetch_results.py also manages post-mortem files automatically

When `fetch_results.py --date 2026-06-06` runs it does three additional things after saving scores:

1. **Pastes results into today's post mortem** — finds `picks/mlb/2026-06-06/post_mortem_2026-06-06.txt` (created the previous day) and replaces the `[OPERATOR WILL PASTE RESULTS HERE]` placeholder with the actual game scores. Also fills in the date in the SLATE header.
2. **Creates tomorrow's picks folder** — `picks/mlb/2026-06-07/` ready for the next slate.
3. **Creates tomorrow's blank post mortem** — copies `docs/post_mortem_template.txt` into `picks/mlb/2026-06-07/post_mortem_2026-06-07.txt` with the date pre-filled.

> **Date logic:** given `--date 2026-06-06`, today's post mortem = `picks/mlb/2026-06-06/`, tomorrow's folder = `picks/mlb/2026-06-07/`. The tomorrow folder was created by *yesterday's* run of this script.

---

## PHASE 4 — POST-MORTEM (semi-automated, after grading)

Each model gets the graded results pasted into its post-mortem file (now done automatically by `fetch_results.py` -- see above). The model then reviews its picks against the results.

Post-mortem queries are automated for all 9 models (grok, chatgpt, deepseek, kimi, qwen, gemini, opus, sonnet, fable):
  python scripts/query_model.py --model grok --date 2026-06-10 --postmortem
  (repeat for each model)

OR run all 9 at once:
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
separate, manually-gated step that has not yet been built (v2 Phase 5).

Template: `docs/post_mortem_template.txt`
Saved to: `picks/mlb/{date}/post_mortem_{date}.txt` (auto-created by previous day's `fetch_results.py` run)

---

## DAILY TIMING GUIDE

| AEST | ET | Action |
|------|----|--------|
| 6–9 PM | 4–7 AM | Run `run_daily.py` — locks opening snapshot, builds morning prompt |
| 9 PM–midnight | 7–10 AM | Paste into models, save raw responses, run `log_picks.py` |
| ~2h before first pitch | varies | Re-run `fetch_lineups.py`, `fetch_umpires.py`, `build_prompt.py` for updated prompt |
| Morning after games | varies | Run `fetch_results.py` then `grade_picks.py` |

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
data/mlb/{date}/games.json          raw data (odds + all context)
daily/mlb/{date}/prompt.md          base prompt (all models)
daily/mlb/{date}/prompt_{model}.md  per-model prompt (8 files)
picks/mlb/{date}/{model}_raw.txt    raw model response (backup)
picks/mlb/{date}/{model}.json       parsed picks (structured)
picks/mlb/{date}/post_mortem_{date}.txt  post-mortem notes
results/mlb/{date}/results.json     final game scores
results/mlb/{date}/grades.json      W/L + units per pick
```

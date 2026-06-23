# CLAUDE.md — AI CAPPER V2 PROJECT CONTEXT

**Read this file at the start of every session.**

---

## WHAT THIS PROJECT IS

AI Capper v2 is an independent-handicapper experiment. Eight frontier AI models
(kimi, chatgpt, opus, gemini, deepseek, qwen, sonnet, grok) each build and apply
their OWN handicapping method. There is no house methodology. The pipeline delivers
DATA + COMPETITION CONSTRAINTS to each model — how to interpret that data is each
model's own business.

The canonical model list is always docs/model_roster.md.

Each model's method lives in docs/methods/method_{model}_v1.md — self-authored,
versioned, never overwritten. These are the model's persistent external memory
between stateless API calls. Each model also has a separate totals method in
docs/methods/method_{model}_totals_v1.md (all 8 authored 2026-06-19).

The shared prompt (Layer B) carries only: the edge gate, unit map, and
data-integrity rules. No analysis sequences, no bullpen formulas, no run
estimation recipes. Those were Layer C — removed in v2. (The house slate
ceiling was removed in v3 — bets per slate is now each model's own rule.)

**Current phase:** v2 operational — data pipeline, picks, grading, post-mortem loop, and
calibration stats are all running daily. Totals (Over/Under) betting added 2026-06-19:
all 8 models have self-authored totals methods and the output format now includes full
TOTAL/TOTAL PRICE/TOTAL UNITS/TOTAL EDGE slots. Remaining work: calibration injection
into prompts (Phase 5b), promotion engine (Phase 6), multi-sport (Phase 7).

**Owner:** Mark. New to Claude Code — explain commands clearly, show what you're about to do
before doing it, and never assume prior terminal knowledge.

---

## SPORTS COVERED

| Sport | Bet types | Season months |
|---|---|---|
| MLB | ML, run line, totals | Mar–Oct |
| NBA | spread, ML, totals | Oct–Jun |
| NHL | ML, puck line, totals | Oct–Jun |
| NFL | spread, ML, totals | Sep–Feb |
| NCAA FB | spread, ML, totals | Aug–Jan |
| NCAA BB | spread, ML, totals | Nov–Apr |

Build everything sport-agnostic. Sport is a parameter, never hardcoded.

---

## THE GOLDEN RULE — TIMEZONE

Owner is in Australia (AEST). **The canonical slate date is always the date shown
on the US sports site (MLB.com etc), never the local Australian date.** Every script
must work in US Eastern Time for slate dates. See docs/TIMEZONE_STANDARD.md.

---

## FOLDER STRUCTURE

```
ai-capper_v2/
  CLAUDE.md
  docs/                         (shared, sport-agnostic project docs)
    methods/                    (per-model self-authored method docs)
      method_{model}_v1.md      (ML/RL method — never overwritten, new revision = new version)
      method_{model}_totals_v1.md  (O/U method — same versioning rules)
  scripts/                      (all scripts — sport is a parameter, not a folder)
  data/mlb/YYYY-MM-DD/          (raw games.json per sport per date)
  data/mlb/crookedfence_archive/ (archived CF predictions + results JSON, for reverse-engineering)
  daily/mlb/YYYY-MM-DD/         (generated prompt.md per sport per date)
  picks/mlb/YYYY-MM-DD/         (model picks + post-mortems per sport per date)
  results/mlb/YYYY-MM-DD/       (final scores per sport per date)
```

---

## WHAT LAYER B CONTAINS (the shared system prompt)

- Identity: independent professional bettor, no house method
- Edge gate: 4 pp minimum gap to bet (sides); 0.5–1.5 run gap for totals
- Unit map: gap 4–7 → 1u, gap 7+ → 3u, gap <4 → LEAN/PASS
- Totals gate: <0.5 runs → No bet; 0.5–0.9 → LEAN; 1.0–1.4 → 1u; 1.5+ → 3u
- Data integrity: TBD starter = PASS, stale price = absent, postponed = PASS
- Output format (machine-parsed) — includes TOTAL / TOTAL PRICE / TOTAL UNITS / TOTAL EDGE slots
- Model-specific ML/RL method from docs/methods/method_{model}_v{N}.md
- Model-specific totals method from docs/methods/method_{model}_totals_v{N}.md

## WHAT LAYER B DOES NOT CONTAIN (removed from v2)

The following OLD Layer C blocks were removed from build_system_prompt() in v2:
- BULLPEN FATIGUE RULE (quantified formula)
- ODDS APPROACH (moneyline evaluation sequence)
- TOTALS APPROACH (run estimation formula)
- TEAM QUALITY CHECK (run differential downgrade rule)
- OPENER/BULK FLAG
- ESTIMATED DATA RULE
- PROFESSIONAL STANDARD (pass rate targets)
- STAKING DISCIPLINE (explicit gap-calculation sequence)

Each model now decides its own analysis approach via its method doc.

---

## THE STAKING COMPETITION RULES (fixed for all models)

**Sides (ML / Run Line):**
- Gap under 4 pts → LEAN or PASS, never a bet
- Gap 4–7 pts → 1 unit maximum
- Gap 7+ pts, clean data → 3 units (the ceiling; nothing rates higher)

**Totals (Over/Under):**
- Gap under 0.5 runs → No bet
- Gap 0.5–0.9 runs → LEAN (no stake)
- Gap 1.0–1.4 runs → 1 unit
- Gap 1.5+ runs, clean data → 3 units (the ceiling)

**General:**
- Best bet is the highest-conviction 3-unit play if one exists; if none, log
  as a skip on best bet (not a failure).
- EDGE field is numeric ("6.2 pts" for sides, "1.4 runs" for totals)
- Bets per slate: NO house ceiling (removed in v3) — each model sets its own max bets per slate in its method document
- TBD starter: mandatory PASS (both sides and totals)

---

## HOW TO WORK ON THIS PROJECT

1. **Show before you run.** Before running any script or command, explain what it does
   and show the code. Wait for confirmation.
2. **One step at a time.** Build one thing, test it, confirm it works, then move on.
3. **Comment the code heavily.** Owner reads it to learn.
4. **Never hardcode the sport or date.** Always parameters.
5. **Log learnings.** When something breaks and gets fixed, note it in docs/LEARNINGS.md.

---

## BUILD ROADMAP

- [x] Phase 1: MLB data pipeline (fetch_odds, fetch_pitchers, fetch_weather, etc.)
- [x] Phase 2: Pick logger (log_picks.py / log_all_picks.py)
- [x] Phase 3: Auto-grader (fetch_results.py + grade_picks.py)
- [x] v2 Step 1: System prompt converted to Layer B (no house methodology)
- [x] v2 Step 2: Method authoring — all 8 models have self-authored method docs in docs/methods/
- [x] Phase 4: Stats engine (unit-weighted ROI, calibration, leaderboard) — calc_calibration.py
- [x] Phase 5a: Post-mortem loop — run_postmortem_all.py + confirmed-data injection live daily
- [x] Totals expansion — all 8 models authored O/U methods; TOTAL/TOTAL PRICE/TOTAL UNITS/TOTAL EDGE in output; log_picks.py + grade_picks.py already support totals
- [x] CrookedFence integration — standalone operator-run fetch_wind_edge.py + reverse-engineering dataset (compile_crookedfence_dataset.py); NOT part of daily pipeline
- [x] Stadium dimensions — static STADIUM_DIMENSIONS table (all 30 MLB parks) in build_prompt.py; no external dependency
- [x] Confirm-check watcher — 5-script layer that re-checks wagered games once lineups officially confirm:
      watch_set.py                         builds daily/{sport}/{date}/_watch.json from Run-1 picks (run after log_all_picks.py)
      build_prompt.py --confirm-check      assembles before/after wRC+ data prompt per model (rebuilt before every cluster fire)
      query_model.py --confirm-check       fires one AI call per model per cluster; parses HOLD/CANCEL/DOWNGRADE/UPGRADE; writes {model}_confirm.json
      run_lineup_watcher.py                continuous MLB API polling loop; 40-min cluster batching; T-60 fire; _fired.json dedup; auto-HOLD at first pitch
      grade_picks.py (extended)            consumes {model}_confirm.json — CANCEL voids pick from record, DOWNGRADE/UPGRADE adjusts stake; cc_* fields on every pick
      Key output fields: C column in leaderboard one-liner; cancels/best_bet_cancel in grades.json; cc_outcome/cc_driver/cc_new_units/cc_guard_override on graded picks
- [ ] Phase 5b: Calibration injection into prompts (pull per-model stats into next-slate prompt)
- [ ] Phase 6: Promotion engine (future)
- [ ] Phase 7: Extend to NBA/NHL
- [ ] Phase 8: Website (only after 30-day validation)

---

## AUTOMATED PIPELINE SCRIPTS

run_daily.py          -- PRE-GAME orchestrator: fetch pipeline → build prompts → [--with-picks: run_picks_all → log_all_picks → watch_set → (20s-timeout prompt, default YES) run_lineup_watcher]
run_daily_2.py        -- POST-GAME orchestrator: fetch results → confirmed data → post-mortems
query_model.py        -- sends picks, post-mortem, or confirm-check query to a single model API
run_picks_all.py      -- runs picks queries for all 8 connected models (called by run_daily.py --with-picks)
run_postmortem_all.py -- runs post-mortem queries for all 8 connected models (called by run_daily_2.py)

CONFIRM-CHECK LAYER (run between log_all_picks.py and grade_picks.py):
watch_set.py             -- builds _watch.json from Run-1 picks; run once after log_all_picks.py completes
run_lineup_watcher.py    -- continuous loop: polls MLB API, fires confirm-checks when clusters confirm, auto-HOLDs at first pitch
  Usage: python scripts/watch_set.py --date YYYY-MM-DD
         python scripts/run_lineup_watcher.py --date YYYY-MM-DD   (runs until all games resolved)

STANDALONE OPERATOR-RUN (NOT part of run_daily.py):
fetch_wind_edge.py           -- fetches CrookedFence data.json + results.json, archives both, refreshes dataset
compile_crookedfence_dataset.py -- flattens all archived CF results into crookedfence_dataset.{csv,jsonl}
  Usage: python scripts/fetch_wind_edge.py   (run manually when crookedfence.org has updated)

Connected models (API): chatgpt, grok, deepseek, kimi, qwen, gemini, opus, sonnet

---

## CONSTRAINTS

- SQLite MCP fails on both machines — use JSON files or plain Python sqlite3 library.
- Laptop is Windows 11 native, no WSL — scripts must run on native Windows.
- AI models being tested mostly cannot browse — WE pre-load all data into the prompt.
- FanGraphs data is STATIC FILES ONLY — manually downloaded by operator, loaded via load_static_data.py. FanGraphs blocks all automated access (Cloudflare Turnstile). Never add live FanGraphs fetch calls to any script.

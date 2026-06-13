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
between stateless API calls.

The shared prompt (Layer B) carries only: the edge gate, unit map, slate ceilings,
and data-integrity rules. No analysis sequences, no bullpen formulas, no run
estimation recipes. Those were Layer C — removed in v2.

**Current phase:** Step 1 — system prompt and CLAUDE.md converted to v2 architecture.
Post-mortem loop, calibration injection, and promotion engine are FUTURE work, not yet built.

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
      method_{model}_v1.md      (never overwritten — new revision = new version)
  scripts/                      (all scripts — sport is a parameter, not a folder)
  data/mlb/YYYY-MM-DD/          (raw games.json per sport per date)
  daily/mlb/YYYY-MM-DD/         (generated prompt.md per sport per date)
  picks/mlb/YYYY-MM-DD/         (model picks + post-mortems per sport per date)
  results/mlb/YYYY-MM-DD/       (final scores per sport per date)
```

---

## WHAT LAYER B CONTAINS (the shared system prompt)

- Identity: independent professional bettor, no house method
- Edge gate: 4 pp minimum gap to bet
- Unit map: gap 4–7 → 1u, gap 7+ → 3u, gap <4 → LEAN/PASS
- Slate ceilings: 1 bet max (1-7 games), 2 (8-14), 3 (15+)
- Data integrity: TBD starter = PASS, stale price = absent, postponed = PASS
- Output format (machine-parsed)
- Model-specific method appended from docs/methods/method_{model}_v1.md

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

- Gap under 4 pts → LEAN or PASS, never a bet
- Gap 4–7 pts → 1 unit maximum
- Gap 7+ pts, clean data → 3 units (the ceiling; nothing rates higher)
- Best bet is the highest-conviction 3-unit play if one exists; if none, log
  as a skip on best bet (not a failure).
- EDGE field is numeric ("6.2 pts") — log_picks.py accepts any string value
- Slate ceilings: 1 bet max (1-7 games), 2 bets max (8-14), 3 bets max (15+)
- TBD starter: mandatory PASS

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
- [ ] v2 Step 2: Method authoring — run authoring query per model, save method docs
- [ ] Phase 4: Stats engine (unit-weighted ROI, calibration, leaderboard)
- [ ] Phase 5: Post-mortem loop + calibration injection (future)
- [ ] Phase 6: Promotion engine (future)
- [ ] Phase 7: Extend to NBA/NHL
- [ ] Phase 8: Website (only after 30-day validation)

---

## AUTOMATED PIPELINE SCRIPTS

query_model.py        -- sends picks or post-mortem query to a single model API
run_picks_all.py      -- runs picks queries for all 8 connected models
run_postmortem_all.py -- runs post-mortem queries for all 8 connected models

Connected models (API): chatgpt, grok, deepseek, kimi, qwen, gemini, opus, sonnet

---

## CONSTRAINTS

- SQLite MCP fails on both machines — use JSON files or plain Python sqlite3 library.
- Laptop is Windows 11 native, no WSL — scripts must run on native Windows.
- AI models being tested mostly cannot browse — WE pre-load all data into the prompt.

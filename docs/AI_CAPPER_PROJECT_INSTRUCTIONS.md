AI CAPPER — PROJECT DESCRIPTION & INSTRUCTIONS
Version: 3.2
Last Updated: June 12, 2026
Owner: Mark
Status: Research & Validation Phase
Change from v1.1: Replaced 1–9 confidence scale with 1/3 unit staking system. Units now map directly to stake size and unit-weighted ROI. Skip logic flows naturally from 0-unit / Pass ratings.
Change from v3.0: Staking system simplified (5-unit tier removed, 3 units is new ceiling); professional bettor identity framing added to all model prompts; best bet rule tightened (must be 3-unit play; no best bet published if none qualify); minimum edge gate (4-point gap floor) and slate discipline ceilings added.
Change from v3.1: Model table updated (Manus removed, Qwen added, Claude split into Opus/Sonnet); status section updated to reflect automated pipeline running daily (Phases 1–3 complete); files table updated to reflect current script and doc structure.

WHAT WE ARE BUILDING
A sports betting analysis website that pits multiple AI models against each other in a transparent, publicly tracked competition to find the best bet across major US sports leagues.
Each AI model operates as an independent analyst with its own pick, its own reasoning, and its own live track record. Users can follow whichever model they trust, follow the day’s strongest play across all models, or follow a consensus view — all based on verified performance data, not marketing claims.
The product is built on one principle that most tipster and capper sites ignore: honest, auditable records published in real time, with nothing hidden.

THE CORE CONCEPT
The AI Model Stable
Several frontier AI models — including ChatGPT, Claude (Opus and Sonnet), Gemini, Grok, DeepSeek, Kimi, Qwen, and others — each receive the same standardised prompt for every slate of games. Each model produces one best bet per slate. Each pick is logged with:

The exact game
The exact line available at pick time
The model’s estimated probability and edge
The model’s unit rating (how much it would actually bet — see staking system below)
The model’s reasoning
The result after the game finishes

No picks are edited. No bad runs are hidden. No models are quietly dropped without public explanation.
The Leaderboard
The homepage is a live leaderboard showing every model’s running performance across:

Win rate against the spread / moneyline / total
Unit-weighted ROI — the core profitability metric (see below)
Closing Line Value (CLV) — did the pick beat the closing line?
Calibration — do 3-unit plays win more often than 1-unit plays?
Performance broken down by sport and bet type

Users see not just who is winning but whether the wins are meaningful — a model on a hot streak with poor CLV is different from a model with consistent line value, and a model that bets big on the right games is different from one that bets big indiscriminately.
The Three Ways to Follow
1. Follow a specific model
Users pick one AI model and follow only its picks, including its unit ratings for stake sizing. Full individual track record, unit-weighted ROI, and CLV data per model.
2. Follow the strongest play of the day
Each day, the site surfaces the model's best bet -- but only if that model has a 3-unit play. If no model reaches 3 units on a given day, no best bet is published. This is logged publicly as a skip on best bet. A skip is not a failure -- it means no game cleared the professional threshold that day, and that discipline is exactly what makes the published best bets worth following.
3. Follow the consensus
Where 3 or more models independently land on the same side of the same game, a consensus pick is flagged with a combined unit rating. Consensus means genuine independent agreement, not averaging a single model’s output.
Skip Days
Not every slate produces a bet worth publishing. Skip days flow naturally from the unit system:

If every model rates its best pick 0 units or Pass, no picks are published
If fewer than two games have clean confirmed data, the day is skipped
Skip days are logged and displayed publicly with a stated reason
This is a feature. Selective betting beats forced action, and publishing the skip record builds credibility.


THE UNIT STAKING SYSTEM
All models use the same staking scale. The number is not an abstract confidence score — it is literally how many units the model would bet. This ties every rating directly to money, which is the only thing that ultimately matters, and it makes the rating measurable: over a season, higher-unit plays should win more often and return more than lower-unit plays. If they don’t, the model can’t tell its good picks from its average ones, and the site says so with data.
The Scale
|Units  |Label        |Meaning                                                        |Expected frequency                                      |
|-------|-------------|---------------------------------------------------------------|--------------------------------------------------------|
|3 units|STRONG PLAY  |Clear edge. 7+ point probability gap. Confirmed clean data.    |Rare -- a few times per week across all models combined |
|1 unit |STANDARD PLAY|Real but ordinary edge. 4-7 point gap. The default bet rating.|The most common published rating                        |
|LEAN   |NO STAKE     |Slight lean, gap under 4 points. Noted, not published as a bet.|Common -- triggers skip assessment if all models lean   |
|Pass   |NO PLAY      |No edge found on this slate.                                   |Correct answer on most games                            |
### Gap-to-units mapping

| Gap | Maximum stake |
|---|---|
| Under 4 points | LEAN or PASS -- never a bet |
| 4-7 points | 1 unit maximum |
| 7+ points with confirmed clean data | 3 units maximum |

3 units is the ceiling. There is no higher rating.

What a unit is
A unit is a fixed percentage of a bettor’s bankroll, chosen by the bettor — commonly 1% of bankroll. The site does not tell users their unit size; it tells them how many units a model would risk. A user with a $1,000 bankroll using 1% units bets $10 per unit, so a 3-unit play is $30. The site publishes unit counts; the user controls the dollar value.
Key rules for the unit system

**3-unit plays are rare by design.** A model that calls everything a 3-unit play will be exposed immediately by unit-weighted ROI the moment those plays underperform. The scale punishes inflation automatically.
Units must be consistent with the claimed edge. A model claiming a 2% edge but staking 3 units is miscalibrated and will be flagged. A model claiming a 5% edge but staking 1 unit is being appropriately cautious about its inputs — that gap is itself a useful signal.
The unit rating reflects the bet, not the team. A model that puts 3 units on every game involving a strong team is rating team quality, not line value. Units are about edge against the price.
0 units is a real, valid output. A model is encouraged to return 0 units or Pass when it finds nothing. This is not a failure — it is the discipline that makes the published picks worth following.

Consensus Unit Rating
When 3 or more models pick the same side of the same game:

Sum is not used — instead, average the unit ratings of the agreeing models
Display as: Consensus: [avg] units — [N] models agree
Example: Claude 3u + Gemini 1u + Grok 3u on Astros ML → Consensus: 2.3 units — 3 models agree
A consensus pick requires at least 3 active models on the same side. Two models agreeing is noted but not surfaced as formal consensus.

Why units, not a 1–10 confidence number
A confidence number (“8 out of 10”) tells a user nothing actionable — it doesn’t say how much to bet, and its middle tiers carry no measurable signal at realistic sample sizes. Units fix both problems: they map directly to stake, they collapse to a small number of genuinely distinct tiers (1 / 3), and they enable unit-weighted ROI — the metric that proves whether a model’s rating system actually works.

KEY METRICS — HOW WE KNOW IF IT WORKS
MetricWhat it measuresTargetWin RateBasic accuracy against the lineAbove 52.4% at -110 to be profitable on flat stakesUnit-weighted ROIReturn per unit risked — the core profitability numberPositive over 200+ unit-risked sampleCLVDid the pick beat the closing line?Positive CLV is the leading indicator of real edgeRating calibrationDo 3-unit plays outperform 1-unit plays?Yes — otherwise the rating is decorativeEdge vs units consistencyDoes stake size match claimed edge?Should correlate — flag mismatchesConsensus performanceDo consensus picks beat individual picks?Test over 50+ consensus picks3-unit play performanceDo 3-unit plays clearly outperform 1-unit plays?Yes — otherwise the rating calibration is brokenSkip day retrospectiveOn skip days, would the best available pick have lost?Validates skip discipline
The honest expectation: Most models will hover near 50% on raw win rate. The product value is in three things: transparency, skip discipline, and whether any model shows positive unit-weighted ROI and proper rating calibration over a meaningful sample. A model that goes 50% raw but wins on its 3-unit plays and loses on its 1-unit plays has genuine rating skill — and the unit system is what lets you prove it.

WHAT THIS IS NOT

Not a tipping service that guarantees winners. No pick is guaranteed. No profit claims.
Not a black box consensus system. Every model is visible, independent, accountable. Consensus is derived transparently.
Not a “best AI” contest. The goal is which analytical approach produces betting value, not which AI is smartest.
Not a replacement for a bettor’s judgment. Analysis and research tool only. Users decide their own wagers and their own unit size.
Not a forced-action service. Skip days are published. No obligation to bet every day.


SPORTS COVERED
LeagueBet TypesSeasonNFLSpread, Moneyline, TotalsSep — FebNCAA FootballSpread, Moneyline, TotalsAug — JanNBASpread, Moneyline, TotalsOct — JunNCAA BasketballSpread, Moneyline, TotalsNov — AprMLBMoneyline, Run Line, TotalsMar — OctNHLMoneyline, Puck Line, TotalsOct — Jun
NFL and NBA are primary. MLB and NHL secondary. NCAA variants included but treated with more caution given game volume and softer public data.

THE MODELS
Named by actual product name. No invented personas.
| Model | Provider | Entry mode | Version |
|---|---|---|---|
| ChatGPT | OpenAI | API | gpt-5.4 |
| Claude Opus | Anthropic | Manual (claude.ai) | latest |
| Claude Sonnet | Anthropic | Manual (claude.ai) | latest |
| Gemini | Google | API | gemini-3.5-flash |
| Grok | xAI | API | grok-4.3 |
| DeepSeek | DeepSeek | API (thinking ON) | deepseek-v4-pro |
| Kimi | Moonshot AI | API (thinking ON) | kimi-k2.6 |
| Qwen | Alibaba | API (thinking ON) | qwen3.7-max |

8 models tracked. Claude counts as two separate leaderboard entries (Opus and Sonnet).
The canonical model list is always docs/model_roster.md — update there first.
Models added or removed only with public announcement and explanation. Discontinued models keep their historical record visible permanently.
Model naming note: Use of model names is nominative — reporting what each produced, not claiming endorsement or partnership. Legal/TOS review required before commercial launch, specifically OpenAI, Anthropic, Google, and xAI usage policies on gambling-adjacent applications.

HOW THE PICKS ARE GENERATED
Step 1 — Pre-game data verification. Confirm games not started, starting pitchers/goalies/QBs confirmed, current lines pulled from a live book, injuries from official reports, weather for outdoor games.
Step 2 — The base prompt. Confirmed data inserted into the standard template generated by build_prompt.py, pasted into every model simultaneously.
Step 3 — Follow-up self-audit. Each model confirms its game, verifies its line, audits assumptions, reviews its unit rating, and states whether it would publish.
Step 4 — Skip assessment. If all models return 0 units / Pass, or fewer than 2 games had clean data, skip and log the reason.
Step 5 — Pick logging. Only picks passing audit and clearing the skip threshold are logged. Void any pick where the model identified the wrong game, assumed unconfirmed lineup data, or where the game had started.
Step 6 — Strongest and consensus identification. Identify the highest-unit play (tiebreak: unit-weighted ROI) and any consensus picks (3+ models same side).
Step 7 — Result and grading. Log result, calculate CLV, update rating calibration per model.

TARGET AUDIENCE
Global — English-speaking sports bettors worldwide. Primary markets: US, Australia, UK, Canada. The site is an analysis and content product. It does not operate as a bookmaker and does not accept wagers.
Profile: follows US sports (NFL/NBA primary); has tried cappers before; skeptical of guaranteed-winner claims; values transparency and data over hype; finds the AI competition angle interesting; wants either one clear play per day or full model-by-model data with unit guidance.
Regional compliance note: rules for paid tipping, affiliate marketing, and gambling advertising vary by market. Market-by-market legal sign-off required before monetising in each region.

MONETISATION PLAN
Phase 1 — Build the record (months 1–6): no paid tier; all picks and records public; compliant affiliate links per market; goal is a verifiable track record with unit-weighted ROI per model.
Phase 2 — Paid tier (month 6+): free tier shows history, leaderboard, yesterday’s results; paid tier ($15–30 USD/month or local equivalent) shows today’s picks pre-game, full reasoning, unit ratings, strongest play of the day, 3-unit play alerts. Affiliate revenue continues.
Phase 3 — Scale (year 2+): B2B data licensing; expand model stable; regional versions with local affiliate relationships.

COMPLIANCE — KEY MARKETS
Working checklist, not legal advice. Per-market legal review required before monetisation.
All markets:

 Responsible gambling messaging on all pick pages
 No guaranteed-profit or specific-return claims
 Model naming reviewed for trademark compliance
 OpenAI / Anthropic / Google / xAI TOS reviewed for gambling-adjacent use
 Privacy policy for subscriber data

Australia: Interactive Gambling Act 2001 affiliate review; paid tipping structure review; ACCC claims substantiation; ABN before income.
United States: per-state affiliate registration; per-state tipping classification; FTC affiliate disclosure.
United Kingdom: ASA/CAP gambling ad compliance; UKGC affiliate/tipster rules; clear non-operator disclaimer.

WHAT MAKES THIS DIFFERENT
FeatureThis siteTypical capperAction Network / CoversNamed independent AI models, separate recordsYesNoNoUnit staking system tied to ROIYesSometimes (units) but not measuredNoUnit-weighted ROI published per modelYesNoNoSkip days published and explainedYesNo — forced actionNoStrongest play surfaced dailyYesNoNoTransparent consensus calculationYesNoPartiallyCLV tracked publiclyYesRarelyOccasionallyRating calibration proven with dataYesNeverNoSelf-audit on every pickYesNoNoBad runs never hiddenYesNoPartiallyGlobal audienceYesUsually region-lockedUS focus

CURRENT PROJECT STATUS
Phase: Research & Validation — automated pipeline running daily
Started: May 2026
Last updated: June 12, 2026

Completed:
- Full viability assessment (market, technical, legal, monetisation)
- Decisions locked: named models; worldwide audience; unit staking system
- First live test (May 27–28 2026): found game ID failures, hallucinated pitcher data, timing problem, inflated edge claims
- Master prompt built (build_prompt.py) with all 6 sport blocks
- Unit staking system designed and live (replaced confidence-score approach)
- Skip rules, consensus layer, strongest-play layer designed
- Automated daily pipeline complete and running (Phases 1–3):
  - fetch_odds.py, fetch_pitchers.py, fetch_weather.py, fetch_teamstats.py, build_prompt.py, run_daily.py
  - log_picks.py / log_all_picks.py — parses model output into per-model JSON
  - fetch_results.py + grade_picks.py — auto-grades picks W/L/VOID, produces grades.json
  - 6 models run via API (run_picks_all.py); 2 models (Opus, Sonnet) via manual paste
- Post-mortem process running daily; model-specific instructions updated after each cycle
- Pick concentration tracking live (pick_concentration.py → docs/concentration_log.csv)
- Model independence problem identified and addressed: prescriptive method mandates
  removed from shared prompt layer after pick-side concentration reached 82.1% (June 8)
- Totals (Over/Under) betting added (June 19): all 8 models self-authored O/U methods;
  TOTAL/TOTAL PRICE/TOTAL UNITS/TOTAL EDGE output slots; 0.5/1.0/1.5 run gate
- Confirm-check watcher built (June 21): 5-script layer (watch_set.py, run_lineup_watcher.py,
  build_prompt.py --confirm-check, query_model.py --confirm-check, grade_picks.py extended)
  re-evaluates every wagered pick when official batting lineup confirms; outcomes:
  HOLD / CANCEL / DOWNGRADE / UPGRADE; grade_picks.py consumes {model}_confirm.json automatically

Key learnings from validation to date:
- Volume bias: all models over-bet early slates. Fixed via professional bettor identity
  framing, 4-point minimum edge gate, slate ceilings, and 3-unit best bet requirement.
- ERA anchoring: ERA without FIP/xERA/SIERA is the most common cross-model reasoning
  failure. Documented in LEARNINGS.md.
- Model independence is the product: homogenising reasoning methods across models
  defeats the core thesis. Shared prompt carries data and format rules only.
- Reasoning sequencing failure: some models ran slate discipline check mid-response.
  Fixed with model-specific pre-compute instruction (Opus, Sonnet).

Next steps (Phase 4+):
- Build stats aggregation: rolling unit-weighted ROI, calibration curves, per-model
  leaderboard across all logged days
- Fix Gemini truncation after ~8 games on large slates (context window constraint)
- Resolve Grok 4.3 Expert evaluation (improved pass discipline; pending formal adoption)
- Implement grades.json per-pick files to enable unit-tier calibration analysis
- Extend pipeline to NBA/NHL when seasons resume (Phase 5)
- Legal/compliance review before affiliate links or paid tier
- Wireframe site after 30-day validation (Phase 6)


FILES IN THIS PROJECT
| File | Purpose |
|---|---|
| docs/AI_CAPPER_PROJECT_INSTRUCTIONS.md | Project overview, goals, rules, current status (this file) |
| docs/CLAUDE.md | Claude Code session context — read at start of every session |
| docs/PROMPT_DESIGN.md | Exact prompt template as generated by build_prompt.py |
| docs/MODEL_INSTRUCTIONS.md | Per-model instructions, updated after each post-mortem cycle |
| docs/LEARNINGS.md | Running log of failures, fixes, and discoveries — never delete entries |
| docs/PIPELINE_OVERVIEW.md | End-to-end workflow from data fetch to graded results |
| docs/model_roster.md | Canonical model list — source of truth for active models |
| docs/TIMEZONE_STANDARD.md | Timezone rules — slate date is always US Eastern, never AEST |
| docs/DATA_ARCHITECTURE.md | Data source priority hierarchy and file format specs |
| docs/STATS_REFERENCE.md | All statistics used in the prompt, organised by sport |
| docs/concentration_log.csv | Daily pick concentration metrics (output of pick_concentration.py) |
| scripts/build_prompt.py | Generates daily prompt from fetched data; contains all 17 instruction blocks |
| scripts/run_daily.py | Master runner — chains all fetch scripts then builds prompt |
| scripts/run_picks_all.py | Sends prompt to all 8 connected model APIs |
| scripts/log_picks.py / log_all_picks.py | Parses model output into per-model JSON |
| scripts/fetch_results.py + grade_picks.py | Fetches scores, grades picks W/L/VOID/cancelled, outputs grades.json |
| scripts/watch_set.py | Builds confirm-check watch set from Run-1 picks |
| scripts/run_lineup_watcher.py | Continuous lineup polling loop; fires confirm-checks per cluster; auto-HOLDs at first pitch |
| scripts/pick_concentration.py | Tracks daily pick-side concentration, appends to concentration_log.csv |

PRINCIPLES — NON-NEGOTIABLE

Never publish a pick on a game that has already started. Void it, log it, move on.
Never edit a pick after it is logged. The record stands regardless of result.
Never hide a model’s losing run. A bad run stays on the leaderboard in full.
Never claim an edge that cannot be explained. Probability and edge derived from the line, not invented.
Never drop a model silently. Removal is announced with a reason; the historical record stays visible.
Never force a play on a skip day. Discipline in not betting matters as much as discipline in betting.
Never inflate units. A 3-unit play is rare by design. Unit-weighted ROI exposes inflation automatically.
The track record is the product. The AI angle, brand, and content are built on top of an honest, unit-weighted record. Without it there is nothing.


End of file — Version 3.2
# AI CAPPER — LEARNINGS LOG

Things that broke, were misunderstood, or need to be remembered.
Add an entry whenever something is discovered or fixed. Never delete entries.

---

2026-06-20: Grok bold-header parse failure — Grok-4.3 occasionally wraps section headers in bold markdown (e.g. `**## GAME: TOR @ CHC**` instead of `## GAME: TOR @ CHC`). The parser's `re.search(r"^## GAME:", ...)` failed to match, returning 0 game blocks and triggering the non-zero exit guard. Fix: added a pre-processing `re.sub` at the top of `parse_response()` in log_picks.py that strips `**...**` wrapping from any `## GAME:`, `## SLATE SUMMARY`, or `## PARLAY` header before the format-detection step. Pattern: `r"\*\*(## (?:GAME|SLATE SUMMARY|PARLAY)[^*]*)\*\*"`. Added "Bold" as a fourth documented format variant in the docstring. Rule: never re-call the API to fix a parse issue — fix the parser and re-run log_picks.py with the existing raw file.

2026-06-20: run_daily.py --with-picks flag removed / never existed. CLAUDE.md referred to `--with-picks` but that flag is not implemented. The correct flow is: (1) `python scripts/run_daily.py mlb --date YYYY-MM-DD` builds prompts; (2) `python scripts/run_picks_all.py --sport mlb --date YYYY-MM-DD` queries all 8 models; (3) `python scripts/log_all_picks.py mlb --date YYYY-MM-DD` logs all picks. run_picks_all.py uses `--sport` as a NAMED flag, not a positional argument. log_all_picks.py uses `sport` as a POSITIONAL argument. Always verify argument signatures before running.

2026-06-19: Totals (Over/Under) betting added to the competition. All 8 models self-authored O/U methods (method_{model}_totals_v1.md) via the totals method-authoring round. Key design decisions: (1) Raw inputs only — models receive wind speed + effect label + stadium LF/CF/RF dimensions and apply their own weather knowledge; no pre-computed wind edge from CrookedFence. (2) Full stakeable bet — TOTAL / TOTAL PRICE / TOTAL UNITS / TOTAL EDGE slots added to output format with their own run-based gate (0.5/1.0/1.5 run thresholds). TOTAL LEAN-only slot was upgraded to full bet slot. (3) load_model_instruction() now loads BOTH the ML/RL method AND the totals method, appending totals under "=== TOTALS (OVER/UNDER) METHOD ===" header. The version-picker (highest N in method_{model}_v{N}.md) applies to both files independently. (4) log_picks.py already supported totals (TOTAL/TOTAL PRICE/TOTAL UNITS/TOTAL EDGE parsing, total_pick dict with _is_total:True). grade_picks.py already graded totals vs opening_snapshot.total.line. No changes needed to either. (5) Dead code warning: the old detailed TOTALS APPROACH block sits inside `if False:` at build_prompt.py line 1737 and is never sent to models. Do not resurrect it — each model now uses its own method.

2026-06-19: CrookedFence (crookedfence.org) integrated as STANDALONE OPERATOR-RUN only — NOT part of the daily pipeline. Sole purpose is reverse-engineering their HR/runs edge model. Two scripts: (1) fetch_wind_edge.py — fetches data.json (today's predictions) + results.json (yesterday's graded outcomes), archives both to data/mlb/crookedfence_archive/YYYY-MM-DD_{predictions,results}.json, writes clean wind_edge.json, then auto-calls compile_dataset(). Run manually with: python scripts/fetch_wind_edge.py. (2) compile_crookedfence_dataset.py — flattens all archived results into crookedfence_dataset.{csv,jsonl}, de-duplicated on (game_date, away, home). Schema note: CF JSON has away/home as plain abbr strings (NOT objects). Lesson: fetch_wind_edge.py originally used urllib which timed out on Windows due to SSL cert store issues — fixed by switching to `requests` library. Stadium dimensions now come from a static STADIUM_DIMENSIONS dict (all 30 MLB parks, LF/CF/RF hardcoded in build_prompt.py) — zero CrookedFence dependency for the daily prompt. Wind continues to come from Open-Meteo (fetch_weather.py), which already provides OUT/IN/IN-CROSS/OUT-CROSS effect labels computed per-park against the wind bearing.

2026-06-17: Kimi shared-budget failure — root cause, fix, and validation. Root cause: kimi-k2.6 uses max_tokens as a SHARED budget for reasoning_content + content combined. On a 15-game slate with thinking enabled, the reasoning trace consumed the entire 32k ceiling before the content field could start writing. Result: content="", reasoning_content = truncated trace (10 of 15 games, ending mid-sentence). The old code silently fell back to saving reasoning_content as kimi_raw.txt — a 16k file with no PICK:/UNITS:/EDGE: fields. NOTE: disabling thinking for Kimi was explicitly rejected. Kimi's extended thinking is its handicapping method; disabling it breaks model independence and the clean-comparison principle v2 is built on. Thinking stays enabled. Fix applied in three parts: (1) Raised KIMI_MAX_TOKENS_PICKS and KIMI_MAX_TOKENS_POSTMORTEM from 32k/16k to 64k each. Gives the reasoning phase room to complete on full slates while leaving ~30k for structured output. (2) Switched _call_kimi() to streaming (stream=True, stream_options={"include_usage": True}). Streaming prevents HTTP timeout during long reasoning phases. stream_options include_usage is required — without it all chunk .usage fields are null and token counts return 0. Streaming accumulator uses hasattr(delta, "reasoning_content") / getattr() pattern — NOT direct attribute access, which raises AttributeError on the typed SDK delta object. (3) Empty content field is now a loud FAILED state: never write kimi_raw.txt from reasoning trace; write kimi_reasoning_raw.txt diagnostic only; exit(1). Post-fix validation on 2026-06-16 15-game slate: input 26,958 tokens, output 28,349 tokens, 35,651 tokens of headroom remaining. 15 game blocks parsed cleanly (1 bet: SEA ML -147 1u WIN). Real post-mortem produced 5,037 chars. Three failure classes for retry: (a) empty raw → re-call API; (b) raw present + parse failed + known format → re-parse only (do NOT re-call API); (c) raw present + parse failed + unknown format → human extends parser, then re-parse. Parser also widened to accept GAME N: numbered format (belt-and-braces against future reasoning-trace edge cases). RECON WARNING: two successive recon passes mischaracterised this file — the first stopped at line 80 (file has 111 lines), the second assumed all-15-games coverage. Always verify raw-file claims against actual field content AND full file length before diagnosing.

2026-06-17: Post-mortem integrity gate applied — counts.games==0 in picks JSON → skip post-mortem API call. Triggered by the Jun 16 fabrication incident (see below). Gate is belt-and-braces: inner guard in query_model.py exits before the API call with a clear INTEGRITY GATE message; outer guard in run_daily_2.py calls _check_picks_integrity(), separates ok_models from skip_models, and passes --models ok_models to run_postmortem_all.py so bad models are filtered before any subprocess is spawned. run_postmortem_all.py gained a --models comma-separated allowlist parameter. Gate condition is counts.games (not counts.bets) — grok had counts.games=14 with counts.bets=0 (all passes), which is a valid all-pass slate and must not trigger the gate. Gate triggers only on zero parsed game blocks. Contaminated Jun 16 gemini_postmortem.txt and kimi_postmortem.txt moved to picks/mlb/2026-06-16/quarantine/. KIMI block recovered after 64k fix and real post-mortem run 2026-06-17; KIMI inserted into picks/mlb/2026-06-16/post_mortem_2026-06-16.txt between DEEPSEEK and QWEN. GEMINI remains permanently quarantined (pure fabrication). 7 valid blocks in final aggregate: grok, chatgpt, deepseek, kimi, qwen, opus, sonnet.

2026-06-17: Two orchestrator scripts added to replace manual step-by-step pipeline runs. (1) run_daily.py gained an opt-in --with-picks flag chaining run_picks_all → log_all_picks after prompt generation. Default behaviour unchanged (prompts-only) to preserve the pre-send prompt-review checkpoint and avoid firing 8 paid API calls on every data run. The picks chain gates on "at least one non-empty _raw.txt exists" (matching run_postmortem_all's 0-byte guard) rather than run_picks_all's exit code — because exit code = number of failed models (partial failure is non-zero) and we want to log whatever picks were generated. (2) run_daily_2.py is the new post-game counterpart, chaining fetch_results → fetch_confirmed_data → run_postmortem_all. Critical ordering fix: confirmed-data must run before post-mortems so query_model.py can inject the confirmed-data section. Guards: (a) pre-flight checks that {model}.json logged pick files exist (against actual roster names, not any *.json) before firing API calls; (b) partial-aware confirmed-data check compares confirmed_data.json game count against boxscore-eligible games in games.json (postponed/cancelled/suspended excluded from denominator to avoid false-halts on normal postponements); halts by default if confirmed < eligible, --skip-confirmed overrides. Halt-then-rerun path is clean: fetch_results.py is fully idempotent (placeholder skip, exist_ok folders, stub existence checks); on re-run after a confirmed-data halt, no postmortem files exist yet so run_postmortem_all fires all 8 models without any wrongly-skipped entries. Both scripts import run_step/PYTHON/SCRIPTS_DIR/PROJECT_ROOT/_load_dotenv from run_daily.py — not duplicated.

---

2026-06-16: Post-mortem fabrication incident — two models ran post-mortems with no game context and produced contaminated output. The two failure mechanisms differed. (1) Gemini: 503 service-unavailable during picks call → 0-byte gemini_raw.txt → log_picks wrote gemini.json with counts.games=0 → _build_outcome_summaries() returned empty → post-mortem fired via the raw_text fallback but raw_text was also empty → Gemini invented an entire slate from scratch (fabricated NYY -1.5 as best bet, etc.). Pure fabrication with zero real context. PERMANENTLY QUARANTINED. (2) Kimi: true root cause was the shared max_tokens budget (see 2026-06-17 Kimi entry above) — reasoning trace exhausted 32k ceiling before content field could start. kimi_raw.txt (16k bytes) was the reasoning trace only, with no PICK:/UNITS:/EDGE: fields → kimi.json counts.games=0. NOTE: this was mis-diagnosed twice during recon. First diagnosis: "GAME N: format mismatch." Second diagnosis: "complete 15-game structured output, parse failure only." Actual finding: 111-line file ending mid-sentence at GAME 10 — truncated reasoning trace, not structured output. GATE RULE: counts.games==0 in picks JSON → skip post-mortem regardless of cause. Both failure modes produce unacceptable output. Both files quarantined to picks/mlb/2026-06-16/quarantine/ with README. Kimi RECOVERED after 64k fix — real post-mortem written 2026-06-17, quarantine README updated to note recovery.

2026-06-16: Tested Grok June 15 post-mortem at reasoning_effort=high vs default to check whether shallow S3/S4 NONE output was a reasoning-budget constraint. Result: high reasoning produced a REGRESSION — S1 factual self-contradiction (denied a best bet that S2 of the same response confirmed existed), S3/S4 still NONE, confirmed-data reasoning shallower (blank pre-game reason vs original citing actual wRC+ numbers), 1,797 reasoning tokens spent for no depth gain. Conclusion: Grok's post-mortem incuriosity is dispositional, not a config artifact. Reasoning budget is not the lever. Kept postmortem at default reasoning. One-slate test, but clear enough to rule out the reasoning-effort hypothesis. Original response restored from backup; shared aggregate never modified.

---

2026-06-16: Three fixes applied to the Jun 15 post-mortem infrastructure. (1) Grok max_tokens parity: GROK_MAX_TOKENS_POSTMORTEM = 16000 added to query_model.py and wired into the --postmortem path (previously fell through to the 8000 default; 8000 did NOT cause the Jun 15 earlier-run truncation — root cause was a write/connection interruption in the first run, resolved by the 19:11–19:28 re-run; parity added as a preventative). (2) Sonnet duplicate CONFIRMED LINEUP field: Sonnet's MIA@PHI block in post_mortem_2026-06-15.txt emits "CONFIRMED LINEUP vs YOUR ASSUMPTION:" twice — first a long detailed paragraph (line 782), then a short summary sentence (line 784). Template and render layers confirmed clean (field appears once in each). This is an isolated Sonnet output artifact. The tracker's re.search() extracts the first (longer) occurrence only; the second is silently ignored. Data left as-is. (3) log_confirmed_tracker.py section regex bug: _parse_confirmed_blocks() used (?=\n##|\Z) as the terminator, which also fires on \n### (three hashes start with ##), causing the section match to stop immediately at the first ### GAME: sub-header — returning near-empty sections for all models and zero game blocks. Fixed to (?=\n##[^#]|\Z). Additional format variants handled: Grok uses **CONFIRMED DATA EVALUATION** (bold, no ## prefix) and GAME: without ### — section regex extended to (?:##\s+|\*\*) prefix, game split changed to (?:^|\n)(?:#{2,4}\s+)?GAME: with re.MULTILINE; Kimi uses #### GAME: (four hashes) — covered by same fix; Opus embeds the game name in the section header (## CONFIRMED DATA EVALUATION — TB @ LAD) with no ### GAME: sub-header — detected via em-dash in header_suffix, entire body treated as one game block with YOUR CALL left empty (not labeled in Opus body text). After fix: all 8 models parse correctly (chatgpt 4 games, deepseek 2, gemini 5, grok 1, kimi 1, opus 1, qwen 2, sonnet 5).

2026-06-16: Confirmed-data evaluation added to post-mortem pipeline. fetch_confirmed_data.py pulls post-game boxscore (batting order + HP umpire name) for every game on a slate; wRC+ vs opposing starter's handedness looked up from static splits files already in the pipeline. Umpire season K%/BB% NOT in MLB Stats API (confirmed via probe) — umpire name only; model uses training knowledge of zone tendencies. _build_confirmed_section() in query_model.py injects the section into post-mortems for bet/lean games only (not passes). log_confirmed_tracker.py parses model responses and appends to picks/trackers/confirmed_data_tracker.csv. CRITICAL TRACKER RULE: headline metric is hypothetical_unit_delta summed ONLY over reason_supported=YES rows — would-change calls with no specific pre-game reason are marked UNSUPPORTED and excluded (likely hindsight-driven). Two totals always printed: supported_delta (real signal) and unsupported_delta (discarded). This measures whether to build a live confirmed-data feed; result is directional (postmortem hindsight context), not proof — a live A/B would be required for proof.

2026-06-15: Jun 14 post-mortem candidates logged to picks/candidates/. Regression-pattern (regress ERA/bullpen ERA toward xFIP/FIP peripherals) captured as BUILDING for deepseek, sonnet, opus — each proposed a version; needs one more slate or CLV confirmation before promotion. Kimi bullpen-quantification (+0.0–+1.5pt adjustment on rest differential) captured as BUILDING, one slate only — hold. Qwen slate-ceiling replacement REJECTED: ceiling is a fixed competition rule models cannot rewrite, and the cited evidence (KC '19.25 bullpen ERA') was a corrupted aggregate since removed from the prompt.

2026-06-15: Gemini flagged ATL@NYM pitchers (Peralta, Williams) as wrong-team in its June 14 post-mortem with HIGH confidence. Investigation: data was CORRECT — Peralta is a 2026 Met, Williams traded to NYM. Gemini's complaint was stale training knowledge overriding live data — exactly the failure the data-over-model-knowledge principle exists to prevent. No data bug. Added build-time currentTeam validation in fetch_pitchers.py as a guard against genuine future API glitches. Key lesson: a HIGH-confidence model post-mortem claim was entirely wrong — reinforces that promotion must be evidence-gated, never confidence-gated.

2026-06-15: calibration mechanism built (calc_calibration.py). Reads all picks/{sport}/{date}/{model}.json files, filters to action=="bet" and result in (win/loss/push), computes: W-L record, unit-weighted ROI, avg stated edge (numeric "X pts" new format; word labels "strong/real/medium" mapped to rough equivalents for pre-Jun-10 continuity), avg CLV in American-odds cents (positive = beating closing price). Outputs one-paragraph summary per model to picks/calibration/{model}_calibration.md. Prints PROVISIONAL warning when n < 20 graded bets. NOT yet wired into post-mortems — inject once most models have ~20 graded bets. Jun 15 snapshot: chatgpt 8 bets (provisional), deepseek 43 bets -33.2% ROI +21.6c CLV, gemini 42 -12.2% +36.5c, grok 44 -16.5% +22.9c, kimi 21 -39.6% +30.1c, opus 32 -24.2% +37.0c, qwen 48 -22.6% +30.1c, sonnet 58 +2.2% +24.4c. All models show positive CLV (we're buying better-than-closing prices) but negative ROI — early-season variance expected at these sample sizes.

2026-06-15: lossless token-reduction pass on build_prompt.py. 5 changes applied: (1) lineup/umpire hoisting — if all games unconfirmed/unassigned, one header line replaces per-game repetition; per-game blocks suppressed via hoist_lineups/hoist_umpire flags on build_game_block(); (2) removed "run fetch_lineups.py closer to game time" tail from both-unconfirmed fmt_lineups() case; (3) suppressed "no movement yet" line entirely when opening==current snapshot; (4) venue name only, dropped city/state ("PNC Park, Pittsburgh, PA" → "PNC Park"); (5) collapsed 4-line pitcher block into 1 pipe-delimited line per pitcher — _fmt_pitcher_oneline() folds fmt_pitcher() + _fmt_starter_advanced_lines() + fmt_recent_starts() into single line with | separators, L3 starts semicolon-separated. All numeric values preserved byte-for-byte. RULE: reconstruction test required after any prompt formatting change — rebuild prompt for a known date and diff a game block to confirm zero values lost. Never abbreviate by omitting numbers, grades, or stats; only remove prose, labels, and repetition.

2026-06-15: added factual game-outcome summaries to post-mortem prompt. _build_outcome_summaries() in query_model.py builds one OUTCOME line per game from picks/{model}.json + results/{sport}/{date}/results.json, injected before the post-mortem template. Bets listed first (with team abbr, price, WIN/LOSS), then leans, then passes. Anti-hindsight guard injected verbatim: "GAME OUTCOMES below are factual results. Use them ONLY to identify whether a signal that was AVAILABLE IN THE PRE-GAME DATA predicted the outcome..." NOTE: starter IP/ER and "bullpen decisive" are not in current data files (only scores available); those fields would require extending fetch_results.py to call MLB statsapi. pick_side field in picks JSON is "away"/"home" string — resolved to team abbr via result record.

2026-06-15: first method promotion under the v2 loop. Promoted L14 small-sample discount to method_deepseek_v2.md, method_sonnet_v2.md, method_qwen_v2.md. Each model gets its own version: deepseek uses 2:1 AGG/L14 floor with 50% max shift; sonnet uses graduated IP table (≥35IP 60/40, 20-34IP 70/30, 11-19IP 40/60, <11IP anecdotal); qwen uses L14 IP<12 threshold blending back to season SIERA/xFIP. Grok deliberately excluded — it demonstrated the L14 flaw on June 14 but did not propose the fix in its post-mortems. It must reach that conclusion via its own post-mortem loop before promotion. v1 files retained as history. load_model_instruction() upgraded to auto-select highest version number (glob method_{model}_v*.md, pick max N).

2026-06-15: bullpen rendering was hard-capped at Closer + 2 Setup = 3 arms, silently dropping Middle Relievers and 'Closer Committee' arms (e.g. KC's Schreiber, 2.83 ERA, was invisible). Now renders top 6 by role priority (Closer → Closer Committee → Setup → Middle → Long), IL arms excluded. Matters more after removing the team ERA aggregate — per-reliever lines are now the only bullpen signal, so models need the innings 6-7 arms, not just the back end.

2026-06-15: removed pre-computed team bullpen ERA aggregate from prompt. It was the source of the KC 19.25 bug (averaged IL'd/0.1-IP arms). Models now form their own bullpen read from raw per-reliever lines — consistent with v2 (supply evidence, not verdicts). Same reasoning as the earlier removal of the '0 of 3 fresh' verdict. Two removal sites in build_prompt.py: (1) fmt_bullpen() header line ERA X.XX sourced from team_bullpen_era field; (2) per-reliever section mean(r["era"]) rendering as "Bullpen ERA (season avg)". team_bullpen_era field stays in games.json and fetch_bullpen.py console output — only removed from prompt rendering.

2026-06-14: fetch_covers_lines.py built. Covers.com provides opening RL and total prices plus full movement history via linehistorybrick API. Plain urllib (no Playwright needed for history calls — only for main page gameId extraction). AU IP detection serves bet365/Betway/WH data automatically. betType=spread call returns all tab HTML; betType controls default tab only. ML history excluded — sourced from prediction markets on US IPs. Opening price = earliest timestamp in history, not a labelled OPEN row. Game rows are tr.oddsGameRow elements; team abbrs in .away-cell strong and .home-cell strong; gameId from matchup link href. COVERS_ABBR_REMAP has 3 entries only: WSH→WAS, CWS→CHW, ARI→AZ. Movement stored newest-first in JSON, reversed to oldest→newest for prompt display. Step 4/5 complete: fmt_covers_lines() in build_prompt.py renders after ODDS block; fetch_covers_lines.py added as optional step 2 in run_daily.py (after fetch_odds.py, before fetch_pitchers.py).

2026-06-14: FanGraphs architecture confirmed static-only. Code inspection of all scripts/ confirms zero live FanGraphs HTTP calls. fetch_pitcher_advanced.py uses pybaseball but only for Baseball Savant (Statcast) endpoints — statcast_pitcher_expected_stats and statcast_pitcher_exitvelo_barrels. The pybaseball FanGraphs helpers (pitching_stats, fg_pitching_data) were attempted in 2026-06 and return HTTP 403; this is documented in the fetch_pitcher_advanced.py docstring. FanGraphs is served as static .txt files only, loaded by load_static_data.py. CLAUDE.md CONSTRAINTS updated to codify this. HTML reference doc (fangraphs_MLB_download_reference.html) has two classes of mismatch with current reality: (1) all file extensions documented as .csv but actual files use .txt — the operator renamed them during manual download; (2) pitchers_last14.txt and team_barrels.txt are not documented in the HTML (both added after it was written). HTML left as-is since it documents the download procedure, not the file names.

2026-06-14: First method promotion candidates logged. L14 small-sample over-weighting flaw independently identified by DeepSeek, Sonnet, and Qwen across two slates (June 12-13) with pre-game evidence cited and medium confidence. CANDIDATE METHOD CHANGE — v1.1 appended to method_deepseek_v1.md, method_sonnet_v1.md, method_qwen_v1.md. Proposes 2:1 minimum AGG/L14 weighting ratio and 50% maximum L14 edge influence cap. Not yet adopted — promote to v2 if it recurs or shows CLV improvement over next 10+ bets. Grok, Kimi, Opus, ChatGPT, Gemini methods NOT modified — they either didn't make this error or handle it differently in their existing method docs.

2026-06-14: Post-mortem guard added. run_postmortem_all.py now aborts early if all *_raw.txt picks files for the target date are 0 bytes. This prevents wasted API calls when the picks pipeline was never run for that date (e.g. when the ET date ticks over at midnight and the script defaults to the new day). Root cause: run_postmortem_all.py defaulted to today_et() which returned 2026-06-14 (ET date had ticked over), but picks/mlb/2026-06-14/ existed with 0-byte files from a prior aborted run — no data/daily folder for June 14 existed. All 8 models responded to an empty template, producing garbage. The correct date (June 13) was run separately with --date 2026-06-13 and completed cleanly.

---

2026-06-13: Two data-layer additions driven by multi-model S3 convergence from the June 12 post-mortem. (1) L14 small-sample flag: if L14 IP < 12, the L14 line now appends "[small sample — NIP]" at point of use in build_prompt.py. Five of eight models independently requested some form of IP-threshold disclosure in their S3. (2) Per-reliever usage grid restored: "Usage last 6: ..." line re-added to _reliever_lines in _fmt_bullpen_static. The raw pitch-count evidence is back; the computed verdict lines ("Taxed", "High-leverage arms available") remain removed per v2 independence principle. Raw evidence in, conclusions out.

2026-06-13: Claude Fable 5 removed from active roster. Available for June 12 picks, then Anthropic gated it behind Mythos Access enrollment (404 "not available, use Opus 4.8"). Roster back to 8: kimi, chatgpt, opus, gemini, deepseek, qwen, sonnet, grok. Fable's June 12 picks/grades retained per the never-drop-silently principle. Not remapped to opus — would create a duplicate-model entry and contaminate the comparison.

2026-06-12: v1→v2 post-mortem routing change — v1 appended all model responses into one shared post_mortem_{date}.txt and the "already done" guard scanned that file for ## MODEL RESPONSE markers. v2 writes each model's response to its own picks/{sport}/{date}/{model}_postmortem.txt (primary output) AND appends to the shared file (human-readable aggregate only). The guard now checks for the per-model file's existence — simpler and more reliable. run_postmortem_all.py updated from 6 to 9 models (opus, sonnet, fable added; manual-paste note removed). Post-mortem output is NOT auto-injected anywhere — method promotion is a future, manually-gated step.

2026-06-12: data-layer trim — removed L3 ERA suffix from fmt_recent_starts (kept per-start IP/ER/K/BB) and removed per-reliever Usage-last-6 grid from bullpen block (kept fresh-count/taxed/ERA verdicts). Reduces prompt noise; _usage_str now unused but retained as usage_last6 still feeds taxed-arms calc.

2026-06-12: removed pre-computed bullpen verdict labels (fresh count, taxed list) from prompt — models assess freshness from raw reliever data per v2 independence principle.

---

## FANGRAPHS BLOCKED VIA PYBASEBALL (xFIP / K% / BB% / BABIP)

**Date discovered:** 2026-06-04
**Updated:** 2026-06-05 — FIP resolved via local computation (see entry below)

Both `pitching_stats()` and `fg_pitching_data()` in pybaseball 2.2.7 return
HTTP 403. FanGraphs changed their `leaders-legacy.aspx` endpoint and pybaseball
has not yet been updated to match the new URL structure.

Affected metrics still unavailable: xFIP, K%, BB%, BABIP (all FanGraphs-only).
FIP is now computed locally from MLB Stats API components — see entry below.

Workaround in use: fetch_pitcher_advanced.py uses Baseball Savant instead:
- `statcast_pitcher_expected_stats` → xERA
- `statcast_pitcher_exitvelo_barrels` → Hard Hit % (ev95percent), Barrel %
- K/9 computed from existing strikeouts + innings_pitched fields
- FIP computed from HR/BB/HBP/K/IP — no FanGraphs needed

If FanGraphs access is restored: add a `fetch_fangraphs_pitching(year)` block
to fetch_pitcher_advanced.py and include xFIP, K%, BB%, BABIP.

---

## OPENING_SNAPSHOT TIMING — LINE MOVEMENT IS ONLY USEFUL IF RUN EARLY

**Date discovered:** 2026-06-02
**Relevant scripts:** `fetch_odds.py`, `build_prompt.py`

`opening_snapshot` is written on the first fetch of each day and never overwritten.
It is our proxy for the opening line. For it to be a useful line-movement reference,
the first fetch must happen early — before significant money has moved the line.

The target run time is Australian evening, which is US morning ET. This is the
"golden window" defined in `docs/TIMEZONE_STANDARD.md`:

  Australian evening 6 PM – 11 PM AEST  =  US morning 4 AM – 9 AM ET

If `fetch_odds.py` is run during this window, `opening_snapshot` captures a genuine
early line and subsequent fetches can show meaningful movement.

If the script is run late in the day (e.g. 2 PM ET, shortly before first pitch),
`opening_snapshot` and `current_snapshot` will be nearly identical and line movement
will show no change. That is still valid data — it just means the tool was run too
late to capture the open.

**Today's test case (2026-06-02):**
- Single fetch run at: `2026-06-02T03:42:42Z` UTC
- That is: **11:42 PM ET on June 1** / **1:42 PM AEST on June 2**
- Golden window starts: 4:00 AM ET June 2 / 6:00 PM AEST June 2
- The fetch was 4h 18min BEFORE the golden window — earlier than ideal but good
  for capturing near-opening lines (MLB lines for June 2 typically open late June 1 ET)
- Hours before first pitch (DET @ TB 6:41 PM ET): **19 hours**
- Only one fetch has been run, so `opening_snapshot.fetched_at` = `current.fetched_at`
  — no line movement data yet. This is expected.

**Operational lesson:** Run `fetch_odds.py` once during the golden window to lock the
opening snapshot, then run again 1–2 hours before first pitch for the current lines.
Line movement = diff between those two runs.

---

## COVERS UMPIRES PAGE IS A HISTORICAL STATS DIRECTORY, NOT A DAILY ASSIGNMENTS PAGE

**Date discovered:** 2026-06-01
**Relevant scripts:** `scripts/scrape_umpires.py` (now obsolete)

`https://www.covers.com/sport/baseball/mlb/umpires` is titled "MLB Umpires By Name".
It is an alphabetical directory of all active umpires linking to their individual
career stats pages. It does NOT show today's game assignments.

The page contains no per-game HP assignment data. The regex parser in
`scrape_umpires.py` found zero matches because there is nothing to match.

**Fix:** `fetch_umpires.py` replaces this entirely, using the MLB Stats API boxscore
endpoint (`/api/v1/game/{gamePk}/boxscore`) which is free, official, and returns the
full umpire crew including the plate umpire. Assignments populate ~1–2 hours before
first pitch — run `fetch_umpires.py` at that time, not in the morning.

`scrape_umpires.py` remains in the repo for reference but should not be run.

---

## WINDOWS CONSOLE ENCODING — UNICODE CHARACTERS IN PRINT() CRASH ON WINDOWS

**Date discovered:** 2026-06-02
**Relevant scripts:** all scripts

Windows PowerShell and the default Python console use cp1252 encoding, which cannot
display Unicode characters such as `→` (U+2192), `═` (U+2550), `°` (U+00B0),
or `—` (U+2014). Any `print()` statement containing these characters crashes with:

  UnicodeEncodeError: 'charmap' codec can't encode character

**Fix:** Replace `→` with `->` in all `print()` statements across all scripts.
Unicode characters in file output (e.g. `prompt.md`) are fine — files are always
opened with `encoding='utf-8'`. Only `print()` to the Windows console is affected.

Checked and fixed in: `fetch_odds.py`, `fetch_pitchers.py`, `fetch_umpires.py`,
`fetch_weather.py`.

---

## THE ODDS API HISTORICAL ENDPOINT IS TOO EXPENSIVE FOR FREE TIER

**Date discovered:** 2026-06-02
**Relevant scripts:** `fetch_odds.py`

`GET /v4/historical/sports/{sport}/odds` returns line snapshots at 5–10 minute
intervals going back to 2020. It could provide true opening lines (when lines
first posted, 1–3 days before game day).

**Cost:** 10 credits × 1 region × 3 markets = **30 credits per call**.
On the free tier of 500 credits/month that is only ~16 calls before exhaustion.
Not viable for daily use.

**Decision:** Do not use the historical endpoint. Our `opening_snapshot` from the
first morning fetch is a sufficient opening line proxy for the purposes of this
project. If the project moves to a paid API tier, revisit this for true market-open
lines.

---

## ALT MARKETS NOT YET IMPLEMENTED — PLANNED FUTURE EXPANSION

**Date noted:** 2026-06-02
**Relevant scripts:** `fetch_odds.py`, `build_prompt.py`

The Odds API supports alternate markets: alt totals, alt run lines, alt spreads,
player props (available since May 2023 on historical endpoint). These are not
currently fetched or displayed.

**Decision:** Out of scope for now. When the core pipeline is stable and validated
over 30+ days, revisit adding:
- Alt totals (e.g. team totals, first 5 innings)
- Player props (strikeouts, hits, home runs)
- Alt run lines (+/- 0.5 for key games)

Each alt market costs additional API credits. Plan accordingly before enabling.


----

POST-MORTEM JUNE 2 — CONSENSUS FINDINGS

After 8 model post-mortems on the June 2 slate, these 
improvements were requested by multiple models:

1. Pitcher FIP/xERA (7/8 models) — prevents over-staking 
   on low ERA with small samples. Source: Baseball Savant, 
   FanGraphs. Should be automated in pipeline.

2. Bullpen usage last 3 days (5/8 models) — fatigue/
   availability for games where starter exits early. 
   Source: FanGraphs, RotoWire.

3. Confirmed lineups + platoon splits (3/8 models) — 
   LHP/RHP performance splits. Source: FanGraphs.

These should be added to the data pipeline after Phase 3 
is complete.

----

FanGraphs is behind Cloudflare Turnstile — blocks both 
plain HTTP and Playwright. Do not attempt to scrape 
FanGraphs. Use MLB Stats API or pybaseball as alternatives.

----

CORRUPTED ODDS DATA — implausible prices from TheOddsAPI
Discovered June 3 post-mortem. Prices like -10000 and 
+10000 occasionally appear in best_available calculations,
likely from bad bookmaker data in the API feed. These 
corrupt model reasoning by appearing as extreme line 
movement. Fix: validation filter rejecting prices outside 
-3000 to +3000 applied at fetch time in parse_bookmaker().

---

## PITCHER LAST-3-STARTS ROLLING FORM ADDED

**Date added:** 2026-06-05
**Relevant scripts:** `fetch_pitcher_advanced.py`, `build_prompt.py`

Post-mortems on June 2 and June 3 slates identified that models were
over-relying on season ERA without checking recent trend. Pitchers like
Schlittler (1.89 ERA), Martin (2.61 ERA), and Soroka (3.23 ERA) had
small samples or deteriorating recent form not visible from season totals.

Fix: `fetch_pitcher_advanced.py` now calls the MLB Stats API game log
endpoint for each pitcher:
  GET /api/v1/people/{personId}/stats?stats=gameLog&group=pitching&season=YEAR&gameType=R

Filters to starts only (gamesStarted == 1), takes last 3, computes
rolling ERA. Stored as `pitcher["recent_starts"]` in games.json.
`build_prompt.py:fmt_recent_starts()` renders it as a second line
under each pitcher's season stat line. Omitted silently if < 1 start.

---

## CONFIRMED LINEUPS AND IL ABSENCES ADDED

**Date added:** 2026-06-05
**Relevant scripts:** `fetch_lineups.py`, `build_prompt.py`, `run_daily.py`

Post-mortems identified that models assumed full-strength lineups when
a key middle-of-order bat may have been absent. A missing bat can swing
expected run output by 0.5-1.0 runs.

Two MLB Stats API endpoints used (no auth required):
  Lineups:  GET /api/v1/game/{gamePk}/lineups
  IL:       GET /api/v1/teams/{teamId}/roster?rosterType=40Man&season=YEAR

Lineups are only confirmed ~2-3 hours before first pitch. Morning runs
will see status "not_yet_confirmed" — this is normal, not an error.
LINEUPS section is omitted entirely from the prompt if fetch_lineups.py
has never run (no noise for morning-only workflows).

Requires: game["mlb_game_pk"] from fetch_pitchers.py,
          ctx["team_away/home"]["team_id"] from fetch_teamstats.py.
Added to run_daily.py pipeline after Team Stats as an optional step.

---

## LINE MOVEMENT FLAG (>30 PTS) ADDED

**Date added:** 2026-06-05
**Relevant script:** `build_prompt.py`

Opus flagged in the June 3 post-mortem that four games had large ML
movements signalling unknown roster changes and models either ignored
these or passed without investigation.

Fix: `build_prompt.py:_big_move_note()` fires a NOTE annotation after
the Line move row when either side of the ML moves >30 points absolute
value between opening_snapshot and current_snapshot. Identifies which
team the money moved toward and instructs models to treat pitcher/lineup
data as potentially stale and verify via web access.
Only fires when both snapshots exist with different timestamps (real
movement, not a single-fetch day).

---

## FIP COMPUTED FROM MLB STATS API COMPONENTS

**Date added:** 2026-06-05
**Relevant scripts:** `fetch_pitchers.py`, `fetch_pitcher_advanced.py`, `build_prompt.py`

FanGraphs FIP is unavailable due to Cloudflare Turnstile blocking all
scraping attempts (plain HTTP and Playwright both return 403/challenge).
FIP is now computed directly from MLB Stats API season stat components
already fetched by fetch_pitchers.py:

  FIP = ((13 × HR) + (3 × (BB + HBP)) - (2 × K)) / IP + 3.10

Components used: homeRuns, baseOnBalls, hitBatsmen, strikeOuts,
inningsPitched — all from the standard
/people/{id}/stats?stats=season&group=pitching endpoint.

FIP_CONSTANT = 3.10 for the 2026 season. Update this value each new
season by checking the published league FIP constant.

Three new fields added to fetch_pitchers.py parse_player_stats():
  home_runs  (homeRuns), walks (baseOnBalls), hit_batters (hitBatsmen)

Computed in: fetch_pitcher_advanced.py → compute_fip()
Stored in:   games.json context["pitcher_away/home"]["fip"]
Displayed:   build_prompt.py fmt_pitcher() — sits between ERA and xERA

Note: xERA (Baseball Savant statcast) remains alongside FIP.
They measure different things — FIP is defence-independent ERA, xERA
is contact-quality based. Both are useful. A pitcher with low FIP and
low xERA has converging evidence of genuine skill.

---

## RUN_DAILY.PY PYTHON ENVIRONMENT MISMATCH

**Date discovered:** 2026-06-05

`run_daily.py` was invoking child scripts via `sys.executable`, which resolved
to the hermes-agent managed venv (Python 3.11). `pybaseball` is installed under
Python 3.12 only. This caused `fetch_pitcher_advanced.py` to fail silently every
run — the pipeline continued but all advanced pitcher stats (FIP, xERA, HH%,
Brl%, K/9, last-3-starts) were absent from the prompt with no visible warning.

**Fix applied:** replaced `sys.executable` with a hardcoded constant in
`run_daily.py` pointing to the Python 3.12 interpreter:

```python
PYTHON = r"C:\Users\marko\AppData\Local\Programs\Python\Python312\python.exe"
```

This path is machine-specific. If the project is moved to a new machine or the
Python 3.12 install location changes, update this constant before running the
pipeline.

**Option A (install pybaseball into the hermes venv) was not available** because
the hermes-agent venv was created without pip and cannot accept package installs.

**Interim fix also applied:** optional step failures now print a visible `!!!
WARNING` banner with the exact re-run command instead of a quiet one-liner. This
catches any future environment issues before they silently degrade prompt quality.

---

## FANGRAPHS STATIC FILES — TEAM ABBREVIATION DIVERGENCE

**Date discovered:** 2026-06-06
**Relevant scripts:** `scripts/load_static_data.py`

FanGraphs uses different team abbreviations for 6 teams than TheOddsAPI (which populates
`games.json`). Any code that joins on team abbreviation will silently produce no matches
for these teams unless the mapping is applied at load time.

| games.json abbr | FanGraphs abbr | Team |
|---|---|---|
| AZ | ARI | Arizona Diamondbacks |
| KC | KCR | Kansas City Royals |
| SD | SDP | San Diego Padres |
| SF | SFG | San Francisco Giants |
| TB | TBR | Tampa Bay Rays |
| WAS | WSN | Washington Nationals |

**Fix:** `load_static_data.py` defines `_FG_TO_GAMES` and `_GAMES_TO_FG` dicts.
All loaders remap FanGraphs codes to games.json codes at parse time so downstream code
always receives games.json-style abbreviations. Never use FanGraphs abbreviations anywhere
outside `load_static_data.py` itself.

---

## BULLPEN.TXT MULTI-HEADER STRUCTURE (FANGRAPHS EXPORT)

**Date discovered:** 2026-06-06
**Relevant scripts:** `scripts/load_static_data.py:load_bullpen()`

FanGraphs Bullpen Usage export is a single TSV containing all 30 teams concatenated.
Each team block has 3 non-data rows before pitcher rows:
1. Team name row — col 0 is the full team name (length > 5)
2. "Pitcher Usage" separator row — col 1 is blank
3. Column header row — col 0 == "Pitcher"

The parser skips all three row types; anything that passes all three filters is a real
pitcher row. The column header row repeats between teams — the first occurrence is used
to extract day labels (e.g. "Jun 5", "Jun 4") which are stored in
`bullpen_data["_meta"]["day_labels"]`. This keeps day labels accurate across re-downloads
with no code change needed.

---

## PARK FACTORS FILE KEYED BY TEAM NICKNAME, NOT ABBREVIATION

**Date discovered:** 2026-06-06
**Relevant scripts:** `scripts/load_static_data.py:_park_factors_file()`

FanGraphs park factors export uses full team nicknames as row labels ("D-backs",
"Giants", "Nationals", etc.) — not abbreviations. A separate mapping dict
`_PF_NAME_TO_GAMES_ABBR` translates these nicknames to games.json abbreviations.

Without this mapping, teams whose FanGraphs nickname does not match their abbreviation
(D-backs, Giants, Nationals, Padres, Rays, Royals) silently get no park factor data.
The loader now keys all output by games.json abbreviation, matching all 30 teams.

---

## MLB API STATUS "GAME OVER" NOT RECOGNISED BY GRADE_PICKS

**Date discovered:** 2026-06-07
**Relevant scripts:** `scripts/fetch_results.py`, `scripts/grade_picks.py`

The MLB Stats API sometimes returns `"Game Over"` (and `"Completed Early"`) as the
game status instead of `"Final"`. `fetch_results.py` was only mapping `"Final"` to
the `"final"` status used by `grade_picks.py`, so games ending in these alternate
states were excluded from grading — their picks showed as unresolved.

**Fix:** Added `"Game Over"` and `"Completed Early"` to the final-status mapping:
```python
if status_raw in ("Final", "Game Over", "Completed Early"):
    status = "final"
```

---

## GRADE_PICKS BEST BET REGEX TOO NARROW FOR (GAME: CLE @ TEX) FORMAT

**Date discovered:** 2026-06-07
**Relevant scripts:** `scripts/grade_picks.py`

The SLATE SUMMARY BEST BET line uses the format `TEAM ML (GAME: CLE @ TEX) — N units`.
The original regex `\(([A-Z]{1,5}\s*@\s*[A-Z]{1,5})\)` only matched a bare `(CLE @ TEX)`
and failed to match the `(GAME: CLE @ TEX)` form with a prefix, leaving best bets
as "unresolved" even when the game was graded.

**Fix:** Changed to `\([^)]*\b([A-Z]{1,5})\s*@\s*([A-Z]{1,5})\b[^)]*\)` which
tolerates any prefix inside the parentheses and extracts only the two team codes.

---

## LOG_ALL_PICKS SILENTLY SKIPS MODELS WHOSE JSON EXISTS BUT HAS EMPTY PICKS

**Date discovered:** 2026-06-07
**Relevant scripts:** `scripts/log_all_picks.py`

`log_all_picks.py` checked `if json_path.exists()` to decide whether to skip re-parsing.
If a previous run produced a valid JSON file with an empty `picks` array (e.g. because
the raw file was in free-form markdown instead of the structured format), the script
would skip it silently on subsequent runs, leaving the model stuck at 0 bets forever.

**Fix:** Added a content check — reads the JSON and inspects `len(doc.get("picks", []))`.
Only skips if the file exists AND has at least one pick. If the file exists but is empty,
logs `[reparse]` and re-parses from the raw file.

---

## MODELS IGNORING OUTPUT FORMAT — FREE-FORM MARKDOWN BREAKS PARSER

**Date discovered:** 2026-06-07
**Affected models:** chatgpt5.5, gemini (June 7 slate)
**Relevant scripts:** `scripts/log_picks.py`, `scripts/build_prompt.py`

Some models responded with free-form markdown analysis (headers, tables, prose summaries)
instead of the structured `## GAME:` block format. `log_picks.py` found zero parseable
blocks, recording 0 picks. Raw files had to be manually reformatted.

**Root cause:** The output format instructions were not stern enough. Models treated the
format as a suggestion.

**Fix:** Strengthened the output format block in `build_prompt.py` with an explicit warning:
> "Your response will be parsed by an automated script. Any deviation from this format —
> including prose introductions, analysis summaries, markdown tables, or section headings
> not shown below — will cause your picks to be lost entirely and your record will show
> 0 bets for the day."

Also added terminal barrier at bottom of the format block:
> "START YOUR RESPONSE WITH ## GAME: — NOTHING BEFORE IT."

**Ongoing risk:** Models with web browsing may still add introductory prose. If this
recurs, consider adding a pre-prompt line: "Your FIRST token must be `##`."

---

## SEASON AGGREGATE vs ESTIMATED — FANGRAPHS PLATOON DATA IS NOT A PROXY

**Date discovered:** 2026-06-08
**Relevant scripts:** `scripts/build_prompt.py`, `scripts/load_static_data.py`

Platoon wRC+ figures from FanGraphs splits files were labeled `ESTIMATED` in the prompt,
but this was misleading — the data is real, full-season team aggregate stats, not a
calculated proxy. `ESTIMATED` implied low trust and caused at least one model
(GPT-5.2-high) to apply its LOW-TRUST rule and refuse to use the data at all.

**Fix:** Changed `status_tag = "ESTIMATED"` to `status_tag = "SEASON AGGREGATE"` in
`build_prompt.py:_fmt_platoon_matchup()`. Updated the ESTIMATED DATA RULE block to
explain both labels: CONFIRMED (from actual lineup) and SEASON AGGREGATE (FanGraphs
team-level). SEASON AGGREGATE is valid supporting context but not the primary bet
justification (lineup-specific splits from a confirmed batting order are stronger).

---

## L10 RS/G ADDED TO TEAM FORM

**Date added:** 2026-06-08
**Relevant scripts:** `scripts/fetch_teamstats.py`, `scripts/build_prompt.py`

Season RS/G is a lagging indicator — a team that was scoring 5.2 RS/G in April but
4.0 in June looks the same. L10 RS/G (runs scored per game in last 10 games) captures
current offensive form and is a required input for accurate totals estimation.

**Implementation:** Added `fetch_l10_rsg(team_id, season, before_date)` to
`fetch_teamstats.py` — calls `/teams/{id}/stats?stats=gameLog&group=hitting`,
filters to games before the slate date, takes last 10, returns mean runs.
Called in Step 2b of the main function for each unique team in the slate (at most
~20 API calls per run). Stored as `l10_rs_per_game` in the team context block.
`build_prompt.py:fmt_team_form()` appends `, L10 RS/G {n}` when the field is present.

---

## WINDOWS CP1252 — ALSO AFFECTS NEW SCRIPTS (ADDENDUM TO EARLIER ENTRY)

**Date discovered:** 2026-06-06
**Addendum to:** WINDOWS CONSOLE ENCODING entry above

The same cp1252 crash applies to any new script that prints Unicode characters.
`load_static_data.py` self-test originally used box-drawing characters (`-`, `->` style
arrows) — fixed to plain ASCII before the first run.

For `build_prompt.py` test output (which displays the prompt block in the terminal),
the fix is `re.sub(r'[^\x00-\x7F]', '?', block)` to strip non-ASCII before printing.
This strips characters that are fine in the file (UTF-8 encoded) but crash the console.

Rule: any `print()` statement in any script must use ASCII-only characters. Unicode in
file output (always opened as `encoding='utf-8'`) is fine and expected.

---

## STAKING SYSTEM SIMPLIFIED -- 5-UNIT TIER REMOVED

**Date:** 2026-06-09
**Relevant scripts:** `scripts/build_prompt.py`, `docs/MODEL_INSTRUCTIONS.md`

The original 5-tier system (5/3/1/LEAN/PASS) created an inflation target.
Models chased 5-unit designations using narrative richness and inflated edge
estimates. The tier also created ambiguity in the best bet rule -- a 3-unit
best bet felt like a weak day even when 3 units was the correct call.

**New system:** 3 units is the ceiling.

Gap mapping:
  <4 points  = LEAN or PASS -- never a bet
  4-7 points = 1 unit maximum
  7+ points, clean data = 3 units maximum

**Best bet rule tightened:** best bet must be a 3-unit play. If no game
clears 3 units, no best bet is published. A skip on best bet is logged
publicly with reason. Some days will have picks but no best bet -- that
is correct and expected.

**Impact:** simplifies calibration tracking (two bet tiers only), removes
the inflation target, makes skip days on best bet a natural and credible
outcome rather than a failure state.

---

## VOLUME BIAS -- MODELS OVER-BET SLATES BY DEFAULT

**Date discovered:** 2026-06-09
**Relevant scripts:** `scripts/build_prompt.py`

All models averaged 4-6 picks on 15-game slates during the first 7 days of
validation. A professional bettor passes on 85-90% of available games.

Root cause: the prompt opened with "You are an expert MLB betting analyst."
An analyst proves value through volume and insight. A professional bettor
proves value through ROI. The identity framing set the wrong goal.

Secondary cause: the output format requires a block per game, creating
implicit pressure to find something on each game reviewed.

**Fixes applied (all in build_prompt.py Part 2):**

1. Identity reframe -- replaced analyst opening with PROFESSIONAL BETTOR
   block that explicitly establishes passing as the expected default and
   defines success as unit-weighted ROI, not pick volume.

2. PROFESSIONAL STANDARD block -- frames 85-90% pass rate as the baseline,
   flags multiple 3-unit plays as a calibration error.

3. MINIMUM EDGE GATE -- 4-point probability gap is the hard floor for any
   bet. Cannot be overridden by narrative, price, or line movement.

4. SLATE DISCIPLINE CHECK -- hard bet ceilings per slate size (1/2/3 bets
   for small/medium/large slates) with a three-step self-audit filter.

5. EDGE field changed to numeric percentage points -- makes gap-to-units
   accountability visible in the log and enables calibration tracking.

---

## TEAM BARREL% -- STATIC FILE SOLUTION

**Date:** 2026-06-11

Team offensive Barrel% and HardHit% loaded from:
    data/mlb/team_barrels.txt
Manual export from FanGraphs team batting exit velocity leaderboard.
Filter to current season only before exporting.
Update weekly or when roster changes significantly.
Loader: load_static_data.load_team_barrels()
Injected into prompt by build_prompt.py per game block (team form line).
Remap: FanGraphs team abbreviations converted via _FG_TO_GAMES
    (e.g. WSN->WAS, KCR->KC, SDP->SD, SFG->SF, TBR->TB, ARI->AZ).

FanGraphs pybaseball API blocked by Cloudflare Turnstile (403).
fetch_pitcher_advanced.fetch_team_barrel_pct() is now a stub that
returns {} -- team barrel% comes exclusively from the static file.

---

## REASONING SEQUENCING FAILURE (first documented: 2026-06-10, Sonnet)

Model ran slate discipline check mid-response instead of completing
it before writing the first ## GAME: block. Result: duplicate game
blocks, picks assigned then retracted, prose between game blocks.
Fix: model-specific instruction to pre-compute all cross-game
reasoning before beginning output. Monitor other models for same
pattern.

---

## PICK CONCENTRATION MONITORING

**Date:** 2026-06-08 (baseline established)

pick_concentration.py tracks daily herding metrics to docs/concentration_log.csv.
Baseline measurement on June 8 slate: 82.1% same-side pick concentration across
models. This was the motivating data point for removing prescriptive method mandates
from the shared prompt layer (build_prompt.py).

Goal: drive concentration below 70% by allowing models to find edge independently.
Monitor daily against 82.1% baseline. A rising trend signals re-homogenisation of
reasoning -- check recent shared prompt changes.

Metric: % of non-Pass picks landing on the same side of the same game across all models.

---

## GROK 4.3 EXPERT EVALUATION

**Date:** 2026-06-08 (informal test)

Grok 4.3 Expert tested informally on June 8 slate.
Improvements observed: better EDGE self-labeling, improved pass discipline.
Gap identified: mandatory probability gap documentation (estimated fair ML ->
implied probability -> gap in percentage points) was absent on a high-unit play.

Rule: any 3+ unit play without documented gap calculation must be mechanically
downgraded to 1 unit. This is a mandatory output field, not optional documentation.

Decision pending: switch to 4.3 Expert as clean entry point, or continue
parallel informal comparison for 1-2 more slates before committing.

---

## GEMINI CONTEXT TRUNCATION

**Date:** First documented 2026-06-10 (approximate)

Gemini truncates output after approximately 8 games on large slates.
Likely cause: prompt size (~56,000 characters) is approaching context limits
when combined with a full game-by-game reasoning pass.
Status: open. Mitigations under consideration -- prompt compression,
game-block batching, or model upgrade.
Do not mistake truncation for a PASS decision on uncovered games.

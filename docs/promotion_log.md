# METHOD PROMOTION LOG

Audit trail for every candidate method change that was reviewed for promotion
into a model's `docs/methods/method_{model}_v{N}.md`. This is the shared,
cross-model record — the per-model "building" notes live in
`picks/candidates/candidate_changes_{model}.md`.

**Rule:** No entry is added here until Mark (owner) has made a decision.
Models author their own methods; the owner is the promotion gate. Fixed
competition rules (edge gate, unit map, slate ceiling, anti-hindsight) are
never promotable — those belong to Layer B, not model methods.

Active roster only (kimi, chatgpt, opus, gemini, deepseek, qwen, sonnet, grok).
Deprecated V1 legacy (fable, manus, chatgpt5.5, gpt-5.2-high) excluded.

---

## How to read an entry

| Field | Meaning |
|---|---|
| Date | Date of the promotion DECISION |
| Model | Whose method is affected |
| Decision | PROMOTED / DECLINED / DEFERRED |
| Change | One-line summary of the candidate |
| Method version | New version created (if PROMOTED), e.g. `method_opus_v3.md` |
| Evidence | Recurrence count / cross-model convergence / CLV that justified it |
| Owner reasoning | Mark's agree/disagree note |

---

## Decisions

<!-- Append newest entries at the top. Template:

### YYYY-MM-DD — <model> — PROMOTED / DECLINED / DEFERRED
- **Change:** <one line>
- **Method version:** method_<model>_v<N>.md  (or "n/a")
- **Evidence:** <recurrence / convergence / CLV trail>
- **Owner reasoning:** <Mark's note>

-->

> **Backfill note (2026-06-20):** Entries below were reconstructed from the V2
> timeline (start 2026-06-12) by cross-referencing `docs/LEARNINGS.md` and
> `picks/candidates/`. Conditioning rules drawn from LEARNINGS that govern how
> these candidates are judged:
> - **Promotion is evidence-gated, never confidence-gated** (2026-06-15: a HIGH-confidence Gemini claim was entirely wrong).
> - **One slate is never enough** — require recurrence across 2+ slates OR cross-model convergence OR CLV confirmation.
> - **Fixed competition rules are not promotable** (edge gate, unit map, slate ceiling, anti-hindsight) — those are Layer B, not model methods.
> - **Each model promotes its own version** of a shared theme; a model that did not derive the fix itself is NOT promoted by proxy (e.g. Grok excluded from the L14 promotion).

---

### 2026-06-15 — deepseek / sonnet / qwen — PROMOTED  ✅ IMPLEMENTED
- **Change:** L14 small-sample over-weighting discount (down-weight last-14-day stats when L14 IP is low).
- **Method version:** method_deepseek_v2.md (2:1 AGG/L14 floor, 50% max shift); method_sonnet_v2.md (graduated IP table); method_qwen_v2.md (L14 IP<12 blend back to season SIERA/xFIP).
- **Evidence:** Flaw independently identified by all three models across two slates (Jun 12–13) with pre-game evidence; logged as candidate Jun 14; promoted Jun 15. Cross-model convergence + recurrence both satisfied. (LEARNINGS 2026-06-14, 2026-06-15; commit ccac664.)
- **Owner reasoning:** Approved — first promotion under the V2 loop. v1 files retained as history. `load_model_instruction()` auto-selects highest version. Grok deliberately excluded: it demonstrated the flaw but never proposed the fix in its own post-mortems — must self-derive first.

### 2026-06-15 — qwen — DECLINED  ⛔ REJECTED (do not resurface)
- **Change:** Replace the fixed 3-bet slate ceiling with a max-daily-risk limit.
- **Method version:** n/a
- **Evidence:** Single slate (Jun 14). Logged in candidate_changes_qwen.md as REJECTED.
- **Owner reasoning:** Two disqualifiers — (a) the slate ceiling is a FIXED competition rule models cannot rewrite (would break leaderboard fairness); (b) cited evidence relied on KC's '19.25 bullpen ERA', a corrupted aggregate since removed from the prompt. Invalid evidence base.

---

## Building — awaiting recurrence / CLV before a promotion decision

These are tracked in `picks/candidates/` as CANDIDATE (building). No owner
decision yet — listed here for visibility only.

| Logged | Model(s) | Candidate | Status | Waiting on |
|---|---|---|---|---|
| 2026-06-14 | deepseek, sonnet, opus | Regress extreme results-stats (ERA, bullpen ERA) toward xFIP/FIP peripherals | 🟡 PENDING | One more slate of recurrence OR CLV confirmation. Cross-model convergence (3 models) already present. |
| 2026-06-14 | kimi | Bullpen-quantification: +0.0–+1.5pt adjustment on rest differential | 🟡 PENDING — **2 slates** (06-14, 06-19) | Recurrence now satisfied. 06-19 S4: +0.25-run total adjustment when both bullpens taxed (TOR@CHC, BOS@SEA), self-rated LOW pending backtest. Cross-model convergence still absent (kimi-only); needs either a second model or CLV before a decision. |
| 2026-06-18 | deepseek, sonnet | Team-level wRC+ aggregates mislead on platoon edges (DeepSeek: discount unconfirmed platoon edges; Sonnet: stress-test extreme aggregates) | 🟡 PENDING — logged in candidate files (deepseek + sonnet 06-18; recurrence notes 06-20); root theme recurs 06-18→06-19 with broad convergence | Root theme clears recurrence + convergence, but on a thread-level read it is **not one promotable edit** — it splits into two: **(A) confirmation-gating** — wait for / recalc on confirmed lineups, discount unconfirmed platoon edges (deepseek, chatgpt, qwen S4 + gemini's MISSED-LINEUP grade; the bulk of the 06-19 convergence). **BLOCKED:** evidence rests on post-lock confirmed-lineup data → `outcome-biased` per the evidence-validity rule (see deepseek 06-20 recurrence note), AND depends on the confirmed-lineup feature (deferred). **(B) distribution / PA-robustness** — judge whether an extreme aggregate is broad-based or outlier-driven before staking (sonnet 06-18; opus 06-19 expected-lineup-weighting loosely adjacent). This is the pre-game-supportable thread, now directly enabled by the **2026-06-21 PLATOON data fix** (per-bat wRC+/PA + <25 PA outlier guard in build_prompt.py). **Decision deferred, do NOT bundle into one entry:** promote (B) only after a clean same-thread recurrence **under the new data format**; (A) stays blocked pending confirmed lineups. The data fix addressed the *symptom* both threads share — it is not itself the method promotion. |
| 2026-06-19 | grok | L14 small-sample flag → require a 7-pt estimated edge (not 4 pt) before any 1u stake | 🟡 PENDING — single slate, MEDIUM | Needs recurrence. **Owner-relevant flag:** this is Grok self-deriving a small-sample fix in its own post-mortem for the first time — the exact behavior it was excluded from the 06-15 L14 promotion for failing to do (see Decisions, 2026-06-15). The exclusion condition may now be clearing; audit trail captures the start of that watch. Evidence: every bet (CIN, STL, COL) carried an L14 flag, yet the current rule still permitted 1u sizing. |
| 2026-06-19 | sonnet | Star-player availability flag — if a key bat cited by name in the pick reasoning (e.g. Ohtani 172) is absent from the confirmed lineup, auto 50% stake cut (1u→0.5u) or recalc the gap with that player removed | 🟡 PENDING — single slate | Needs recurrence. Mechanically distinct from (but related to) the 06-18 platoon-aggregate candidate: that one is about aggregate dilution from bench platoon splits; this is a single-star-absence trigger. Evidence: Ohtani out of both NYY and LAD confirmed lineups affected the NYY ML and LAD RL stakes. Self-rated confidence not captured (Sonnet's S4 response truncated mid-sentence). |

## Process flags observed in V2 post-mortems

- **2026-06-19 — chatgpt / kimi / qwen:** all three graded the MIL @ ATL loss "CORRECT PROCESS / BAD VARIANCE / would-bet-again YES" when the lineup dilution was pre-game-knowable from the confirmed card (MIL's wRC+ vs LHP fell from the modelled 136 to 108.9 via Frelick 14 / Hamilton 76). That is an anti-hindsight breach — a loss is bad variance only if no pre-game data point justified avoiding it. Qwen self-contradicted: S2 said "bad variance / bet again" while its own confirmed-data block on the same game said "bet→lower stake." Contrast: deepseek graded it INCORRECT TEAM STRENGTH and gemini MISSED LINEUP — both correct process errors. This is the **second straight slate with a qwen anti-hindsight flag** (see 06-18 below). Watch for recurrence.
- **2026-06-18 — qwen:** S4 cited a game OUTCOME ("MIN won 9-3") as evidence for upweighting K-BB%. Outcome-biased reasoning (anti-hindsight). Self-flagged LOW confidence. Watch for recurrence.
- **2026-06-16 — grok:** Post-mortem incuriosity confirmed dispositional, not a config artifact (high-reasoning test regressed). S3/S4 chronically NONE.
- **2026-06-15 — gemini:** HIGH-confidence post-mortem claim (wrong-team pitchers) was entirely wrong — reinforces evidence-gated promotion.

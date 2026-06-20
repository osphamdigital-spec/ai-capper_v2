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
| 2026-06-14 | kimi | Bullpen-quantification: +0.0–+1.5pt adjustment on rest differential | 🟡 PENDING | Single slate only — needs recurrence. |
| 2026-06-18 | deepseek, sonnet | Team-level wRC+ aggregates mislead on platoon edges — discount/distribution-check before staking (DeepSeek: discount unconfirmed platoon edges; Sonnet: stress-test extreme aggregates) | 🟡 PENDING — **not yet logged to candidate files** | Needs logging to `candidate_changes_*.md`, then recurrence. Cross-model convergence (2 models) present. |

## Process flags observed in V2 post-mortems

- **2026-06-18 — qwen:** S4 cited a game OUTCOME ("MIN won 9-3") as evidence for upweighting K-BB%. Outcome-biased reasoning (anti-hindsight). Self-flagged LOW confidence. Watch for recurrence.
- **2026-06-16 — grok:** Post-mortem incuriosity confirmed dispositional, not a config artifact (high-reasoning test regressed). S3/S4 chronically NONE.
- **2026-06-15 — gemini:** HIGH-confidence post-mortem claim (wrong-team pitchers) was entirely wrong — reinforces evidence-gated promotion.

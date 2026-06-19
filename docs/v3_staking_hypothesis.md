# v3 STAKING HYPOTHESIS — the eight self-authored staking policies

**Generated:** 2026-06-19, at the v2→v3 transition (before any v3 results).

This table is the v3 experiment's **opening hypothesis**. With the house edge
gate / slate ceiling / unit map removed, each model authored its own. The spread
below — selective vs loose, concentrated vs high-volume — is what the bankroll
will test. Read it now; revisit it after ~20+ settled bets per model to see which
philosophy the bankroll rewarded.

All eight rules are self-authored in `docs/methods/method_{model}_v{N}.md` (sides)
and `method_{model}_totals_v2.md` (totals).

## The table

| Model | Sides edge gate | Totals edge gate | Slate ceiling | 3u trigger (sides) | Cross-market ceiling |
|---|---|---|---|---|---|
| **sonnet** (v3) | **5.0 pts** | 0.6 runs | 3 (2 on ≤4g, 1 on ≤2g) | 7.0 pts + 5 integrity/conviction conds | unified |
| **chatgpt** (v2) | **3.5 pts** | 0.7 runs | 3 | 7.0 pts + clean components | unified (combined) |
| **opus** (v2) | 4.0 pts | 0.5 runs | 3 | 7.0 pts + clean data | unified (combined) |
| **gemini** (v2) | **5.0 pts** | 0.5 runs | 4 | **8.0 pts** | unified (combined) |
| **deepseek** (v3) | 4.0 pts | 0.5 runs | 3, **max 2×3u** | 7.0 pts + clean | unified (reconciled) |
| **qwen** (v3) | 4.0 pts | 0.5 runs | **5** | **6.5 pts** | unified (combined) |
| **kimi** (v2) | **3.5 pts** | **0.35 runs** | 1/2/3 by slate size | 7.0 pts, **max 1×3u/slate** | unified |
| **grok** (v2) | 4.0 pts | 0.75 runs | 3 | 7.0 pts + clean | unified (combined) |

## Reading the spread

**Edge gate (selectivity):** ranges 3.5 → 5.0 pts. Tightest: sonnet, gemini (5.0).
Loosest: chatgpt, kimi (3.5). Nobody removed the gate. Several explicitly *raised*
it above the old house 4.0 (sonnet, gemini) given freedom — using freedom to be
more disciplined, not less.

**Slate ceiling (volume):** mostly 3 combined. Outliers: qwen (5), gemini (4),
kimi (slate-size scaled 1/2/3). Two models added sub-limits on 3u concentration:
deepseek (max two 3u/slate), kimi (max one 3u/slate).

**3u trigger (aggression on size):** mostly 7.0 pts (kept from v2). Outliers:
qwen lowered to **6.5** (easiest 3u), gemini raised to **8.0** (hardest 3u).

**Most aggressive overall: qwen** — highest ceiling (5) AND lowest 3u trigger
(6.5). This is the model to watch on bankroll drawdown; the combination means more
bets and easier max-stakes. Allowed — it is a finding, not an error.

**Most conservative overall: gemini** (gate 5.0, 3u 8.0) and **sonnet** (gate 5.0,
graduated short-slate ceiling).

## The signal that v3 is working

**All eight set evidence-gated self-revision triggers** — without being told to:
- sonnet: revisit gate→4.5 only after 30+ bets of +CLV in the 5–6 pt band
- gemini: audit if CLV negative over 30 bets; tighten 3u→9.0 if 3u ROI<0
- kimi: raise 3u→8.0 if 3u ROI lags after 50+ bets
- deepseek: no rule changes until 100 settled bets
- opus: CLV-first; "draw no conclusion" until report stops flagging small sample
- chatgpt: audit 1u-vs-3u CLV; "draw no conclusion" on tiny samples
- qwen: monitor 1u/3u ROI & CLV splits to validate thresholds
- grok: CLV evaluation gates any change

Showing each model the account-block format *before* it authored (the forward
note) directly produced this: models wrote rules anticipating their own
evidence-based evolution, anchored to metrics they know they'll receive. That is
v3 as designed — not just self-authored rules, but rules that plan their own
revision and refuse to overfit a handful of bets.

All eight **revised rather than tore down** — every model kept its v2 handicapping
core (projection framework, distrust lists) and changed only the staking layer.

## Resolved — DeepSeek cross-market ceiling conflict

DeepSeek's first re-author produced disagreeing docs (sides: combined; totals:
separate) because each call saw only its own file. Fixed by re-authoring
`method_deepseek_totals_v3.md` with its sides doc embedded as authoritative
context — DeepSeek reconciled it itself: the totals doc now reads "my overall
sides method imposes a combined slate ceiling of maximum 3 bets… there is no
separate totals-only bucket… at most two 3-unit bets across both markets." Fully
consistent with its sides v3. (totals_v2 retained as history; the loader uses the
highest version.) The totals re-author template now always embeds the sides doc,
so this class of conflict cannot recur.

## Cosmetic note (not corrected)

Several models self-stamped wrong datelines in their docs (qwen "2026-07-01",
deepseek "June 2025", sonnet "2026-06-21"; today is 2026-06-19). Harmless in a
dateline, but the same class of "asserting something not grounded in given data" —
the promotion gate scrutinizes this everywhere it would actually matter.

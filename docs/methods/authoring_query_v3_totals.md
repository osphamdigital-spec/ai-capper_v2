# TOTALS METHOD RE-AUTHORING — v3 (you now own your totals staking)

You are an independent professional sports bettor in a long-running MLB
forecasting experiment. You already have a working **totals (Over/Under) method**
(yours is reproduced in full at the bottom of this message). The rules of the
game have changed, and you are being asked to **revise your totals method
document** to fit the new rules.

## WHAT CHANGED

Previously the house fixed a TOTALS GATE — a run-gap edge gate and a 1u/3u map
(e.g. <0.5 runs → no bet, 1.0–1.5 → 1u, 1.5+ → 3u) — identical for everyone, and
a house slate ceiling (1/2/3 bets by slate size).

**Those house rules are now REMOVED.** On totals you author your own:

1. **Your totals edge gate** — the minimum run gap between your projected total
   and the posted line below which you will not bet.
2. **Your 1u-vs-3u threshold on totals** — what run gap (and any other
   conditions) makes a totals bet a 3-unit play rather than 1 unit.
3. **How totals interact with your slate ceiling** — your overall slate ceiling
   is defined in your main (sides) method document. State here whether a total
   and a side on the same game both count toward that one ceiling, or whether you
   run a separate ceiling for totals. **Do not reference the old house slate
   ceiling (1/2/3 by slate size) — it no longer exists.**

## WHAT IS STILL FIXED (do not redefine)

- **Unit denominations:** a totals bet is staked at **either 1 unit or 3 units**.
  LEAN = zero stake. "No bet" = no action. The labels stay 1u/3u.
- **Data integrity:** TBD starter → PASS; stale/suspect total price → that market
  is absent; postponed → PASS.
- The machine-parsed output format (TOTAL / TOTAL PRICE / TOTAL UNITS / TOTAL
  EDGE) is unchanged.

## A REAL BANKROLL — AND YOU SEE YOUR OWN HISTORY

v3 runs on a real per-model bankroll (start $10,000; 1 unit = $100 base, to-win
convention). Before each slate you receive a block of YOUR OWN account history —
raw numbers, no verdicts — including a Totals (O/U) line in the by-type
breakdown (e.g. `Totals (O/U): 1 / 0-1 / −$40`). It carries a small-sample
warning; conclusions from a few bets are unreliable, and drawing none is valid.
You see only your own history, never another competitor's. Author your totals
staking knowing this is the feedback you will receive.

## YOUR TASK

Rewrite your totals method document so it **explicitly states**, in a clearly
labeled staking section:

- your totals edge gate (in runs),
- your 1u-vs-3u threshold on totals,
- how totals count against your slate ceiling.

Keep everything else you still believe in — your run-estimation framework, your
wind/park/weather adjustments, your pass triggers. This is a revision, not a
teardown. **Remove any reference to the old house slate ceiling or house run-gap
gate.** State the reasoning behind your selectivity, not just the numbers.

Output ONLY the revised totals method document text. No preamble, no picks, no
## GAME: blocks.

---

## YOUR SIDES METHOD (already finalized — DO NOT contradict it)

This is your main (sides) method document. Its slate-ceiling decision is
AUTHORITATIVE. Your totals ceiling statement must be **consistent** with it: if
your sides doc says the ceiling is combined across both markets, your totals doc
must agree that totals count toward that same combined limit; if it defines a
separate totals allowance, match that. Do not state a conflicting scheme.

{SIDES_METHOD}

---

## YOUR CURRENT TOTALS METHOD (revise this)

{CURRENT_METHOD}

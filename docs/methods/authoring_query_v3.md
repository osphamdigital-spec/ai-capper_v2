# METHOD RE-AUTHORING — v3 (you now own your staking discipline)

You are an independent professional sports bettor in a long-running MLB
forecasting experiment. You already have a working handicapping method (yours is
reproduced in full at the bottom of this message). The **rules of the game have
changed**, and you are being asked to **revise your method document** to fit the
new rules.

## WHAT CHANGED

In the previous version (v2), three staking rules were FIXED by the house and
identical for every competitor:

- a 4 percentage-point minimum **edge gate** to bet,
- a **slate ceiling** of 1/2/3 bets by slate size,
- a fixed **unit map** (gap 4–7 pts → 1u, gap 7+ → 3u).

**These house rules are now REMOVED.** You author your own. You decide:

1. **Your edge gate** — the minimum gap (in percentage points for sides, in runs
   for totals) below which you will not bet.
2. **Your slate ceiling** — the maximum number of bets you will make on a slate,
   or explicitly "no ceiling." **State explicitly whether this ceiling spans BOTH
   markets** — i.e. whether a total (Over/Under) and a side (ML/RL) both count
   toward the same limit, or whether you keep separate ceilings for sides and
   totals. (There is no house rule on this anymore; it is your call.)
3. **Your 1u-vs-3u threshold** — the rule that decides whether a qualifying bet
   is staked 1 unit or 3 units.

## WHAT IS STILL FIXED (do not redefine these)

- **Unit denominations:** every bet is staked at **either 1 unit or 3 units** —
  those are the only two stake sizes. LEAN = zero stake. PASS = no action. You
  choose WHEN to use 1u vs 3u, but the labels stay 1u/3u (the leaderboard
  arithmetic depends on it).
- **Best bet** = your single highest-conviction 3-unit play, or none.
- **Data integrity:** TBD starter → PASS; stale/suspect price → that market is
  absent; postponed → PASS. Non-negotiable.
- The machine-parsed output format is unchanged.

## NEW: A REAL BANKROLL, AND YOU SEE YOUR OWN HISTORY

v3 runs on a real per-model bankroll. You start at **$10,000**. 1 unit = $100
base, settled on the "to-win" convention (an underdog at +110 risks $100 to win
$110; a favorite at −130 risks $130 to win $100; 3u triples both). Your balance
moves only on settled bets.

Before each slate you will receive a block of **your own account history** —
raw numbers, no verdicts — that looks like this:

```
═══════════════════════════════════════════════════════
YOUR ACCOUNT — v3 bankroll (your own history only)
═══════════════════════════════════════════════════════
SMALL-SAMPLE WARNING: 12 settled bets is far too few to draw reliable
conclusions about your method. Variance dominates at this size...

Balance: $10,300.00   (start $10,000.00 — net +$300.00)
Record:  7-5-0 (W-L-P) over 12 settled bets
ROI:     +6.1% on $4,910 risked
CLV:     +18.4c average over 12 bets

By bet type   (bets / W-L / net $)  — three overlapping views of the SAME bets
  Favorites (−odds):  8 / 5-3 / +$120
  Underdogs (+odds):  4 / 2-2 / +$180
  1-unit bets:        9 / 5-4 / −$60
  3-unit bets:        3 / 2-1 / +$360
  Moneyline:         10 / 6-4 / +$240
  Run line:           1 / 1-0 / +$100
  Totals (O/U):       1 / 0-1 / −$40

Leaderboard: you are rank 4 of 8. Leader has $10,820.00. Gap: −$520.00.
```

You see ONLY your own history — never another competitor's picks or method.
The sample will be near-empty for the first several slates; conclusions from a
handful of bets are unreliable, and "draw no conclusion" is always valid.

Author your staking rules **knowing this is the feedback you will receive.** A
threshold you can actually evaluate against this report is better than one you
cannot.

## YOUR TASK

Rewrite your method document so that it **explicitly states**, in their own
clearly labeled section:

- your edge gate (sides, in pts; totals, in runs),
- your slate ceiling (a number, or "no ceiling," with your reasoning),
- your 1u-vs-3u threshold.

Keep everything else about your method that you still believe in — this is a
revision, not a teardown. State the reasoning behind your selectivity vs
aggression, not just the numbers, so it can be evaluated. Your objective remains
long-term, risk-adjusted bankroll growth measured against closing line value.

Your totals (Over/Under) staking remains governed by your separate totals method
document; you may restate your totals edge gate here for completeness if you wish.

Output ONLY the revised method document text. No preamble, no picks, no
## GAME: blocks.

---

## YOUR CURRENT METHOD (revise this)

{CURRENT_METHOD}

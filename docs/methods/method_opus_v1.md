# MLB Handicapping Method — Personal System

## Core Philosophy
I price each game from component fundamentals, then compare my fair line to the median market. The market is sharp; my edge comes from spots where recent surface stats (ERA, W-L, L10) distort the price relative to predictive metrics. I bet projection vs. perception gaps, not winners.

## Pitcher Valuation (my largest input)
I anchor starters on **xFIP, SIERA, and K-BB%** from the AGG (full-sample) line, NOT seasonal ERA or FIP. I treat the AGG row as my true-talent baseline. I distrust:
- Sub-40 IP samples and any [small sample] flag — these never anchor a play and never earn 3 units.
- L14/L3 splits as predictive — I read them only for injury/velocity red flags or workload, not for ERA narratives. A 0.55 L3 ERA on inflated BABIP luck is a fade signal, not a buy signal.
- Wide ERA-vs-xERA gaps: when ERA is far below xERA/xFIP, the market may be overpricing a regression candidate (e.g., Phillips 2.08 ERA / 4.27 SIERA — I'd lean against, not with, the hype side).

Stf+ near/below 90 with low K-BB% caps my upside on that arm.

## Bullpen
I weight **fresh high-leverage arm count** and recent pitch-count taxation over season bullpen ERA. "0 of X fresh" in a likely-close game shifts 3-5% toward the opponent. I flag closers with bloated ERAs (Fairbanks 7.00, Vest 6.53) only if the game projects tight; in blowout-leaning spots bullpen quality matters less.

## Offense & Context
I use **vs-RHP/LHP wRC+ (AGG)** as the lineup baseline, adjusting for the actual starter's hand. Lineups unconfirmed = I shave confidence and never go 3 units on a thin offensive read. Park factors matter for totals only; I largely avoid Coors (variance too high) and any total with stale-flagged TT prices.

## Converting to Probability
I build expected runs for each side from starter true-talent run rate + bullpen + offense vs. hand, convert run differential to win probability (~0.10 WP per 0.5 projected run margin near pick'em), then compare to no-vig implied probability (I strip juice from the median two-way line). Gap ≥4 pts = bet; ≥7 with clean data = 3 units.

## Automatic Passes
- Either starter TBD (Game 8).
- [small sample] starter for any 3-unit consideration.
- Stale/suspect price on the side I want — market treated as absent.
- Edge built primarily on L3/L10 momentum.
- Coors totals; any game where my number sits within 3 pts of market.

I respect slate ceilings strictly and pass freely. Most games rate PASS. My favorite spots: solid xFIP/K-BB% starter being underpriced because seasonal ERA looks ugly, facing a regression-candidate ERA darling.
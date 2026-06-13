**Method: Run-Prevention Hierarchy**

I bet on starting pitching and bullpen state because run suppression is lower-variance than run production. My edge comes from pricing pitcher skill more accurately than the market, using predictive metrics over results-oriented noise.

**What I weigh (in order):**
1. **Starting-pitcher skill gap.** SIERA and xFIP are the anchors; I ignore ERA. I compare the away starter’s AGG SIERA/xFIP to the home starter’s, then layer in L14 trends only to spot degradation, not improvement. K-BB% confirms strike-zone dominance.
2. **Bullpen fatigue.** “High-leverage arms available” is critical. If the team I am fading has 0 of 3 fresh leverage arms while my side has 2+ fresh, I add a full point to my edge. I treat bullpen ERA as secondary to usage patterns.
3. **Offense platoon split.** I use only the aggregate wRC+ versus the announced starter’s hand, not individual keys. A gap of >15 wRC+ points moves my needle.
4. **Park/weather.** Park factor is a tiebreaker. Weather gaps downgrade confidence but force a pass only if rain risk is extreme or data are missing in a high-variance park.

**What I distrust:**
Team win-loss records, L10 records, run differential, and line movement without volume context. I also distrust any ERA that is more than 1.50 runs below a pitcher’s xERA/SIERA. Small-sample starters are capped at 1-unit or LEAN regardless of gap.

**Win-probability conversion:**
I begin with the market’s implied probability from the cleanest available moneyline. I then apply a probit-style adjustment:
- **Pitching gap:** ±0.5% per 0.25-run SIERA differential (typically ±2% to ±4%).
- **Bullpen stress:** ±1% if leverage-arm availability is lopsided (≥2 fresh vs. 0 fresh).
- **Offense platoon:** ±0.5% per 10-point wRC+ gap.
- **Park/weather:** ±0.5% max.
Sum these to reach my estimated win probability. I require a 4-point minimum gap over implied probability to bet.

**Pass triggers:**
Either starter TBD; stale/suspect price on my intended side; small-sample starter with no reliable AGG track; Coors Field side bets (extreme variance); gap under 4 points; or bullpen fatigue on my own side that cancels the opponent’s fatigue. I never force action. On a 1–7 game slate I cap at one bet, choosing the largest clean gap.

**Unit map:**
Gap 4.0–6.9 pts and clean data → 1 unit. Gap ≥7.0 pts, clean data, no small-sample starters, and fresh leverage arms on my side → 3 units. Everything else is LEAN or PASS.
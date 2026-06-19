<!-- v3 (2026-07-01): Transitioned to independent bankroll management. Removed house-mandated staking rules in favor of proprietary edge gates, slate ceilings, and unit sizing thresholds calibrated for long-term risk-adjusted growth and CLV maximization. Supersedes v2. -->

**MLB Handicapping Method: Underlying Run Prevention & Platoon Efficiency**

**What I Weigh**
My model prioritizes underlying run prevention and contextual offense. For starting pitchers, I heavily weight SIERA, xFIP, and K-BB%, which strip out defense and batted-ball luck. For offenses, I rely strictly on platoon-specific wRC+ (vs. RHP or LHP) rather than aggregate season stats. Contextual modifiers include park factors (specifically run and HR indices) and weather (wind direction and speed impacting fly balls). Bullpen leverage is evaluated by the availability of top-tier, non-taxed high-leverage arms for late-inning variance reduction.

**What I Distrust**
I ignore surface-level pitching metrics like ERA, W-L records, and basic FIP when they diverge from SIERA/xFIP. I completely distrust short-term team form (L10 win-loss, L10 run differential) and recent pitcher ERA (L3/L14), as they are heavily influenced by variance and opponent quality. I also disregard aggregate team wRC+ when platoon splits reveal significant disparities.

When L14 IP is below 12, I treat the L14 metrics as heavily discounted — I blend them toward the full-season SIERA/xFIP rather than letting them drive my estimate. A starter with fewer than 12 L14 innings has not faced enough batters recently for that sample to carry meaningful signal. I note the direction of the L14 data (improving or declining) but anchor my projection on the season aggregate.

**Probability Conversion**
I build a baseline win probability using a Pythagorean expectation model driven by platoon-adjusted run environments. I calculate expected runs by combining platoon wRC+ with the opponent starter's SIERA, adjusted for the specific park factor.

Each 0.50 advantage in starter SIERA translates to a ~2.5% win probability bump. I then apply a bullpen multiplier: a fully rested, high-leverage bullpen adds 1.5% to the win probability in close games, while a taxed bullpen subtracts 1.5%. The final estimated probability is compared against the market's implied probability (derived from the best available, non-suspect moneyline).

***

### STAKING & BANKROLL MANAGEMENT (v3 PROPRIETARY RULES)

With the removal of house-mandated staking limits, my bankroll management is now strictly calibrated to maximize long-term ROI while mitigating single-day variance. I will monitor my account history—specifically the ROI and CLV splits between 1-unit and 3-unit bets—to continually validate these thresholds.

**1. Edge Gate**
The minimum required edge to place a wager. Anything below this threshold is an automatic PASS.
*   **Sides (Moneyline / Run Line):** 4.0 percentage points. 
*   **Totals (Over/Under):** 0.5 runs.

**2. Slate Ceiling**
*   **Maximum Bets:** 5 bets per slate.
*   **Market Scope:** This ceiling spans **BOTH markets** (sides and totals count toward the same combined limit of 5). 
*   **Reasoning:** MLB slates frequently present numerous marginal edges. Capping my total daily exposure at 5 combined bets prevents over-leveraging the bankroll on a single day's variance and forces me to rank my plays, ensuring capital is reserved only for the absolute highest-conviction opportunities across the entire board. If I identify more than 5 qualifying bets, I will discard the lowest-expected-value plays.

**3. 1-Unit vs. 3-Unit Threshold**
Every qualifying bet is staked at either 1 unit or 3 units. There are no fractional stakes. 
*   **3-Unit Bets (High Conviction):** A bet is staked at 3 units if it meets ALL of the following criteria:
    *   Edge is **≥ 6.5 percentage points** (sides) OR **≥ 0.8 runs** (totals).
    *   The game is in a standard variance environment (not Coors Field or extreme weather anomalies).
    *   Both starters have a full recent sample size (≥ 12 L14 IP).
*   **1-Unit Bets (Standard Conviction / High Variance):** A bet is staked at 1 unit if it meets the minimum Edge Gate (≥ 4.0% / 0.5 runs) but fails to meet the strict 3-unit criteria. This includes:
    *   Standard edges between 4.0% and 6.4% (sides) or 0.5 to 0.7 runs (totals).
    *   High edges (≥ 6.5% / 0.8 runs) that are downgraded due to a small-sample starter (< 12 L14 IP) or an extreme variance environment (e.g., Coors Field). 

***

**Pass Criteria**
I automatically pass and take no action if:
1. Either starter is TBD.
2. The best market price is flagged as stale or suspect.
3. The game is postponed.
4. The calculated edge is below the minimum Edge Gate (< 4.0 percentage points for sides; < 0.5 runs for totals).
5. I have already reached my Slate Ceiling of 5 combined bets for the day, and the current play ranks lower in expected value than my existing 5 selections.
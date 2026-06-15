<!-- v2 (2026-06-15): integrated self-proposed L14 small-sample discount. Promoted after recurring across June 12-13 post-mortems with pre-game evidence. Supersedes v1 (retained as history). -->

**MLB Handicapping Method: Underlying Run Prevention & Platoon Efficiency**

**What I Weigh**
My model prioritizes underlying run prevention and contextual offense. For starting pitchers, I heavily weight SIERA, xFIP, and K-BB%, which strip out defense and batted-ball luck. For offenses, I rely strictly on platoon-specific wRC+ (vs. RHP or LHP) rather than aggregate season stats. Contextual modifiers include park factors (specifically run and HR indices) and weather (wind direction and speed impacting fly balls). Bullpen leverage is evaluated by the availability of top-tier, non-taxed high-leverage arms for late-inning variance reduction.

**What I Distrust**
I ignore surface-level pitching metrics like ERA, W-L records, and basic FIP when they diverge from SIERA/xFIP. I completely distrust short-term team form (L10 win-loss, L10 run differential) and recent pitcher ERA (L3/L14), as they are heavily influenced by variance and opponent quality. I also disregard aggregate team wRC+ when platoon splits reveal significant disparities.

When L14 IP is below 12, I treat the L14 metrics as heavily discounted — I blend them toward the full-season SIERA/xFIP rather than letting them drive my estimate. A starter with fewer than 12 L14 innings has not faced enough batters recently for that sample to carry meaningful signal. I note the direction of the L14 data (improving or declining) but anchor my projection on the season aggregate.

**Probability Conversion**
I build a baseline win probability using a Pythagorean expectation model driven by platoon-adjusted run environments. I calculate expected runs by combining platoon wRC+ with the opponent starter's SIERA, adjusted for the specific park factor.

Each 0.50 advantage in starter SIERA translates to a ~2.5% win probability bump. I then apply a bullpen multiplier: a fully rested, high-leverage bullpen adds 1.5% to the win probability in close games, while a taxed bullpen subtracts 1.5%. The final estimated probability is compared against the market's implied probability (derived from the best available, non-suspect moneyline).

**Pass Criteria**
I automatically pass if:
1. Either starter is TBD.
2. The best market price is flagged as stale or suspect.
3. The calculated edge is under 4.0 percentage points.
4. A starter is flagged [small sample] and the edge is under 6.0 points (never risking 3 units on small-sample volatility).
5. The game is in an extreme variance environment (e.g., Coors Field) unless the edge exceeds 7.0 points, as the noise overwhelms the signal.

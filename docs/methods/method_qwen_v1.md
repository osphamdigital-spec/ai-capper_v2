**MLB Handicapping Method: Underlying Run Prevention & Platoon Efficiency**

**What I Weigh**
My model prioritizes underlying run prevention and contextual offense. For starting pitchers, I heavily weight SIERA, xFIP, and K-BB%, which strip out defense and batted-ball luck. For offenses, I rely strictly on platoon-specific wRC+ (vs. RHP or LHP) rather than aggregate season stats. Contextual modifiers include park factors (specifically run and HR indices) and weather (wind direction and speed impacting fly balls). Bullpen leverage is evaluated by the availability of top-tier, non-taxed high-leverage arms for late-inning variance reduction.

**What I Distrust**
I ignore surface-level pitching metrics like ERA, W-L records, and basic FIP when they diverge from SIERA/xFIP. I completely distrust short-term team form (L10 win-loss, L10 run differential) and recent pitcher ERA (L3/L14), as they are heavily influenced by variance and opponent quality. I also disregard aggregate team wRC+ when platoon splits reveal significant disparities. 

**Probability Conversion**
I build a baseline win probability using a Pythagorean expectation model driven by platoon-adjusted run environments. I calculate expected runs by combining platoon wRC+ with the opponent starter’s SIERA, adjusted for the specific park factor. 

Each 0.50 advantage in starter SIERA translates to a ~2.5% win probability bump. I then apply a bullpen multiplier: a fully rested, high-leverage bullpen adds 1.5% to the win probability in close games, while a taxed bullpen subtracts 1.5%. The final estimated probability is compared against the market’s implied probability (derived from the best available, non-suspect moneyline). 

**Pass Criteria**
I automatically pass if:
1. Either starter is TBD.
2. The best market price is flagged as stale or suspect.
3. The calculated edge is under 4.0 percentage points.
4. A starter is flagged [small sample] and the edge is under 6.0 points (never risking 3 units on small-sample volatility).
5. The game is in an extreme variance environment (e.g., Coors Field) unless the edge exceeds 7.0 points, as the noise overwhelms the signal.

---
## CANDIDATE METHOD CHANGE — v1.1 (proposed 2026-06-14, 2-slate evidence)
PROPOSED CHANGE: Cap L14 stat influence. When estimating a starter's true-talent
level, weight full-season AGG metrics at minimum 2:1 over L14 metrics. L14 stats
may only shift the edge estimate by a maximum of 50% of the raw AGG-based value.
Exception: only override this cap when corroborating structural evidence exists
(documented velocity change, new pitch, documented injury return, or consistent
30+ day trend — not a single bad/good stretch).
EVIDENCE: Named independently by DeepSeek, Sonnet, Qwen across June 12-13 slates.
All three 0-3 DeepSeek losses, Sonnet's oversized best-bet, and Qwen's McLean
concern all traced to the same root: L14 outliers treated as signal without
full-season anchoring.
CONFIDENCE: MEDIUM (2 slates, 3 models, pre-game evidence cited)
STATUS: CANDIDATE — not yet adopted. Promote to v2 if it recurs or shows CLV
improvement over next 10+ bets for these models.
---
# TOTALS METHODOLOGY — gemini (self-authored, v1)
# Persistent Over/Under strategy. Authored 2026-06-19 via the totals
# method-authoring round. Applied to every slate alongside the ML/RL method.

# Persistent MLB Totals Forecasting Methodology

This document outlines the systematic, quantitative approach used to forecast game totals (Over/Under) using the standardized per-game data block. This methodology operates independently of moneyline or run-line strategies and runs on a disciplined, rule-based framework designed to capture closing line value (CLV).

---

## 1. Baseline Run Estimation

The foundation of the total is a raw baseline calculated by combining the offensive true talent of both teams with the expected performance of the two starting pitchers.

```
Baseline Total = Away Team Projected Runs + Home Team Projected Runs

```

### Step A: Offensive Baseline (Weight: 40%)

We establish how many runs each team is expected to score against an average major league pitching staff.

* **Season RS/G (Base - 50% of offensive weight):** Use the team's season runs scored per game as the long-term anchor. Adjust for venue splits (Away RS for the road team, Home RS for the home team).
* **Platoon Matchup wRC+ (Adjuster - 35% of offensive weight):** Modify the base using the team's `vs_RHP` or `vs_LHP` wRC+ relative to the league average of 100. For every 10 points of wRC+ above or below 100, add or subtract **0.2 runs** from the offensive baseline.
* **Recent Form & Quality of Contact (Current State - 15% of offensive weight):** Compare `L10RS` to season RS/G. Cross-reference this with `Brl%` and `HH%`. If a team's L10RS is elevated but their barrel rate is below 7.0% and hard-hit rate is under 35%, treat the recent scoring surge as sequencing luck and regress it heavily back to the season mean.

### Step B: Starting Pitching Baseline (Weight: 60%)

We calculate how many runs each starter is expected to yield per 9 innings based on their underlying metrics, prioritizing descriptive estimators over surface ERA.

* **The Anchor (70% of pitching weight):** Use **AGG SIERA** and **AGG xFIP** as the primary indicators of a pitcher's true skill level. If there is a massive gulf between a pitcher’s season ERA and their AGG metrics (e.g., Sonny Gray's 3.03 ERA vs. 4.55 xERA but 3.45 SIERA), trust the AGG SIERA and K-BB% (above 18% is elite, below 12% is dangerous for an under).
* **Recent Form (30% of pitching weight):** Check the `L14 xFIP/SIERA` and `L3` game logs. If the L14 metrics deviate by more than **0.75 runs** from the AGG baseline, adjust the pitcher’s expected run allowance by 50% of that deviation.

### Combining to a Raw Total

1. Calculate Team A Offense vs. Team B Starter: `(Team A Offensive Baseline + Team B Starter Expected RA) / 2`
2. Calculate Team B Offense vs. Team A Starter: `(Team B Offensive Baseline + Team A Starter Expected RA) / 2`
3. Sum these two values to produce the **Raw Baseline Total**.

---

## 2. Park & Environment Adjustments

Ballparks dictate structural run environments. We use the 3-year stabilized Park Factors to modify the Raw Baseline Total.

* **Runs Factor Adjustment:** The Runs factor scales the entire environment. We multiply the Raw Baseline Total directly by the Park Factor ratio.

$$\text{Adjusted Baseline} = \text{Raw Baseline} \times \left( \frac{\text{Park Factor (Runs)}}{100} \right)$$



*Example: A raw total of 8.0 at Fenway Park (Runs: 104) scales up to 8.32 runs ($8.0 \times 1.04$).*
* **HR Factor & Outfield Dimensions Check:** High walls or expansive outfields can suppress home runs while increasing doubles/triples. If a park has a low HR factor (e.g., Fenway HR: 80 due to the Green Monster) but a high Runs factor, we cap our expectation for explosive multi-run innings via the long ball, shifting our expectation toward incremental, sequential scoring. Conversely, short porches (e.g., RF 302ft) with high HR factors inflate the likelihood of sudden over-adjustments.

---

## 3. Weather Adjustments

Weather acts as a compounding multiplier on top of the stadium's base park factor. We evaluate temperature and wind dynamics using the following precise rules of thumb:

### Temperature (Thermal Lift)

The baseline for major league total settings is 72°F. Air density changes with temperature, affecting ball flight.

* **Warm Weather:** For every 10°F **above 72°F**, add **0.15 runs** to the projected total.
* **Cold Weather:** For every 10°F **below 72°F**, subtract **0.20 runs** from the projected total.

### Wind Velocity & Directional Vectors

Wind vectors must be mapped manually against the stadium's dimensions.

| Wind Velocity | Direction | Structural Impact on Total |
| --- | --- | --- |
| **10+ mph** | **Blowing Straight Out** (e.g., S/SE at Wrigley, or out toward the short porches) | Add **0.5 to 1.0 runs** depending on intensity. |
| **10+ mph** | **Blowing Straight In** (Against the hitters) | Subtract **0.6 to 1.2 runs**; deeply suppresses high fly balls. |
| **15+ mph** | **Crosswind** (Left-to-Right or Right-to-Left) | Subtract **0.3 runs**. Crosswinds create unpredictable movement on breaking pitches, increasing K% and killing the distance on deep fly balls pushing toward the lines. |

* **Domed / Roof-Closed Stadiums:** If weather metadata indicates a closed roof or a fixed dome environment, all weather variables are ignored. The total is evaluated purely at a stagnant, neutral 70°F with 0 mph wind.

---

## 4. Pitching & Bullpen Nuances

Starters rarely finish games. The final third of the game belongs to the bullpen, making relief availability a massive lever for late-game run leakage.

### Starter Longevity & Quality Metrics

* **Stuff+ (Stf+):** A starter with a Stf+ over 105 can mitigate high hard-hit environments. If a starter possesses high Stuff+ but poor recent results, expect a positive regression bounce-back (favorable for the Under).
* **K-BB%:** This is our primary operational health metric. Any starter with a K-BB% below 13% is highly susceptible to traffic on the bases via walks, raising the ceiling for high-scoring innings.

### Bullpen Fatigue and Tier Assessment

We analyze bullpen availability across Tier 1 (Closer), Tier 2 (Setup), and Tier 3 (Middle Relief) to adjust the game's final 3 innings:

```
Bullpen Penalty/Bonus = Away Bullpen Impact + Home Bullpen Impact

```

* **The Taxed Bullpen Penalty:** Look at the "Usage last 6" days. If a team's Tier 1 closer or primary Tier 2 setup man has thrown on 2 of the last 3 days, or logged a high pitch count ($>25\text{ pitches}$) within the last 48 hours, they are marked **Unavailable/Taxed**.
* **Quantifying the Leak:**
* If **Tier 1 is unavailable** and Tier 2 is thin: Add **0.4 runs** to that team’s expected Runs Allowed (RA).
* If a team has fewer than 50% of its overall bullpen arms fresh (`[T1: 0/1 | T2: 1/2]`): Add **0.6 runs** to their expected RA. Low bullpen depth means high-leverage situations will be handled by low-K%, high-ERA middle relievers.
* **Elite, Rested Bullpen Bonus:** If a top-tier bullpen is fully fresh (`all tiers available`, low recent pitch counts) and possesses sub-3.00 collective ERAs with high K% ($>28\%$), subtract **0.3 runs** from their expected RA.



---

## 5. Edge & Staking Strategy

A calculated projection is meaningless without market discipline. We compare our final refined projection against the **Best Current Total** line and price.

### Defining the Edge

The edge is the absolute mathematical difference between our projected total and the market line.

$$\text{Total Edge} = |\text{Projected Total} - \text{Market Total}|$$

### Staking Matrix

| Total Edge Size | Market Action | Unit Allocation |
| --- | --- | --- |
| **Less than 0.5 Runs** | Pass | 0 Units (No Value) |
| **0.5 to 0.9 Runs** | Lean (Over/Under) | LEAN (Tracked, no risk) |
| **1.0 to 1.4 Runs** | Standard Play | **1.0 Unit** |
| **1.5+ Runs or more** | Maximum Advantage Play | **3.0 Units** |

### Market Line Movement as a Signal

We treat opening-to-current line movement as a vital indicator of sharp sentiment.

* **Concurrence:** If our model projects an **Over** and the market total has moved from `8.5 (-116) → 8.5 (-122)` or jumped to `9.0`, the market is validating our thesis. This confirms a green light for a 1-unit or 3-unit bet.
* **Counter-Movement (The Red Flag):** If our model shows a massive edge on the Over, but the market line has moved strongly toward the Under (e.g., `8.5 → 8.0`), we must re-verify the data block. If no inputs were missed, we do not reverse our position, but we **reduce a 3-unit play to a 1-unit play** to respect the clear presence of opposing sharp capital.

---

## 6. Mandatory Fades (The No-Bet Zones)

To preserve capital and protect against catastrophic variance, the following scenarios dictate an **immediate, mandatory PASS**, regardless of how large our calculated edge appears:

* **Small-Sample Starters (`[sm]` Flag):** If a starting pitcher has fewer than 20.0 total innings pitched on the season or carries the `[sm]` tag on their short-term form, their projection is fundamentally unreliable. **PASS.**
* **TBD Starters:** If either starting pitcher is unannounced or listed as TBD at the time of slate evaluation. **PASS.**
* **Extreme-Velocity Wind Games ($>22\text{ mph}$):** While wind adds or subtracts value linearly up to a point, gale-force winds introduce chaotic physical variance (e.g., outfielders misjudging routine pop-ups turning into triples, or extreme movement breaking pitchers' control completely). **PASS.**
* **Stale Book Data / Flagged Prices:** If the best available price carries a `[price flagged as suspect — stale book data]` warning, that specific market is treated as dead. If alternative clean lines exist at other books on the block, those may be used; otherwise, the game is a **PASS.**

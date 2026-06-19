# TOTALS METHODOLOGY — qwen (self-authored, v1)
# Persistent Over/Under strategy. Authored 2026-06-19 via the totals
# method-authoring round. Applied to every slate alongside the ML/RL method.

This is my permanent, self-authored methodology for MLB TOTALS (Over/Under). It is designed to be strictly mechanical, quantitative, and derived solely from the provided data block and my internal baseball knowledge (specifically regarding park orientations). I will apply this exact framework to every slate to calculate my projected total, determine my edge, and assign a staking tier.

### 1. RUN ESTIMATION (Base Projection)
I anchor my projection to a baseline of **9.0 combined runs** (4.5 per team) and adjust based on weighted offensive and pitching metrics. 

*   **Starter Quality (40% Weight - Anchor):** I use the **AGG xFIP** as the primary baseline for run prevention. For every 0.25 runs the *average* of the two starters' AGG xFIP is below 4.50, I add 0.25 to the game total. For every 0.25 it is above 4.50, I subtract 0.25. *(e.g., Average xFIP of 4.00 = +0.5 runs; 5.00 = -0.5 runs).*
*   **Platoon wRC+ (25% Weight):** I look at the lineup's wRC+ against the opposing starter's handedness. 100 wRC+ is neutral. For every 10 points *above* 100, I add 0.2 runs to the game total. For every 10 points *below* 100, I subtract 0.2 runs.
*   **Recent Form (15% Weight):** I compare **L10 RS/G** to Season **RS/G**. If a team's L10 RS/G is >0.5 runs higher than their season average, I add 0.2 runs to the total. If it is >0.5 runs lower, I subtract 0.2 runs.
*   **Contact Quality (10% Weight):** I evaluate **Brl%** (Barrel Rate) and **HH%** (Hard-Hit Rate). League average is roughly 7.0% Brl / 36.0% HH. 
    *   If *both* teams have HH% > 38% and Brl% > 7.5%, I add 0.5 runs (slugfest profile).
    *   If *both* teams have HH% < 34% and Brl% < 6.0%, I subtract 0.5 runs (pitching duel/groundball profile).

### 2. PARK & ENVIRONMENT
I adjust the base estimate using the provided Park Factors and Stadium Dimensions.

*   **Park Runs Factor:** 100 is neutral. I add/subtract **0.1 runs for every 2 points** away from 100. *(e.g., A park factor of 104 adds 0.2 runs; 94 subtracts 0.3 runs).*
*   **Park HR Factor & Dimensions Synergy:** 
    *   If the Park HR factor is **< 90** (suppresses home runs, like Fenway's Green Monster) AND the opposing pitcher allows a high **Brl% (> 8.0)**, I subtract **0.25 runs** (the park neutralizes the offense's primary weapon).
    *   If a stadium has a short porch (**< 325 ft** in LF or RF) AND the opposing pitcher allows a high **Brl% (> 8.0)**, I add **0.25 runs** (high risk of pull-side fly balls clearing the short fence).

### 3. WEATHER
I use my internal knowledge of specific MLB park orientations (e.g., Fenway points North/Northeast, Wrigley points Northeast) to map the raw compass wind direction to "Blowing In" or "Blowing Out".

*   **Wind Speed & Direction:**
    *   **Blowing OUT:** 8-12 mph = **+0.25 runs**. 13-18 mph = **+0.5 runs**. 19+ mph = **+1.0 runs**.
    *   **Blowing IN:** 8-12 mph = **-0.25 runs**. 13-18 mph = **-0.5 runs**. 19+ mph = **-1.0 runs**.
    *   **Crosswind:** Ignored unless > 20 mph, in which case I add **0.25 runs** for general defensive turbulence and erratic fly balls.
*   **Temperature:** 
    *   > 85°F: Add **0.25 runs** (ball carries better, pitchers fatigue faster).
    *   < 50°F: Subtract **0.25 runs** (dense air, stiff hitters).
*   **Roof/Dome:** If the roof is closed or it is a dome, wind is 0 and temp is neutral. All weather adjustments are voided.

### 4. PITCHING & BULLPEN
I adjust for starter deviations and late-game bullpen leverage.

*   **Starter L14 Form:** If a pitcher's **L14 xFIP** is > 0.75 runs *worse* than their AGG xFIP, I add **0.3 runs** (they are in a slump). If it is > 0.75 *better*, I subtract **0.3 runs**. *(Note: If L14 is marked `[sm]` for small sample size, I ignore this adjustment entirely).*
*   **Stuff+ & K-BB%:** 
    *   **Stf+ > 115:** Subtract **0.25 runs** (elite swing-and-miss).
    *   **Stf+ < 95:** Add **0.25 runs** (hittable).
    *   **K-BB% > 20%:** Subtract **0.25 runs** (dominant control).
    *   **K-BB% < 10%:** Add **0.25 runs** (prone to free bases/rallies).
*   **Bullpen Fatigue (The 6-Day Usage Block):**
    *   If a team's **T1 (Closer)** is taxed (threw > 20 pitches yesterday, or pitched back-to-back days), I add **0.5 runs** to the total.
    *   If **T1 AND T2** are both unavailable/taxed, I add **1.0 run** (forces low-leverage arms into high-leverage spots).
    *   If both bullpens are fully fresh (T1/T2 threw 0 pitches last 2 days) and elite (Tier ERA < 3.00), I subtract **0.5 runs**.

### 5. EDGE & STAKING
My edge is calculated as: **Projected Total - Market Total**. I only use the "Best current total" price, explicitly ignoring any price flagged `[suspect — stale]`.

*   **3 Units (Max Bet):** Edge is **≥ 1.0 runs** AND price is -110 or better. *OR* Edge is **≥ 0.75 runs** AND price is +100 (plus money) or better.
*   **1 Unit (Standard Bet):** Edge is between **0.50 and 0.99 runs** AND price is -115 or better.
*   **LEAN:** Edge is between **0.25 and 0.49 runs**, *OR* Edge is > 0.5 but the price is worse than -120. (I will track these but not risk capital unless the line moves in my favor).
*   **PASS:** Edge is < 0.25 runs, or the price is worse than -125.
*   **Line Movement Signals:** 
    *   If the total line moves 0.5+ points *against* my projection (e.g., I project Under, but the market total moves UP), and my edge remains > 0.5, I will upgrade a LEAN to a **1-Unit bet** (fading public money/sharp Reverse Line Movement).
    *   If the line moves 0.5+ points *in favor* of my projection before I bet, I will only place the bet if I can still get -110 or better; otherwise, I reduce the bet to a LEAN.

### 6. WHAT YOU FADE (Mandatory Passes)
Regardless of the calculated edge, I will automatically PASS on the total in the following scenarios:
1.  **TBD Starters:** No starting pitcher data means no reliable baseline.
2.  **High Rain Probability:** If the weather block shows **> 40% rain chance**. High variance, suspended games, and unpredictable bullpen usage ruin totals models.
3.  **Extreme Park Factors:** If the Park Runs factor is **> 115 or < 85** (e.g., Coors Field). The variance is too extreme for standard regression models.
4.  **Blind Pitching Matchups:** If *both* starters have `[sm]` in their L14 and lack a robust multi-year AGG baseline (e.g., two rookies with < 30 career IPs).
5.  **Extreme Wind:** If wind speed is **> 25 mph** in *any* direction. The ball carries erratically and defensive errors spike, creating unmodelable variance.
6.  **Stale Markets:** If the only available total prices in the data block are flagged `[suspect — stale]`. I cannot bet without accurate, live market pricing.

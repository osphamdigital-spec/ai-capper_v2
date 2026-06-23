# LINEUP CONFIRM-CHECK — SYSTEM INSTRUCTIONS
# MLB  2026-06-22  model: gemini

Lineups are now confirmed for the games below. During Run 1 you made picks before lineups were posted. Your task is NOT to re-handicap each game from scratch. Re-evaluate ONLY whether the specific pre-game edge you cited still holds given the confirmed batting orders, any key scratches, and any line movement since Run 1.

For each pick, output exactly the four fields shown. CITED_FACT must name a specific player, wRC+ number, or line move — not a general impression. NEW_UNITS must equal your original units on HOLD; 0 on CANCEL; an adjusted number on DOWNGRADE/UPGRADE. An UPGRADE must respect the gap→units map in your method below. Do not add new bets not in your Run-1 picks.

## YOUR METHOD (gate and unit rules — apply exactly as written)

# PROFESSIONAL MLB HANDICAPPING METHODOLOGY (v3)

## 1. DATA PRIORITIZATION (WHAT I WEIGH & DISTRUST)
*   **Distrust:** Raw ERA, L10 team win-loss records, and L10 Runs Scored. These metrics are lagging, highly volatile, and over-weighted by the public market.
*   **Weigh:** Pitcher aggregate SIERA, xFIP, and Stuff+; platoon-specific offense wRC+; and bullpen fresh-arm availability.
*   **Contextual Modifiers:** 3-year park factors and wind velocity/direction.

## 2. THE THREE-PILLAR PROJECTION MODEL
My model projects an expected run margin (ERM) by calculating team performance across three game phases:

*   **Phase 1: Starting Pitching (50%):** I establish a baseline ERA projection using a 70/30 blend of aggregate SIERA and xFIP. This is adjusted using the opponent’s split-specific wRC+ and hard-hit percentage (HH%). L14 metrics are used strictly as a trend-check; if L14 SIERA is >1.50 runs worse than aggregate SIERA, I apply a 10% penalty to the baseline projection.
*   **Phase 2: Bullpen Bridge (30%):** I calculate a "fatigued bullpen ERA." If $\le 1$ high-leverage arm is fresh, or if key setup/closers are taxed (30+ pitches last 2 days), I inflate the bullpen's season ERA by 1.50 runs. If $\ge 2$ high-leverage arms are fresh, I use the season average.
*   **Phase 3: Park & Environment (20%):** I scale the raw projected runs using 3-year park factors. If wind exceeds 10 mph blowing out, I scale the home run factor up by 1.2% per mph.

## 3. STAKING DISCIPLINE & BANKROLL MANAGEMENT (v3)

Under the v3 bankroll framework ($10,000 starting capital; 1u = $100 base "to-win" risk), preserving capital while aggressively capitalizing on high-conviction mathematical edges is paramount. Below are my self-authored staking and portfolio rules.

### A. Edge Gates (Minimum Triggers)
No bet will be placed unless the projected value exceeds these minimum thresholds:
*   **Sides (Moneyline / Run Line):** A minimum edge of **5.0 percentage points** between my projected win probability and the market implied probability (calculated minus the vig).
*   **Totals (Over / Under):** A minimum difference of **0.50 runs** between my projected total runs and the market total.

### B. Slate Ceiling (Portfolio Risk Limits)
*   **Ceiling Limit:** Maximum of **4 active bets** per daily slate.
*   **Unified Spanning Rule:** This ceiling **spans BOTH markets combined** (Sides and Totals share the same 4-bet limit). 
*   **Reasoning:** Limiting daily exposure to 4 total bets across all markets prevents correlated bankroll disasters (e.g., suffering a sweep where an unexpected wind shift or umpire zone destroys an Over and a Side simultaneously). If more than 4 games meet my edge gate on a single slate, the plays are ranked by absolute edge size, and only the top 4 are selected.

### C. 1-Unit vs. 3-Unit Thresholds
To maximize Expected Value (EV) while protecting against high-variance spots, stakes are assigned based on the following rules:

*   **3-Unit Bets (Max Play / Best Bet candidate):**
    *   *Sides:* Edge $\ge$ **8.0 percentage points**.
    *   *Totals:* Difference $\ge$ **0.80 runs**.
    *   *Qualitative Filter:* The starting pitcher must NOT be flagged [small sample], and the bullpen must not be penalized under Phase 2.
*   **1-Unit Bets:**
    *   *Sides:* Edge between **5.0 and 7.9 percentage points**.
    *   *Totals:* Difference between **0.50 and 0.79 runs**.
    *   *Downgrade Rule:* Any edge that mathematically qualifies for a 3-unit bet (edge $\ge$ 8.0 pts / 0.80 runs) is automatically demoted to a 1-unit bet if the starting pitcher is flagged **[small sample]** or the team's bullpen is penalized for fatigue under Phase 2.

### D. Best Bet Designation
*   My single highest-conviction 3-unit play on the slate will be labeled my **Best Bet**. If no plays reach the 3-unit threshold, or if multiple 3-unit plays carry identical edge metrics, no Best Bet will be declared.

## 4. STRICT PASS TRIGGERS & DATA INTEGRITY
I immediately pass, demote, or hold under these conditions:
*   **TBD Starter:** Absolute PASS on all markets for that game.
*   **Starter flagged [small sample]:** Cap the maximum stake at 1 unit (no 3-unit plays allowed, as detailed in Section 3C).
*   **Price flagged suspect/stale:** Disregard that specific market; pass unless clean, verified book prices are available.
*   **Coors Field or High-Wind Environments ($>$15 mph):** Pass on all total and run line markets due to extreme physical variance; limit exposure to Moneyline only, provided the 5.0 percentage point edge gate is met.

## 5. FEEDBACK LOOP EVALUATION (v3 METRIC TRACKING)
Using the v3 account history feedback, my performance will be monitored and adjusted at regular intervals using these key indicators:
*   **CLV (Closing Line Value):** Must remain positive (+10c or better average). If CLV turns negative over a 30-bet sample, my model's market-timing or projection baselines will be audited.
*   **1u vs. 3u Split performance:** If 3-unit plays show a negative ROI while 1-unit plays are positive, it indicates that my high-edge threshold is failing to account for tail-risk. If this occurs, the 3u threshold will be tightened (e.g., raising the side gate to 9.0 percentage points).
*   **Totals vs. Sides ROI:** Since totals and sides share a unified slate ceiling, if one market significantly underperforms the other over a sustained sample, the slate ceiling will be adjusted to favor the higher-performing market.

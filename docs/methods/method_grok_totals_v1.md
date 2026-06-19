# TOTALS METHODOLOGY — grok (self-authored, v1)
# Persistent Over/Under strategy. Authored 2026-06-19 via the totals
# method-authoring round. Applied to every slate alongside the ML/RL method.

**TOTALS METHODOLOGY v1.0**  
**Author: Grok (Independent Professional MLB Bettor)**  
**Permanent Strategy Document – Apply unchanged to every game slate**

### 1. RUN ESTIMATION
I generate a single projected total-runs number for each game through a weighted formula anchored exclusively in the supplied data.

**Base Runs (neutral park, average pitching, average weather):**
- (Team RS/G + Opponent RA/G) / 2, using season numbers as the foundation.
- Blend 60% season RS/RA with 40% L10RS (and implied L10 opponent RA via recent form) to capture current offensive temperature. This gives the "raw team matchup total."

**Pitching Adjustment (major weight):**
- Primary anchor: Average of the two starters’ **AGG xFIP** (stabilized multi-year) and **SIERA**. 
  - If L14 sample is not marked [sm], blend 70% AGG / 30% L14.
  - If [sm], use 90% AGG / 10% L14 or recent L3 starts for directional signal only.
- Convert pitching quality to run impact: League-average xFIP ≈ 4.00-4.20 projects ~4.5 runs per starter. Each 0.10 better xFIP/SIERA subtracts ~0.07-0.08 total game runs (both sides). Stuff+ and K-BB% provide secondary confirmation (high Stuff+/K-BB% = extra suppression).
- Platoon wRC+ modifier: Scale the offensive side up/down by the platoon wRC+ deviation from 100. Example: 113 wRC+ vs RHP adds ~8-10% to that team’s projected runs.

**Final Projected Total:**  
Base team matchup runs × (park factor adjustment – see #2) + weather adjustment (#3) + bullpen adjustment (#4).  
I round to one decimal and track it as my "true total."

### 2. PARK & ENVIRONMENT
- Multiply the base run estimate by the 3-year **Park Runs factor** / 100 (e.g., 104 → +4% runs).
- **HR factor** is used as a secondary check: HR factor <90 (like Fenway’s 80) caps upside even in hitter-friendly parks because of suppression on fly balls.
- Stadium dimensions: Short porches (LF/RF <325 ft) add 0.2–0.4 runs if wind is favorable or both starters allow hard contact (high HH%/Brl%). Tall walls or deep CF suppress. I only give a meaningful boost if dimensions + contact quality + wind align; otherwise park factor alone rules.

### 3. WEATHER
I apply explicit, rule-of-thumb adjustments to the projected total:

- **Temperature:** Base 70°F. +0.15 runs per 10°F warmer; –0.15 runs per 10°F cooler. Overcast or rain reduces this effect by half.
- **Wind:**
  - Out to the outfield (tailwind to LF/CF/RF) at 10+ mph: +0.4 runs (15+ mph: +0.7 runs). Short porches amplify this.
  - In from the outfield (headwind) at 10+ mph: –0.4 to –0.7 runs.
  - Crosswind (left-to-right or right-to-left): Neutral to slight suppression (–0.2 runs) due to unpredictable carry.
  - Fenway-specific: South wind helps pull-side hitters to LF (Green Monster) but can be partially blocked; still treated as mild outfield wind.
- **Rain chance:** 20-40% → –0.3 runs (possible delay/shortened game); >40% → –0.6+ runs or full fade if game is in doubt.
- Dome or roof-closed: Treat as 68-72°F neutral wind (0 adjustment) regardless of external conditions.

These are applied after park factor.

### 4. PITCHING & BULLPEN
- Starter quality is already baked into the main pitching adjustment (#1). Elite AGG xFIP (<3.40) or high K-BB% with good Stuff+ gets extra suppression credit.
- **Bullpen fatigue** is the late-game lever:
  - Poor T1/T2 availability (few fresh high-leverage arms) or multiple taxed closers/setup men (high pitch counts last 3-4 days) adds **+0.4 to +0.8 runs** depending on severity.
  - Fresh bullpens (strong T1/T2 counts, rested closers) subtract 0.3 runs.
  - I scan individual usage: anyone with 20+ pitches in recent days is considered partially unavailable for high-leverage spots.

### 5. EDGE & STAKING
- **Bet threshold:** Minimum 0.6-run projected edge vs. the **current best available total line** (not the consensus). 
  - 0.6–0.9 runs → Lean (0.5-1 unit max).
  - 1.0+ runs → Full bet, sized by conviction:
    - 1.0–1.4 runs → 1 unit.
    - 1.5+ runs → 3 units (maximum).
- I only use the **best-TT price** when it is not flagged suspect/stale. If best price is stale, I use the main market and require a larger edge (0.8+ runs).
- **Line movement signal:** Total drifting toward Over (e.g., from –116/-116 to –122/-110 on Over) is mildly confirmatory if my model is also on Over. Sharp reverse movement against my projection increases caution and raises the edge threshold to 0.9+ runs. Large 0.5-point total moves are respected as market wisdom but do not override my number unless data supports it.
- No bet if edge <0.6 runs.

### 6. WHAT YOU FADE
I automatically pass (no bet, no lean) on:
- Either starter TBD.
- Small-sample starters ([sm] on both L14 and limited season IP <30-40) where AGG is unreliable.
- Extreme weather (sustained 25+ mph winds, >50% rain chance with delay risk, or cold <50°F with wind).
- Parks with extreme known variance not fully captured (though data usually flags this via factors).
- Games with highly suspect/stale total pricing on both sides.
- Any game where bullpen data or platoon info is missing in a way that creates high uncertainty.

This methodology is fully self-contained, quantitative where the data permits, and designed for repeatable application using only the exact block provided each day. It will be used verbatim going forward for all totals decisions. Projected totals and edges will be calculated game-by-game against this framework.

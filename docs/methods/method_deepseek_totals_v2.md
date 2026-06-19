# TOTALS METHODOLOGY — deepseek (self-authored, v3)
# Persistent Over/Under strategy. Authored 2026-06-19, revised 2026-07-20.
# Author now owns totals staking: edge gate, 1u/3u threshold, slate ceiling.

1. RUN ESTIMATION

I estimate expected combined runs as the sum of each team’s projected runs,
derived from a base projection adjusted for starting pitching, park, weather,
and bullpen.

**Step 1 – Raw Offensive/Defensive Baseline**
For Team A (away) vs Team B (home):

- `Off_raw_A = (Team A RS/game + Team B RA/game) / 2`
- `Off_raw_B = (Team B RS/game + Team A RA/game) / 2`

These capture both the offense’s scoring ability and the opponent’s run
prevention, assuming a neutral environment.

**Step 2 – Apply Park Factor**
Multiply each raw projection by the park’s Runs factor divided by 100:

- `Park_adj_A = Off_raw_A × (PF_Runs / 100)`
- `Park_adj_B = Off_raw_B × (PF_Runs / 100)`

Example: Fenway Runs 104 → factor = 1.04.

**Step 3 – Starting Pitcher Adjustment**
I blend each starter’s multi-year stabilized SIERA (AGG) with their recent form
(L14 SIERA). If L14 is flagged `[sm]` (small sample, <15 IP), I use 85% AGG /
15% L14; otherwise 70% AGG / 30% L14.

- `Blended_SIERA = (AGG_SIERA × w_AGG) + (L14_SIERA × w_L14)`

League‑average run environment is set at 4.50 runs per 9 IP. The opposing
starter’s run‑suppression factor is:

- `Pitcher_factor = Blended_SIERA / 4.50`

Then:

- `Proj_A = Park_adj_A × (Opp_SP_factor)`
- `Proj_B = Park_adj_B × (Opp_SP_factor)`

*Stf+ bonus*: If a starter has Stf+ ≥ 115, I subtract an additional 0.15 runs
from the opponent’s projection (elite stuff suppresses offense beyond SIERA).
If Stf+ ≤ 85, add 0.15 runs.

**Step 4 – Platoon Matchup Adjustment**
The data gives team wRC+ vs the starter’s handedness. I use it as a fine‑tune:

- If wRC+ ≥ 115, add 0.15 runs to that team’s projection.
- If wRC+ ≤ 85, subtract 0.15 runs.

This is applied after the starter adjustment, to avoid double‑counting the
platoon split.

**Step 5 – Recent Offensive Form**
I blend season RS/G with last‑10 RS/G (L10RS). Weight: 60% season RS/game, 40%
L10RS to create a “current offense” number for each team. I then re‑average the
raw offensive baseline using this blended RS number instead of pure season RS,
recalculating Step 1 once. This captures hot/cold streaks.

- `RS_blend = 0.6 × RS_season + 0.4 × L10RS`

**Final Pre‑Weather Total**
`Exp_runs_pre_weather = Proj_A + Proj_B`


2. PARK & ENVIRONMENT

- **Park Factor (Runs):** Already embedded in Step 2 as a multiplicative factor.
- **HR Factor:** Not used directly in run projection (it influences variance,
  not expected total), but it governs my fade rules (Section 6).
- **Stadium Dimensions:** Used only to interpret wind direction. A short porch
  (e.g., RF 302 ft) means a wind blowing toward that porch can dramatically
  increase home runs. The raw distances are referenced when I judge whether a
  wind direction is “blowing out” to a favorable part of the park.


3. WEATHER

**Wind**  
I determine the wind’s effect by its speed and direction relative to the park’s
outfield. The data gives compass direction (e.g., “S” – south). I require a
rule‑of‑thumb mapping that works without looking up stadium orientation:

- **Wind > 15 mph blowing straight out** (i.e., from home plate toward center
  field, judged by typical park configuration: if the direction matches the
  general outfield bearing I recall for that park) → add **1.0 runs** for 16‑20
  mph, **+1.5 runs** for 21‑25 mph.
- **Wind 10‑15 mph blowing out** → add **0.5 runs**.
- **Wind > 15 mph blowing in** → subtract **1.0 runs** (16‑20 mph), subtract
  **1.5 runs** (21‑25 mph).
- **Crosswind** (blowing parallel to the outfield wall) or wind ≤ 10 mph → no
  adjustment.
- **Wind > 25 mph in any direction**: mandatory fade (Section 6).

If I cannot confidently determine out/in from park memory, I treat the wind as
neutral (0 adjustment) unless the wind is extreme (>20 mph), in which case I
add 0.5 runs to reflect general chaos.

**Temperature**  
- Base temperature effect: for every 5°F above 75°F, add **0.10 runs** (warmer
  air reduces density, ball travels farther).  
- Below 55°F, subtract 0.10 runs per 5°F below 55.

**Rain**  
- Rain chance ≥ 50% but < 60%: subtract 0.20 runs (potential delays/poor
  conditions).  
- Rain chance ≥ 60%: game is a pass (fade) due to possible postponement or
  shortened game.

**Domed/Retractable Roof (closed):** Weather adjustment = 0, regardless of
outside conditions.


4. PITCHING & BULLPEN

**Starting Pitcher**  
Already covered in run estimation via blended SIERA and Stf+ bonus. In addition:

- I rely primarily on SIERA/xFIP because they isolate pitcher skill. ERA and
  xERA are used only as tie‑breakers when SIERA models produce an edge exactly
  at a threshold.
- The `L3` game logs (IP/ER/K/BB) are a quick trend check: if a starter’s last
  3 starts show a drastically different K/BB or run‑prevention pattern than
  his blended SIERA, I may manually nudge the projection by ±0.20 runs, but
  only if all three starts consistently deviate in the same direction. This is
  rare and explicitly noted.

**Bullpen**  
The bullpen adjustment is additive, applied after the pre‑weather total.

I use the availability counts by tier:

- **T1 (closer/setup):** If `T1: 0/1 avail`, add **0.30 runs** to the opponent’s
  projected total. (Missing top arms = leaky late innings.)
- **T2:** If fewer than 2 arms available (e.g., `1/2` or `0/2`), add **0.15 runs**.
- **T3:** If fewer than 4 arms available (e.g., `3/5`), add **0.10 runs**.

These effects stack – a team with both T1 empty and T2 low adds 0.45 runs. The
penalty is assessed to the team *with* the depleted bullpen, i.e., it raises
the opponent’s expected runs.

Additionally, I scan individual reliever usage: if the closer threw ≥ 30 pitches
over the last 2 days and is still listed as “available”, I treat him as
effectively unavailable and apply the T1 penalty (unless the availability count
already captured it). This prevents the count from missing hidden fatigue.

**Final expected total**
`Exp_total = Exp_runs_pre_weather + Wind_adj + Temp_adj + Rain_adj + Bullpen_adj`


5. EDGE & STAKING (author‑owned)

**Edge calculation**  
`Edge = Exp_total – Posted_Total` (for Over bets)  
`Edge = Posted_Total – Exp_total` (for Under bets)

Always compare against the **best available total line** from the “Best current
total” field, ignoring any flagged suspect/stale price. If the only available
price is suspect, the game is a pass.

**My totals edge gate**  
I will only place a bet when my edge is **≥ 0.75 runs**. Anything below that
triggers a pass (no action). I no longer use LEAN as an output category; any
edge below 0.75 is simply a pass.

**1‑unit vs 3‑unit threshold**  
- **Edge 0.75 – 0.99 runs** → **1 unit (1u)**  
- **Edge ≥ 1.00 runs** → **3 units (3u)**  

There are no additional qualifiers: once the 0.75 gate is cleared, the
step‑up to 3u depends solely on the modeled edge crossing 1.00 runs.

**Line movement as a signal modifier**  
If the total has moved ≥ 0.5 runs from the opening line (from “OPENING LINES”
→ current bet365 total):

- Movement **in my favor** (e.g., I like Over and the total has risen 0.5): no
  adjustment.
- Movement **against my bet** (I like Over, total has dropped 0.5): I increase
  the required edge by **0.25 runs**. So a 1‑unit bet needs ≥ 1.00 edge, and a
  3‑unit bet needs ≥ 1.25 edge.

If the price has steamed heavily (e.g., -130 or more on one side), I add an
extra **0.15 runs** to the required edge on top of any movement adjustment.
This keeps me from fighting sharp market steam.

**Slate ceiling for totals**  
I operate a **separate slate ceiling for totals**, independent of any side
(ML/RL) bets. My overall sides method document defines its own per‑slate bet
limit; a total and a side on the same game both count toward their respective
limits — they do not share a combined bucket. This prevents over‑exposure
within a single market type.

My totals‑only maximum per slate:

- **1–7 games on the slate** → up to **1 totals bet**
- **8–14 games** → up to **2 totals bets**
- **15+ games** → up to **3 totals bets**

When multiple qualifying bets exceed the limit, I select those with the largest
absolute edge (after all adjustments). If two edges are equal, I prefer the game
with line movement already in my favor (signalling possible closing‑line value).

All totals bets are staked to a **to‑win** convention, with 1 unit = $100 from a
$10,000 bankroll.


6. WHAT YOU FADE

I refuse to bet a total (regardless of edge) in these situations:

- **Missing starter:** Either starter is TBD or listed as “opener/bullpen game”
  with no projected primary pitcher.
- **Suspended data:** The best available total price is flagged suspect/stale
  and no clean alternative exists.
- **Blowout wind:** Wind speed > 25 mph in any direction — extreme uncertainty
  overrides all models.
- **Rain risk:** Rain chance ≥ 60% or game already under a delay threat.
- **Extreme home‑run parks:**  
   - I will **not bet Under** in parks with HR factor ≥ 110 (e.g., Great
     American, Coors — high variance blow‑up risk).  
   - I will **not bet Over** in parks with HR factor ≤ 85 (deadball environments
     where runs may come only in bunches but are not reliable). Fenway’s HR
     factor 80 thus bans Over bets; Unders are permitted.
- **Small‑sample starter meltdown red flag:** If L14 SIERA is ≥ 2.00 runs
  higher than AGG SIERA *and* the L14 sample is small (`[sm]`), I pass — the
  data is too noisy to trust either the recent collapse or the stable skill.
- **Bullpen Armageddon:** Both teams have T1 0/1 *and* T2 ≤ 1 available —
  expect late‑game chaos that can break either way. Pass.
- **Game on a getaway day** (if such info appears in the data block; currently
  it does not, but if added later, fade totals due to resting regulars). For
  now, not applicable.

If any of these conditions are met, I output **No bet** regardless of the edge.
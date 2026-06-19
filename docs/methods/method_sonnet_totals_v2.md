# TOTALS METHODOLOGY — sonnet (self-authored, v3)
# Persistent Over/Under strategy. Revised 2026-06-19 to v3 under self-authored staking rules.
# Replaces v1/v2. Applied to every slate alongside the ML/RL method.

---

## 1. RUN ESTIMATION

**Offensive baseline.** For each team: `0.65 × season RS/G + 0.35 × L10RS/G`. Season rate anchors against noise; the L10 weight captures genuinely current form — hot/cold streaks, recent lineup or injury changes — without letting a 10-game sample dominate.

**Pitcher quality index.** Built almost entirely from stabilized numbers, not ERA:
- AGG xFIP/SIERA blend = 75% weight (these stabilize fastest and predict true talent best)
- ERA/FIP = 15% weight (sanity check only)
- L14 form = 10% weight, and **set to zero** if flagged `[sm]` — an unstable sample shouldn't move a real number

Index = `league-average xFIP (~4.20) ÷ pitcher's blended xFIP`. Above 1.0 = suppresses runs; below 1.0 = gets hit.

**Platoon adjustment.** `(lineup wRC+ vs that handedness ÷ 100)^0.5` — square-rooted deliberately, because platoon splits are real but secondary; I don't want a 156 wRC+ key bat overriding a stabilized pitching read.

**Combine per team:** `Offensive baseline × Pitcher quality index⁻¹ × Platoon index`. Sum both teams for the starter-window (~6 IP) estimate, then add a fixed league-average bullpen carryover (~4.3 runs combined over the final 3 innings) as a placeholder before bullpen-specific adjustments in §4. This sum is the **Raw Total Estimate**.

---

## 2. PARK & ENVIRONMENT

- Multiply Raw Total Estimate by `Park Runs factor ÷ 100`. (Fenway 104 → ×1.04.)
- HR factor and wall dimensions are read as *context*, not a second multiplier — using both Runs and HR factors quantitatively would double-count the same effect. Short porches with a high wall (Fenway: 310ft LF but HR factor only 80) get a qualitative flag — "HR-suppressed despite short distance" — but no separate number.
- Symmetric short porches (both fences <330ft) get a flag for HR-driven total volatility, factored into staking (§5), not into the run number itself.

---

## 3. WEATHER

- **Wind direction first.** I classify direction relative to the park's known orientation (using my own knowledge of each stadium's layout, since orientation isn't given). True "out" or "in" winds get the formula below; anything reading as a crosswind (roughly parallel to the foul lines) gets a flat ±0.1 runs — wind drift affects placement more than distance.
- **Wind OUT:** `+0.3 runs × ((speed − 5) / 10)`, floored at 0, **capped at +1.0 run** regardless of reading — gusts in a data feed are unreliable at the extremes.
- **Wind IN:** same scale, capped at −1.0 run.
- **Temperature:** `+0.15 runs per 10°F above 70°F`; `−0.15 runs per 10°F below 60°F`; capped at ±0.5 runs total.
- **Rain probability:** no direct run adjustment (too weakly correlated with this data alone) — instead it raises my required edge threshold in §5. At ≥70% I flag elevated delay/postponement risk but don't auto-pass, since the data doesn't confirm postponement.
- **Dome/roof-closed:** weather adjustment = 0, full stop.

---

## 4. PITCHING & BULLPEN

- Starter quality is already in the Raw Total via §1. Two overlays on top:
  - **L14 flag:** if L14 SIERA/xFIP is 1.5+ runs worse than AGG *and not [sm]*, shade the opponent's expected runs +0.2. If [sm], ignore entirely.
  - **Stuff+ tiebreaker:** Stf+ <95 adds a flat +0.1 to runs allowed, independent of xFIP — pure stuff often leads the rate stats.
- **Bullpen fatigue:** start from neutral. Each unavailable/taxed T1 or T2 arm (0 days rest, or 20+ pitches in each of the last two appearances) adds +0.15 to that team's runs-allowed estimate, capped at +0.4 per pen. A fully fresh T1+T2 (1/1 and 2/2 available) earns a −0.1 shade in that team's favor.
- If **both** pens show 2+ combined T1/T2 arms unavailable, add a flat +0.3 to the total — thin benches mean worse arms absorb more leverage innings league-wide, not just for one side.

---

## 5. EDGE & STAKING

**Final Adjusted Total** = Raw Total × park multiplier + weather adjustment + bullpen/L14/Stuff+ shades.

**Edge** = Final Adjusted Total − current posted line (current, not opening — it reflects sharper pricing; opening-to-current movement is tracked separately as a confirmation signal below).

### 5a. Totals Edge Gate

**My minimum edge to consider any bet is 1.0 run.** Edges below this threshold receive no stake. A narrow gap between my projection and the posted line means I am essentially agreeing with the market — there is no legitimate informational case for putting money on either side. I set the gate at 1.0 rather than something tighter because totals models carry compounding uncertainty: offensive baseline error, bullpen sequencing noise, weather variance at first pitch, and park factor imprecision all accumulate. A sub-1.0 edge is well within that error band.

Between 0.5 and 0.9 runs I may note a **LEAN** — a directional opinion with no stake. Lean = zero units. This preserves the directional signal for self-review purposes without treating a marginal number as actionable.

| Edge | Action |
|---|---|
| < 0.5 runs | No bet, no lean noted |
| 0.5–0.9 runs | Lean only — zero units |
| 1.0–1.4 runs | **1 unit** |
| ≥ 1.5 runs | **3 units** |

### 5b. 1u-vs-3u Threshold

The step from 1 unit to 3 units is not taken lightly. 3 units represents a high-conviction play, and I require two things simultaneously before committing to it:

1. **Run gap ≥ 1.5 runs** between my Final Adjusted Total and the posted line.
2. **No active uncertainty flag** from the conditions below.

Even with a gap ≥ 1.5 runs, I hold at 1 unit if any of the following apply:
- Rain probability ≥ 40% (raised threshold environment — see below)
- Either bullpen is flagged as severely depleted with 3+ unavailable arms (model error bar expands significantly)
- The total line has shown 3+ directional reversals in its movement history (market has information I cannot see)
- Extreme hitter's park (Runs factor ≥115) with two replacement-level starters (both AGG xFIP >4.50) — the "true total" range in this combination is too wide to justify maximum stake

The reasoning: a 3-unit bet means I am expressing genuine confidence that my number is right and the market is meaningfully wrong. A large run gap alone can be produced by unusual circumstances that also inflate uncertainty. The combination of a large gap *and* a clean environment is rarer and more meaningful than a large gap alone.

### 5c. Line Movement as Confirmation Signal

A 0.5+ point move, or a 12-cent+ vig shift, in the *same* direction as my edge bumps me one staking tier (e.g., a 0.9-run edge confirmed by sharp movement → 1 unit instead of a lean). The same magnitude moving *against* my edge downgrades one tier — the market may be pricing a weather update, late lineup change, or injury not yet visible in my data block, and I defer rather than fight it blind.

This adjustment applies after the base table above, not before. It cannot push a sub-0.5 edge into action.

### 5d. Rain Probability Adjustment

At ≥40% rain probability, all edge thresholds shift up by 0.3 runs before any bet or lean is granted. A 1.0-run edge in clean weather becomes a 1.3-run minimum at 40%+ rain. This applies to both the 1u gate and the 3u threshold. Rain degrades confidence in wind readings, temperature stability, and game completion — the additional edge requirement compensates for that uncertainty rather than ignoring it.

---

## 6. SLATE CEILING AND INTERACTION WITH SIDES

My overall slate ceiling is defined in my main (sides/ML-RL) method document. Totals and sides share a **single unified ceiling**. A total bet on a game and a side bet on the same game each count as one bet toward the ceiling — they are not treated as a single combined position just because they share a ballpark.

The reasoning: my bankroll is unified. Whether I am exposed to a game through a side, a total, or both, each wager draws on the same capital and adds to my daily variance. Running a separate ceiling for totals would allow me to silently double my effective action on high-interest games, which would undermine the risk discipline that the ceiling exists to enforce.

**Practical effect:** on a slate where I have already reached my ceiling with side bets, a qualifying total — even one with a strong edge — does not get placed. The ceiling is a hard stop. Totals with strong edges that go unplayed due to ceiling limits are noted in my working log for calibration purposes but do not override the cap.

If a total qualifies and a side on the same game also qualifies, I place both only if ceiling space remains for both as individual bets. I do not automatically suppress the total because I also have a side — I evaluate each on its own merits and let the ceiling govern total exposure.

---

## 7. MANDATORY PASS TRIGGERS

- Either starter TBD → mandatory pass.
- A starter whose AGG sample is under ~15 IP, or whose only available signal is `[sm]`-flagged → pass regardless of edge; there is no real foundation under the number.
- A stale/suspect-flagged price → treat that side as absent. If both sides are stale, pass the total entirely.
- Wind ≥25mph combined with rain% ≥50% → pass. Too volatile to trust before first pitch.
- Total line with 3+ direction reversals in its movement history → cap at Lean regardless of computed edge; that kind of flip-flopping signals information I cannot see in this data block.
- Extreme hitter's parks (Runs factor ≥115) paired with two replacement-level starters (both AGG xFIP >4.50) → Lean max, never full units. The error bar on "true total" in these spots is wider than my staking tiers are built to responsibly cover.

---

## 8. ACCOUNT HISTORY AND SELF-REVIEW

Before each slate I receive my own totals performance history (e.g., `Totals (O/U): N bets / W-L / net $`). I treat this as calibration data, not a feedback loop that automatically changes my method mid-season.

Small samples — fewer than 30 totals bets — carry too much variance to draw conclusions about edge gate calibration or threshold placement. Drawing no conclusion from a small sample is a valid and disciplined response. I will not tighten or loosen my gate reactively after a short losing streak or a short winning streak.

If a meaningful sample (30+ totals bets) shows persistent underperformance in a specific category — e.g., 3-unit plays losing at a rate inconsistent with model error — I will revisit the 3u threshold conditions in §5b at the end-of-season review. In-season, the method runs as written.
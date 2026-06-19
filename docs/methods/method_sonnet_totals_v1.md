# TOTALS METHODOLOGY — sonnet (self-authored, v1)
# Persistent Over/Under strategy. Authored 2026-06-19 via the totals
# method-authoring round. Applied to every slate alongside the ML/RL method.

# TOTALS METHODOLOGY — Permanent Strategy Document

## 1. RUN ESTIMATION

**Offensive baseline.** For each team: `0.65 × season RS/G + 0.35 × L10RS/G`. Season rate anchors against noise; the L10 weight captures genuinely current form (hot/cold streaks, recent lineup or injury changes) without letting a 10-game sample dominate.

**Pitcher quality index.** Built almost entirely from stabilized numbers, not ERA:
- AGG xFIP/SIERA blend = 75% weight (these stabilize fastest and predict true talent best)
- ERA/FIP = 15% weight (sanity check only)
- L14 form = 10% weight, and **set to zero** if flagged `[sm]` — an unstable sample shouldn't move a real number

Index = `league-average xFIP (~4.20) ÷ pitcher's blended xFIP`. Above 1.0 = suppresses runs; below 1.0 = gets hit.

**Platoon adjustment.** `(lineup wRC+ vs that handedness ÷ 100)^0.5` — square-rooted deliberately, because platoon splits are real but secondary; I don't want a 156 wRC+ key bat overriding a stabilized pitching read.

**Combine per team:** `Offensive baseline × Pitcher quality index⁻¹ × Platoon index`. Sum both teams for the starter-window (~6 IP) estimate, then add a fixed league-average bullpen carryover (~4.3 runs combined over the final 3 innings) as a placeholder before bullpen-specific adjustments in §4. This sum is the **Raw Total Estimate**.

## 2. PARK & ENVIRONMENT

- Multiply Raw Total Estimate by `Park Runs factor ÷ 100`. (Fenway 104 → ×1.04.)
- HR factor and wall dimensions are read as *context*, not a second multiplier — using both Runs and HR factors quantitatively would double-count the same effect. Short porches with a high wall (Fenway: 310ft LF but HR factor only 80) get a qualitative flag — "HR-suppressed despite short distance" — but no separate number.
- Symmetric short porches (both fences <330ft) get a flag for HR-driven total volatility, factored into staking (§5/§6), not into the run number itself.

## 3. WEATHER

- **Wind direction first.** I classify direction relative to the park's known orientation (using my own knowledge of each stadium's layout, since orientation isn't given). True "out" or "in" winds get the formula below; anything reading as a crosswind (roughly parallel to the foul lines) gets a flat ±0.1 runs — wind drift affects placement more than distance.
- **Wind OUT:** `+0.3 runs × ((speed − 5) / 10)`, floored at 0, **capped at +1.0 run** regardless of reading — gusts in a data feed are unreliable at the extremes.
- **Wind IN:** same scale, capped at −1.0 run.
- **Temperature:** `+0.15 runs per 10°F above 70°F`; `−0.15 runs per 10°F below 60°F`; capped at ±0.5 runs total.
- **Rain probability:** no direct run adjustment (too weakly correlated with this data alone) — instead it raises my required edge threshold in §5. At ≥70% I flag elevated delay/postponement risk but don't auto-pass, since the data doesn't confirm postponement.
- **Dome/roof-closed:** weather adjustment = 0, full stop.

## 4. PITCHING & BULLPEN

- Starter quality is already in the Raw Total via §1. Two overlays on top:
  - **L14 flag:** if L14 SIERA/xFIP is 1.5+ runs worse than AGG *and not [sm]*, shade the opponent's expected runs +0.2. If [sm], ignore entirely.
  - **Stuff+ tiebreaker:** Stf+ <95 adds a flat +0.1 to runs allowed, independent of xFIP — pure stuff often leads the rate stats.
- **Bullpen fatigue:** start from neutral. Each unavailable/taxed T1 or T2 arm (0 days rest, or 20+ pitches in each of the last two appearances) adds +0.15 to that team's runs-allowed estimate, capped at +0.4 per pen. A fully fresh T1+T2 (1/1 and 2/2 available) earns a −0.1 shade in that team's favor.
- If **both** pens show 2+ combined T1/T2 arms unavailable, add a flat +0.3 to the total — thin benches mean worse arms absorb more leverage innings league-wide, not just for one side.

## 5. EDGE & STAKING

**Final Adjusted Total** = Raw Total × park multiplier + weather adjustment + bullpen/L14/Stuff+ shades.

**Edge** = Final Adjusted Total − current posted line (current, not opening — it reflects sharper pricing; opening-to-current movement is tracked separately as signal below).

| Edge | Action |
|---|---|
| < 0.5 runs | No bet |
| 0.5–0.9 runs | Lean only, no units |
| 1.0–1.4 runs | 1 unit |
| ≥ 1.5 runs | 3 units |

**Line movement as signal:** a 0.5+ point move, or a 12-cent+ vig shift, in the *same* direction as my edge bumps me one staking tier (e.g., a 0.9 edge confirmed by sharp movement → 1 unit instead of a lean). The same magnitude moving *against* my edge downgrades one tier — the market may be pricing something my data block doesn't show (a weather update, late lineup change), and I'd rather defer than fight it blind.

**Rain probability** raises the bar: at ≥40% rain, the edge thresholds above shift up by 0.3 runs across the board before any bet/lean is granted.

## 6. WHAT YOU FADE

- Either starter TBD → mandatory pass.
- A starter whose AGG sample is under ~15 IP, or whose only available signal is `[sm]`-flagged → pass regardless of edge; there's no real foundation under the number.
- A stale/suspect-flagged price → treat that side as absent. If both sides are stale, pass the total entirely.
- Wind ≥25mph combined with rain% ≥50% → pass. Too volatile to trust before first pitch.
- Total line with 3+ direction reversals in its movement history → cap at Lean regardless of computed edge; that kind of flip-flopping means the market knows something I can't see in this data.
- Extreme hitter's parks (Runs factor ≥115) paired with two replacement-level starters (both AGG xFIP >4.50) → Lean max, never full units. The error bar on "true total" in these spots is wider than my staking tiers are built to responsibly cover.

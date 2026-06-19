# TOTALS METHODOLOGY — K2.6 (REVISED v3)
# Persistent Over/Under strategy. Revised to self-authored edge gate,
# 1u/3u threshold, and unified slate ceiling. Applied to every slate.

---

## 1. RUN ESTIMATION

I estimate expected combined runs through a weighted composite of four inputs, anchored on **pitcher quality** and **current offensive form**, with secondary weights on season baselines and platoon advantages.

**Base Estimate = (Away Expected Runs + Home Expected Runs)**

**Away Team Expected Runs:**
- Start with their **L10RS** (last-10-game runs scored per game) — this captures current offensive momentum. Weight: **40%**
- Add their season **RS** (runs scored per game) as a stabilizer. Weight: **20%**
- Subtract the **home starter's expected runs allowed**: I use a 50/50 blend of their **AGG xFIP** (stabilized multi-year) and **L14 xFIP** (recent form), converted to runs per 9 innings. If L14 is flagged [sm] (small sample), weight 80% AGG / 20% L14. Weight: **30%**
- Adjust for **platoon wRC+ vs RHP/LHP**: If wRC+ > 110, add 0.15 runs per 10 points above 110. If < 90, subtract 0.15 runs per 10 points below 90. Weight: **10%**

**Home Team Expected Runs:** Same structure, using home team's offensive stats and away starter's pitching stats.

**Pitcher-to-Runs Conversion:** xFIP is already scaled to runs per 9 innings, so I use it directly as "expected runs allowed per 9 IP." I assume ~5.5 IP for an average start, scaling the starter's contribution accordingly, with the remaining 3.5 IP filled by bullpen (see Section 4).

**Example math for TOR @ BOS:**
- TOR L10RS = 4.2, season RS = 4.1 → weighted offense = (4.2×0.4) + (4.1×0.2) = 2.50
- vs Gray (AGG xFIP 3.24, L14 xFIP 3.53, no [sm] flag): (3.24×0.5 + 3.53×0.5) = 3.39 → scaled to 5.5 IP = 2.07 runs
- TOR vs RHP wRC+ = 113 (slight platoon edge): +0.15 × 1.3 = +0.20
- TOR expected runs ≈ 2.50 + 2.07 + 0.20 = **4.77** (but this double-counts; correction: the offense baseline already embeds pitcher quality, so I use a cleaner approach)

**Refined Approach (to avoid double-counting):**

I use a **simpler, more robust formula** to avoid the circularity above:

1. **Offensive baseline** = (L10RS × 0.5) + (Season RS × 0.3) + (League average 4.3 × 0.2) = weighted team scoring rate
2. **Pitcher suppression** = (AGG xFIP × 0.6) + (L14 xFIP × 0.4) [or 80/20 if L14 is [sm]]
3. **Team expected runs** = (Offensive baseline × 0.55) + (Pitcher suppression × 0.45) — this blends how much the offense drives scoring vs how much the pitcher suppresses it
4. **Scale to 5.5 IP for starter**, then add bullpen expectation (see Section 4)

**Combined Runs = Away Expected + Home Expected**

---

## 2. PARK & ENVIRONMENT

Park effects are applied as **multipliers to the combined run estimate**, not additive adjustments.

- **Runs factor**: Use directly. 104 = multiply estimate by 1.04. 96 = multiply by 0.96.
- **HR factor**: Used as a secondary check. If HR factor < 85 AND combined estimate is heavily HR-dependent (both teams Brl% > 8.0), apply an additional -0.3 runs. If HR factor > 115 AND both teams Brl% > 7.0, add +0.3 runs.
- **Stadium dimensions**: Short porches (RF/LF < 315 ft) add +0.2 runs if wind is favorable (see Section 3). Very short porches (< 310 ft) add +0.3. Deep alleys (CF > 410 ft) subtract -0.2.

**Fenway example**: Runs 104 (×1.04), HR 80 (suppresses HRs despite short LF). The Green Monster turns deep flies into doubles, not HRs. With Brl% at 6.6/7.0 (not extreme), no additional HR adjustment. LF 310ft is short but the Monster makes it play deeper for HRs — I treat Fenway as neutral-to-slight-inflate on total runs, not a HR park.

---

## 3. WEATHER

I apply weather adjustments **after** park factor, as additive run modifiers:

**Temperature:**
- < 50°F: -0.4 runs
- 50–59°F: -0.2 runs
- 60–69°F: -0.1 runs
- 70–79°F: 0 runs (baseline)
- 80–89°F: +0.2 runs
- 90°F+: +0.3 runs

**Wind (requires knowing park orientation — I infer from standard MLB park layouts):**

- **Wind OUT to RF/LF** (blowing toward short porch): +0.3 runs per 10 mph above 5 mph. Max +0.9 at 25+ mph.
- **Wind IN from RF/LF** (blowing from outfield toward plate): -0.3 runs per 10 mph above 5 mph. Max -0.9.
- **Wind OUT to CF** (straight away): +0.2 runs per 10 mph above 5 mph. Max +0.6.
- **Wind IN from CF**: -0.2 runs per 10 mph above 5 mph. Max -0.6.
- **Crosswind** (parallel to foul lines): ±0.1 runs depending on which field it favors; generally neutral if truly perpendicular.
- **Dome / roof closed**: No wind effect. Temperature fixed at 72°F. No adjustment.

**Rain chance:**
- > 60%: Mandatory PASS (game integrity risk, potential delay shortening)
- 40–60%: -0.2 runs (slight suppression from humid/heavy air)
- < 40%: No adjustment

**Fenway example**: 81.2°F → +0.2 runs. Wind 20.9 mph S. Fenway faces roughly NE (home plate to CF). A 20.9 mph S wind is roughly blowing from left-center toward right field — somewhat cross, somewhat out to RF. The short RF porch (302 ft) is downwind. I treat this as **wind out to RF at ~15 mph effective** = +0.3 to +0.4 runs. Overcast with 25% rain → no rain adjustment.

---

## 4. PITCHING & BULLPEN

**Starter Quality Gap:**
- Calculate the difference between **AGG xFIP** and **L14 xFIP** for each starter.
- If L14 xFIP > AGG xFIP by 1.0+ runs: Starter is struggling — add +0.4 runs to opponent's expected total.
- If L14 xFIP < AGG xFIP by 1.0+ runs: Starter is hot — subtract -0.4 runs.
- If [sm] on L14: shrink the gap adjustment by 50% (less reliable).

**Stuff+ (Stf+):**
- > 110: Elite stuff, add -0.2 runs to opponent's total (swing-and-miss suppresses contact)
- 95–105: Average, no adjustment
- < 90: Poor stuff, add +0.2 runs

**K-BB%:**
- > 20%: Strong command, -0.2 runs
- 15–20%: Solid, -0.1 runs
- 10–15%: Marginal, no adjustment
- < 10%: Poor, +0.2 runs

**Bullpen Fatigue (post-starter innings ~3.5 IP):**
- Calculate bullpen "freshness score": T1 avail + (T2 avail × 0.5) + (T3 avail × 0.25)
  - TOR: 0 + (1×0.5) + (5×0.25) = 0 + 0.5 + 1.25 = 1.75
  - BOS: 1 + (2×0.5) + (3×0.25) = 1 + 1.0 + 0.75 = 2.75
- Scale: 3.0+ = excellent (league-average bullpen ERA), 2.0–2.9 = good (-0.1 runs), 1.0–1.9 = taxed (+0.3 runs), < 1.0 = exhausted (+0.6 runs)
- Also check if closer has pitched in last 2 days with >15 pitches — if so, and T1 avail = 0, that's a red flag for late-inning leakage.

**Bullpen expected runs** = League average 4.5 runs/9 × (3.5/9) × bullpen fatigue multiplier
- Fresh (3.0+): ×0.95
- Good (2.0–2.9): ×1.0
- Taxed (1.0–1.9): ×1.15
- Exhausted (<1.0): ×1.30

---

## 5. EDGE & STAKING

After computing my **estimated total (E)**, I compare it to the **current posted total line (P)**.

**Edge = |E − P|**

### My Totals Edge Gate
I require a **minimum edge of 1.0 runs** to stake anything on a total. This gate preserves selectivity and avoids paying vig on thin projections.
- **Edge < 1.0 runs:** PASS. No bet, no lean stake.
- **Edge 1.0–1.49 runs:** 1-unit play, contingent on clearing all mandatory pass filters in Section 6.
- **Edge ≥ 1.5 runs:** Eligible for a 3-unit play, but only if the additional 3u conditions below are satisfied.

### My 1u-vs-3u Threshold
Three-unit totals are rare and reserved for high-conviction alignment. To escalate from 1u to 3u, ALL of the following must be true:
1. Raw edge is **≥ 1.5 runs**.
2. Neither starting pitcher carries an **[sm]** flag (I trust the underlying
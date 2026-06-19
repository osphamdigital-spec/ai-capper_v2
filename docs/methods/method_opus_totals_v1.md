# TOTALS METHODOLOGY — opus (self-authored, v1)
# Persistent Over/Under strategy. Authored 2026-06-19 via the totals
# method-authoring round. Applied to every slate alongside the ML/RL method.

# TOTALS METHODOLOGY — [my method, persistent]

**Core philosophy.** I build expected combined runs from the bottom up — each staff's expected runs *allowed* against the opposing offense, summed — rather than guessing a single game number. I anchor on stabilized skill (SIERA/xFIP, season RS/RA) and treat hot/cold form and small samples as nudges, not drivers. The line is the market's estimate; I only act when my number and the line disagree by more than the noise floor.

## 1. RUN ESTIMATION

I compute two scoring blocs (away offense vs home staff; home offense vs away staff) and sum them. Neutral league baseline I use is **4.4 R/team/game (8.8 combined)**.

**(a) Offense Rate** — each team's expected R/G in a neutral park vs the announced starter's hand:

```
OffBase = 0.55×(season RS/G) + 0.25×(L10RS) + 0.20×(4.4 baseline)
Platoon mult = 1 + 0.5×((wRC+ vs hand /100) − 1)   [regressed halfway]
Contact mult = ±3% max, from Brl%/HH% vs league (~8% Brl, ~40% HH)
OffRate = OffBase × Platoon mult × Contact mult
```

I regress the platoon multiplier halfway to 1.0 because lineup wRC+ vs hand is real but noisy over a partial season.

**(b) Pitching Rate** — each staff's expected R/G allowed:

Starter RA9, anchored on stabilized skill:
```
StarterRA9 = 0.55×(AGG SIERA) + 0.20×(season xERA) + 0.15×(season FIP) + 0.10×(L14 SIERA)
```
If L14 is flagged `[sm]`, drop it and redistribute that 0.10 to AGG SIERA. Then a small command/stuff modifier: high K-BB% (≥17%) shaves ~0.10–0.15 off RA9 and lowers variance; a live command red flag (L14 or L3 BB/9 spiking well above the stabilized profile) adds +0.2–0.4, because walks manufacture innings and runs even when the talent grade is fine.

Bullpen RA9 = leverage-weighted ERA of the *fresh* arms (T1 heaviest), plus a fatigue premium when tiers are depleted: roughly **+0.15–0.25 RA9 per missing fresh T1/T2 arm**. A taxed closer/setup means I lean on the worse middle relievers, which pushes the total up.

Expected starter IP from L3 start lengths (typically 5.0–6.1). Each staff covers ~**8.7 team-innings** on average (accounts for the home team not always batting in the 9th and for walk-offs).
```
PitchRate = SP_IP×(StarterRA9/9) + (8.7 − SP_IP)×(BullpenRA9/9)
```

**(c) Combine** — blend offense and defense 50/50 per bloc (the truth sits between "how good is the bat" and "how good is the arm"):
```
AwayRuns = 0.50×OffRate(away) + 0.50×PitchRate(home)
HomeRuns = 0.50×OffRate(home) + 0.50×PitchRate(away)
Raw xR = AwayRuns + HomeRuns
```

## 2. PARK & ENVIRONMENT

I apply the **Runs** factor at **half strength**, because the home team's RS/RA already partly bakes in its own park:
```
Park mult = 1 + 0.5×((Runs − 100)/100)
```
Fenway 104 → ×1.02. I trust the Runs factor over the HR factor for totals — runs is what I'm pricing. The HR factor and dimensions are used to (i) interpret wind (where a short porch is, where the wall eats flies) and (ii) flag extreme parks. A suppressed HR factor with a short LF (Fenway's Monster: HR 80, LF 310) tells me fly balls become wall-doubles, not homers — scoring stays up but is less HR-driven, so I don't over-credit wind-aided carry there.

## 3. WEATHER

Baseline reference temp 70°F. My rules of thumb:

- **Temperature:** ±0.12 combined runs per 10°F off 70. Cold below 50°F bites harder (−0.3+). 81°F → about +0.13.
- **Wind, blowing OUT (toward the outfield):** +0.10 runs per 5 mph *above 5 mph*. 20 mph out ≈ +0.30–0.50.
- **Wind blowing IN:** symmetric negative.
- **Crosswind:** ~neutral on total runs; small HR knockdown (−0.05 to −0.10). I don't manufacture a big edge from a cross.
- **Under ~8 mph:** ignore entirely.
- **Direction requires reasoning per park** (home-plate→CF orientation). Fenway faces ENE, so a strong **S wind** is a left-to-right cross with a mild out-to-LF component — toward the Monster, which converts would-be carry into doubles. I treat that as a *muted* positive (~+0.2), not a clean wind-out boost.
- **Roof closed / dome:** zero out wind, set temp to ~72°F, no weather adjustment.
- **Wind > 25 mph any direction:** variance flag — caps the bet (see §6).
- **Rain ≥ 60–70% / likely delay:** pass (delays scramble bullpens).

## 4. PITCHING & BULLPEN

Stabilized multi-year **AGG SIERA/xFIP is the anchor**; L14 is a nudge and is *ignored when `[sm]`*. Stuff+ and K-BB% refine confidence: high K-BB% both lowers the run estimate and tightens variance (so I'll fire bigger). A divergence between a fine stabilized grade and ugly recent command (walks, short hooks in L3) gets a partial — not full — upward nudge, since command wobble leaks runs but I won't price off a 10-inning sample. Bullpen fatigue is asymmetric and matters late: the staff with fewer fresh high-leverage arms gets the fatigue premium, which is often where Over edges actually come from.

## 5. EDGE & STAKING

Gap = |xR − posted total|.

- **< 0.5 runs:** No bet (noise floor).
- **0.5–0.9:** LEAN.
- **1.0–1.4:** 1 unit.
- **≥ 1.5:** 3 units — *only* if not vetoed by §6 and price is fair.

**Price discipline:** if the best available price on my side is worse than −115, shade every threshold up ~0.2 runs. I won't lay worse than −130 on a total. Plus-money on my side shades thresholds down slightly.

**Line movement as signal:** a total moving ≥0.5 pt, or prices shifting hard one way, is sharp action. If it agrees with my lean, I can upgrade a tier; if the market moved hard *against* my number, I downgrade or pass — they may have weather/lineup info I don't. I bet early to capture CLV when I have a number before the market reaches it; chasing a number the market is already moving toward is negative CLV and I'll pass it.

## 6. WHAT I FADE (regardless of edge)

- Either starter TBD or game postponed → mandatory pass.
- A total driven by a **small-sample starter** (thin AGG IP *and* thin season IP) → cap at LEAN, never 3u.
- **Extreme parks** (Runs factor ≳ 115, e.g. Coors) → cap at LEAN either way; variance too high, and I especially distrust Unders there.
- **Wind > 25 mph** sustained → cap at LEAN; no 3u on a wind-dominated game.
- **Openers / bullpen games** (very short expected SP IP) → confidence capped at LEAN.
- Suspect/stale price on my side → that market is absent; pass that side.
- Respect the daily slate ceiling; a totals bet and a side bet on the same game both count.

---

## Worked example — GAME 1: TOR @ BOS (to show the method produces a number)

- TOR OffRate vs RHP: base 4.19 × platoon 1.065 (wRC+113) × contact 0.98 ≈ **4.37**
- BOS PitchRate (Gray SIERA-anchored ~3.62 RA9, ~6 IP; rested pen ~3.2) ≈ **3.37**
- BOS OffRate vs RHP: base 3.93 × platoon 0.96 (wRC+92) × ~1.0 ≈ **3.77**
- TOR PitchRate (Yesavage AGG-anchored ~3.98 + command bump → ~4.25 RA9, ~5.1 IP; taxed pen ~4.4) ≈ **4.17**
- Raw xR = 0.5(4.37+3.37) + 0.5(3.77+4.17) = 3.87 + 3.97 = **7.84**
- Park ×1.02 → 8.00; temp +0.13 → 8.13; muted S-wind +0.2 → **xR ≈ 8.3**

Posted total 8.5 → edge ≈ 0.2 runs (Under), below the 0.5 noise floor. And the game trips two fade flags anyway (Yesavage small-sample + command volatility; 20.9 mph wind).

```
TOTAL: No bet
TOTAL PRICE: —
TOTAL UNITS: No bet
TOTAL EDGE: 0.2 runs (Under) — below threshold
```

---

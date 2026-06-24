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
1. Either starter is TBD or flagged ⚠ RETURNING STARTER (treat identically to TBD).
2. The best market price is flagged as stale or suspect.
3. The calculated edge is under 4.0 percentage points.
4. A starter is flagged [small sample] and the edge is under 6.0 points (never risking 3 units on small-sample volatility).
5. A starter is flagged [small sample] and the bet is a RUN LINE (not ML). Run line bets require a narrower true-talent range than ML bets. I do not make RL bets on small-sample starters unless velocity/spin/pitch-mix data corroborates the SIERA — verbal reasoning about "the number looks good" is not enough.
6. The game is in an extreme variance environment (e.g., Coors Field) unless the edge exceeds 7.0 points, as the noise overwhelms the signal.

---
## CALIBRATION AUDIT — 2026-06-24 (operator-injected; based on full June season record)

SEASON RECORD TO DATE: 31W–49L across 80 graded bets. Net: −33.3u. ROI: −26%. Win rate: 38.8%.

DIAGNOSIS: My Pythagorean edge model is systematically overconfident. I am generating
edge figures of 13–17+ pts on games that my actual results do not support. A model
producing genuine 65–75% win-probability edges should win at ~65–75%, not 39%. The gap
means my edge numbers are inflated — I am treating SIERA gaps as larger win-probability
signals than the real-world data justifies.

ROOT CAUSES IDENTIFIED:
1. Edge inflation from SIERA gaps: Each 0.50 SIERA advantage currently maps to ~2.5%
   win-probability. Real-world data suggests this coefficient is too aggressive. Market
   prices embed information (injuries, handedness, park, bullpen) that my model is not
   fully capturing — so when I see a 14pt edge, the market is likely correct to price it
   tighter, and I should respect that.
2. Over-betting: I am averaging ~4 bets per slate vs. 2–3 for other models. More bets
   at inflated edges compounds the ROI damage. I need to raise my effective threshold to
   filter to only the clearest, highest-confidence plays.
3. Small-sample amplification: Small-sample SIERA figures (IP < 40) are noisier than
   full-season figures. When I use them at face value, I am injecting noise as if it
   were signal, which inflates edge calculations further.

REQUIRED ADJUSTMENTS (effective immediately):
A. EDGE DISCOUNT: Apply a 30% haircut to any edge calculation where either starter
   is [small sample] OR where the edge is built primarily on a SIERA gap > 2.0 runs.
   A 14pt raw edge becomes ~10pt effective edge after the discount. This gate prevents
   my inflated numbers from generating false 3u signals.
B. BET VOLUME CAP: Limit to a maximum of 3 bets per slate until win rate recovers
   above 45% over a rolling 20-bet window. Prioritise the highest effective edge only.
C. CALIBRATION CHECK: Before submitting any bet, ask: "Does the market price imply
   a win probability within 5pp of my estimate?" If the market implies 55% and I show
   70%, the burden of proof is on me — not the market. Document what specific pre-game
   data justifies the gap. If I cannot name it, downgrade to LEAN or PASS.

TARGET: Return to positive ROI over next 20 bets. If win rate remains below 43% after
20 more graded bets, escalate to a full method rewrite (v2).

---
## METHOD CHANGE — v1.1 (adopted 2026-06-24; evidence from June 12-13 and June 23 slates)
CHANGE ADOPTED: Cap L14 stat influence. When estimating a starter's true-talent
level, weight full-season AGG metrics at minimum 2:1 over L14 metrics. L14 stats
may only shift the edge estimate by a maximum of 50% of the raw AGG-based value.
Exception: only override this cap when corroborating structural evidence exists
(documented velocity change, new pitch, documented injury return, or consistent
30+ day trend — not a single bad/good stretch).
EVIDENCE: Named independently by DeepSeek, Sonnet, Qwen across June 12-13 slates
AND confirmed again June 23 (McClanahan 4.00 SIERA [small sample] used for TB RL
bet → 12-run KC blowout; no velocity/spin corroboration existed pre-game).
CONFIDENCE: HIGH — same failure mode on three separate slates.
STATUS: ADOPTED — replace v1.1 candidate.
---
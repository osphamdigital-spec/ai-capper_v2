**Handicapping Method — Independent System**

I estimate true win probability by projecting each team’s runs scored and allowed, then apply Pythagorean expectation. My edge comes from synthesizing pitching true talent, platoon-adjusted offense, and bullpen freshness. I only bet when the gap to market implied probability is ≥4 percentage points.

**Weighing & Distrust**
- **Starting Pitcher**: The core driver. I blend 50% aggregate xFIP/SIERA (large sample) with 50% L14 xFIP (if ≥10 IP, else downweight). Surface ERA ignored. Small-sample flag (slate note) excludes 3-unit bet and reduces projection weight. Stf+ used only as a tiebreaker.
- **Bullpen**: I score availability (high-leverage arms fresh: yes/no/taxed) and quality (regress extreme ERAs). A tired or leaky unit subtracts 0.2–0.4 runs from projected opponent runs. Closer blowups are distrusted if peripherals okay.
- **Offense**: Base is team wRC+ vs starter handedness (platoon splits). Recent L10 form (RS, Brl%, HH%) adjusts baseline ±5%. Apply park factor (and +0.5 runs for Coors). Missing lineups → I assume average if regulars healthy.
- **Weather**: Only adjust for extreme wind (>15 mph in/out) or rain that may truncate game. Unavailable weather → no adjustment; too risky → pass.
- **Line Movement**: Not used for projection. I note if the market moved against me, but I trust my process over steam.

**Projecting Runs**
- Offense factor = (wRC+ / 100) × recent form bump.
- Pitching factor = (pitcher projected ERA / lgAvg ERA) × bullpen multiplier. Bullpen multiplier: 1.0 if fresh, 1.05 if taxed, 1.10 if 0 fresh high-leverage arms.
- Team runs = (lgAvg runs × park factor) × (own offense factor / opponent pitching factor).
- League average runs ~4.4, adjusted for park.

**Win Probability & Edge**
- Pythagorean: Win% = RS^1.83 / (RS^1.83 + RA^1.83).
- Devig the best ML for implied probability; gap = my estimate – market.
- Bet only if gap ≥4 pts. Stake: 1 unit for 4–6.99 pts; 3 units for ≥7 pts with clean data (no small-sample starter, no suspect prices, no bullpen chaos).

**Pass Triggers**
- TBD starter, price flagged suspect, or weather missing with known storm → PASS.
- Under 4% edge → LEAN or PASS.
- If both bullpens heavily taxed or multiple uncertain factors, I pass even if gap exists.

**Portfolio Management**
- Respect slate ceiling. I do not chase volume. A slate with 0 bets is acceptable if no strong edge surfaces.
# Method Document — "Skill-Over-Story" MLB Handicap

## Core philosophy
The market prices reputation and recent results efficiently; it prices *pitcher skill drift* and *bullpen state* less efficiently. My edges come almost entirely from (1) gaps between a starter's ERA narrative and his underlying skill (xFIP/SIERA/K-BB%/Stf+), and (2) same-day bullpen availability, which morning lines rarely fully reflect.

## Baseline build (per game)
1. Start at 50/50, adjust for home field (+3.5 pts to home team).
2. **Starter skill delta** (heaviest weight): Compare AGG xFIP/SIERA and K-BB% — not ERA. A full-run SIERA gap ≈ 4-5 pts of win probability. Stf+ is my tiebreaker; under 90 is a red flag regardless of ERA. L14 form modifies ±1-2 pts only when IP ≥ 10 and it confirms/contradicts the AGG read. I explicitly distrust: shiny ERAs sitting on bad xERA/HH%/Brl% (regression coming), and W-L records entirely.
3. **Bullpen state** (second weight): Season pen ERA sets the base; the "high-leverage arms fresh" count is the live signal. 0-of-3 fresh vs 3-of-3 fresh is worth 2-3 pts, more in projected close games. A taxed closer matters most in games priced near pick'em.
4. **Offense vs. starter hand**: Use platoon wRC+ vs. the actual hand, weighted with L10 RS and Brl%/HH%. wRC+ gap of 15+ ≈ 1.5-2 pts. I distrust L10 W-L records and run differential as standalone signals — rdiff informs only when it contradicts the line badly.
5. **Park/weather**: Park factor and wind/heat adjust totals leans, not sides, unless extreme. wx:unavailable = no total bet that game.

Sum adjustments, cap any single game estimate at 65/35 — if my number says more, I assume I'm missing something the market knows.

## Conversion & comparison
Convert market ML to implied probability after removing vig (average both sides' implied, scale to 100%). My estimate minus de-vigged implied = edge. Bet only at the best available non-flagged price; the gap is measured against the price I'd actually take.

## Automatic passes
- TBD starter, postponed, or stale price on my side.
- [small sample] starter on BOTH key inputs (no L14, <20 IP season) — I'll bet *against* small-sample starters but rarely on them.
- Coors sides at short prices — variance eats the edge; totals lean only.
- My edge depends mainly on a hot/cold L10 record — that's the market's trap, not mine.
- Anything where my estimate moved >8 pts off market without a concrete mechanism I can name in one sentence (usually means I double-counted).

## Discipline
Most days: 0-1 bets. 3 units only when starter skill delta AND bullpen state point the same direction with clean data. Parlays only when both legs derive from unrelated mechanisms; default is none.
# MY MLB HANDICAPPING METHOD
<!-- v2 (2026-06-15): integrated self-proposed L14 small-sample discount. Promoted after recurring across June 12-13 post-mortems with pre-game evidence. Supersedes v1 (retained as history). -->

## Core Philosophy
I am looking for mispriced win probability, not narrative. The market is sharp. I need a specific, quantifiable reason the book is wrong before I commit a unit.

---

## Step 1: Hard Filters (Pre-Analysis)
Before touching any data, I auto-PASS:
- Either starter TBD
- Price flagged stale/suspect on the side I'm evaluating (treat that line as absent)
- Postponed games
- Small-sample starter flag blocks any 3-unit play on that game

These are non-negotiable. No exceptions for "good stories."

---

## Step 2: Starter Quality — My Anchor Weight (~40% of my edge estimate)
I build my pitcher assessment in this priority order:
1. **AGG xFIP/SIERA** — career-stable baseline (primary anchor)
2. **L14 xFIP/SIERA** — recent process quality, weighted by IP sample size (see table below)
3. **Stf+** — stuff quality independent of outcomes
4. **L3 game log** — workload and command trends (BB/9 spiking = red flag)

I distrust ERA and W-L entirely. I distrust xERA on small samples.

**L14 Sample Weighting:**
| L14 IP | L14 weight | AGG weight |
|--------|-----------|------------|
| ≥35 IP | 60% | 40% |
| 20–34 IP | 70% | 30% |
| 11–19 IP | 40% | 60% |
| <11 IP | anecdotal only — treat as AGG-only, note direction |

When L14 and AGG diverge sharply at low IP, the divergence is noted but does not override AGG. A single hot or cold stretch below 11 IP is noise.

---

## Step 3: Bullpen Assessment (~25% of edge estimate)
I look at:
- Season ERA as a baseline
- High-leverage arms available (fresh vs. taxed)
- Taxed arms in last 2 days flagged in the data

A bullpen with 0-of-3 fresh high-leverage arms is treated as a half-run ERA penalty. Closer ERA above 6.00 adds further discount. I do not over-weight single-game usage unless the arm threw 30+ pitches.

---

## Step 4: Offense and Platoon (~20%)
- wRC+ vs. relevant handedness tells me lineup-level threat
- L10 RS shows recent offensive temperature
- Barrel% and HH% confirm quality of contact, not luck
- I don't chase hot streaks unless underlying contact metrics support them

---

## Step 5: Contextual Factors (~15%)
- **Park**: I apply Coors altitude adjustment aggressively; HR factor matters for run-line decisions
- **Weather**: Wind 12+ mph out toward CF adds ~0.3 runs to my total estimate; rain/thunderstorm risk flags postponement
- **Line movement**: Movement against a team is a soft warning; I won't bet against sharp steam without strong independent conviction

---

## Step 6: Win Probability Conversion
I assign each starter a "true ERA" estimate by blending L14 and AGG xFIP using the IP-sample weighting table from Step 2. I run both true ERAs through a simple run-expectancy framework using park factor and bullpen ERA to produce a projected run differential, then convert to win probability via a log5-style approximation. I compare to market implied probability (from American odds, vig-removed). Gap must clear 4 points to bet.

---

## Step 7: Bet Sizing and Slate Ceiling
- 4–6.9 pt gap → 1 unit
- 7+ pt gap, clean data (no small-sample flags, no stale prices on bet side) → 3 units
- Slate ceiling is enforced hard; I rank qualifying bets by gap size and cut at the ceiling

---

## What Makes Me Pass
- Gap under 4 points regardless of how much I "like" the team
- Any material data integrity issue on my bet side
- Coors Field totals with stale prices — too much variance, no reliable market anchor
- Strong line movement against my side with no data explaining why
- Both starters mediocre and bullpens roughly equal — market is probably right

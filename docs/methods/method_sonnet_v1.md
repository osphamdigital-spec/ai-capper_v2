# MY MLB HANDICAPPING METHOD

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
1. **L14 xFIP/SIERA** — recent process quality, not results
2. **AGG xFIP/SIERA** — career-stable baseline
3. **Stf+** — stuff quality independent of outcomes
4. **L3 game log** — workload and command trends (BB/9 spiking = red flag)

I distrust ERA and W-L entirely. I distrust xERA on small samples. When L14 and AGG diverge sharply, I weight L14 at 60% if it's 10+ IP; otherwise I regress toward AGG.

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
I assign each starter a "true ERA" estimate blending L14 and AGG xFIP (60/40 if L14 is 10+ IP, otherwise 30/70). I run both true ERAs through a simple run-expectancy framework using park factor and bullpen ERA to produce a projected run differential, then convert to win probability via a log5-style approximation. I compare to market implied probability (from American odds, vig-removed). Gap must clear 4 points to bet.

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

---
## CANDIDATE METHOD CHANGE — v1.1 (proposed 2026-06-14, 2-slate evidence)
PROPOSED CHANGE: Cap L14 stat influence. When estimating a starter's true-talent
level, weight full-season AGG metrics at minimum 2:1 over L14 metrics. L14 stats
may only shift the edge estimate by a maximum of 50% of the raw AGG-based value.
Exception: only override this cap when corroborating structural evidence exists
(documented velocity change, new pitch, documented injury return, or consistent
30+ day trend — not a single bad/good stretch).
EVIDENCE: Named independently by DeepSeek, Sonnet, Qwen across June 12-13 slates.
All three 0-3 DeepSeek losses, Sonnet's oversized best-bet, and Qwen's McLean
concern all traced to the same root: L14 outliers treated as signal without
full-season anchoring.
CONFIDENCE: MEDIUM (2 slates, 3 models, pre-game evidence cited)
STATUS: CANDIDATE — not yet adopted. Promote to v2 if it recurs or shows CLV
improvement over next 10+ bets for these models.
---
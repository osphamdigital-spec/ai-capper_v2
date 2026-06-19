# MY MLB HANDICAPPING METHOD
<!-- v3 (2026-06-15): staking rules now self-authored. Removed house edge gate, slate ceiling, and unit map. Replaced with own calibrated thresholds and explicit reasoning. All other handicapping logic retained from v2. -->

## Core Philosophy
I am looking for mispriced win probability, not narrative. The market is sharp. I need a specific, quantifiable reason the book is wrong before I commit a unit. My objective is long-term, risk-adjusted bankroll growth measured against closing line value. A bet that loses but beats the closing line is a good bet. A bet that wins but chases a story is a liability.

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
I assign each starter a "true ERA" estimate by blending L14 and AGG xFIP using the IP-sample weighting table from Step 2. I run both true ERAs through a simple run-expectancy framework using park factor and bullpen ERA to produce a projected run differential, then convert to win probability via a log5-style approximation. I compare to market implied probability (from American odds, vig-removed). The resulting gap in percentage points drives bet qualification and sizing under my self-authored staking rules below.

---

## Step 7: Staking Rules (Self-Authored — v3)

### 7A. Edge Gate

**Sides (ML and RL):** Minimum gap of **5 percentage points** between my vig-removed win probability estimate and the market implied probability. I am raising this from the former house minimum of 4 points for the following reason: at 4 points the signal-to-noise ratio is too low given the known sources of error in my model — bullpen state inference, park factor approximations, and L14 sample instability. I want the gate to sit above my typical model error band, not inside it. A 5-point minimum is still reachable on clear edges while filtering out the marginal cases where I am essentially coin-flipping with vig dragging me down.

**Totals (Over/Under):** Minimum gap of **0.4 runs** between my projected total and the posted line (vig-removed). This is restated here from my totals method for completeness. Totals carry more weather and bullpen-availability variance than sides; 0.4 runs represents the threshold at which my projection is meaningfully distinct from the market rather than just within rounding error.

### 7B. Slate Ceiling

**I set a ceiling of 3 bets per slate, total.** Sides and totals count toward the same shared limit. There is no separate ceiling for each market type.

**Reasoning:** A unified ceiling enforces genuine prioritization. If I have found two strong side edges and a strong total edge on the same slate, I must choose among them — I cannot simply add the total as a free fourth bet by pretending it lives in a separate bucket. This prevents the ceiling from becoming meaningless. Three bets is enough to express differentiated conviction on any realistic slate while keeping daily risk exposure bounded. On a very large slate I may qualify four or five games; forcing myself to cut to three means only the three highest-gap plays get action, which is exactly the discipline I want.

When qualifying bets exceed the ceiling, I rank by gap size and take the top three. In the event of a tie in gap size, I prefer the bet with cleaner data integrity (no small-sample flags, no line movement warnings).

### 7C. Unit Threshold (1u vs. 3u)

- **Gap 5.0–8.9 pts (sides) / 0.4–0.69 runs (totals):** 1 unit
- **Gap 9.0+ pts (sides) / 0.70+ runs (totals), AND all of the following conditions met:** 3 units

**Conditions required to unlock 3 units:**
1. No small-sample starter flag on either side of the game
2. No stale or suspect price on the bet side
3. No strong unexplained line movement against my position
4. My projected gap is driven by at least two independent model components (e.g., starter edge AND bullpen edge, not a single fragile input)

If the gap clears the 3u threshold numerically but any one of the four conditions is not met, the bet reverts to 1 unit. It does not get passed — a 9-point edge is still a bet — it is simply not a bet I trust enough to triple.

**Reasoning behind the higher 3u threshold (9 pts vs. former 7 pts):** Under the former house rules, 7 points unlocked 3 units. I am raising that to 9 points because the 3u level represents a meaningful fraction of real bankroll and the four conditions above add a qualitative gate on top of the numerical one. I want genuine high-conviction outliers at 3u, not routine strong edges. The account history block I receive before each slate will let me monitor whether my 3u bets are generating disproportionate positive return over time; if the sample grows large enough and 3u bets are underperforming 1u bets on a CLV-adjusted basis, I will revisit the threshold downward.

**Best Bet designation:** My single highest-gap qualifying play that also meets all four 3u conditions is designated Best Bet. If no play meets all four conditions, no Best Bet is declared for that slate. I will not force a Best Bet.

---

## Step 8: What Makes Me Pass
- Gap under 5 points (sides) or under 0.4 runs (totals) regardless of how much I "like" the team or game
- Any material data integrity issue on my bet side
- Coors Field totals with stale prices — too much variance, no reliable market anchor
- Strong unexplained line movement against my side
- Both starters mediocre and bullpens roughly equal — market is probably right
- Slate ceiling already reached at higher-gap plays

---

## Step 9: Bankroll Context and History Interpretation

My starting balance is $10,000. 1 unit = $100 base on a to-win convention. I receive my own account history before each slate. I treat this history as informational, not directive, for the following reasons:

**Small-sample discipline:** Fewer than 50 settled bets is an unreliable sample for method evaluation. I will not adjust my edge gate, unit threshold, or slate ceiling based on a record of 15 or 20 bets. Variance over a short run tells me almost nothing about whether my model is calibrated. The correct response to a 3-12 start is to examine whether my process was sound on each bet, not to tighten or loosen my gate in reaction to outcomes.

**CLV is my primary signal:** The most useful number in my history block is average CLV. If my bets are consistently beating the closing line, my process is working even if short-run results are negative. If CLV is consistently negative, my model is finding prices the market will sharpen against me, and that warrants a genuine process review — not just a staking adjustment.

**Leaderboard gap:** I note my rank and the gap to the leader. I will not change my method to chase the leader. Leaderboard position over a short sample is dominated by variance and bet volume. I am optimizing for long-run risk-adjusted return, not current-slate rank.

**Trigger for genuine method review:** If, after 100+ settled bets, CLV is negative on a bet type (e.g., consistently negative CLV on favorites, or on 3u bets), I will audit that category and consider structural revision. Below 100 bets, adjustments to the method require pre-game evidence — a flaw in the handicapping logic itself — not ex-post outcome patterns.
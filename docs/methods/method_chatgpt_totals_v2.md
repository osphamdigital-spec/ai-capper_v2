# TOTALS METHODOLOGY — chatgpt (self-authored, v3)
# Persistent Over/Under strategy. Revised for independent totals staking.
# Applied to every slate alongside the ML/RL method.

# 1. RUN ESTIMATION

I start with a neutral scoring baseline built from each team's season-long ability to score and prevent runs, then adjust for matchup quality, environment, and pitching availability. The goal is not to chase every perceived misprice, but to build a total from several independent inputs and only bet when the gap from market is meaningful.

### Step 1: Team Run Expectation

For each offense:

Expected Team Runs =
(Team RS + Opponent RA) ÷ 2

Example:

TOR expected runs =
(TOR RS + BOS RA) ÷ 2

BOS expected runs =
(BOS RS + TOR RA) ÷ 2

Combined Total =
Away Expected Runs + Home Expected Runs

This is the base of the projection and carries the most weight before adjustments.

### Step 2: Offensive Quality Adjustment

I adjust each team expectation using:

* Platoon wRC+ versus starter handedness
* Team Brl%
* Team HH%
* L10RS

Guidelines:

* wRC+ 110–119: +0.2 runs
* wRC+ 120+: +0.4 runs
* wRC+ 90–99: -0.2 runs
* wRC+ <90: -0.4 runs

L10RS:

* ≥1 run above season RS: +0.2
* ≥1 run below season RS: -0.2

Brl% and HH% matter most when they agree:

* Top-tier contact profile: +0.1 to +0.2
* Weak profile: -0.1 to -0.2

I do not overreact to one hot week. Recent form can tilt the estimate, but sustained skill indicators matter more than short-term scoring noise.

### Step 3: Run Differential Context

Run differential is a stability filter, not a primary engine of the total.

* Strong positive differential: +0.1
* Strong negative differential: -0.1

Maximum adjustment: ±0.2 runs

This helps distinguish a legitimately solid team profile from a misleading RS/RA split created by sequencing or schedule noise.

---

# 2. PARK & ENVIRONMENT

Park effects modify the combined run projection after team and pitching context are established.

### Runs Factor

* 95–99: -0.1 to -0.3 runs
* 100–104: neutral
* 105–109: +0.2 to +0.4 runs
* 110+: +0.5 to +0.8 runs

### HR Factor

HR factor matters most around key totals where one extra homer changes the entire scoring shape.

* HR 90–94: -0.1
* HR <90: -0.2 to -0.4
* HR 106–110: +0.1 to +0.3
* HR >110: +0.3 to +0.5

### Stadium Dimensions

Dimensions act as secondary modifiers.

Examples:

* Short RF/LF (<325 ft): small Over boost
* Deep power alleys (>385 ft): small Under boost
* Extremely asymmetric parks: higher variance, not automatically more runs

Maximum dimensions adjustment:
±0.3 runs

I treat park as an amplifier, not a standalone reason to bet a total.

---

# 3. WEATHER

Weather is often the largest non-pitching total adjustment, especially in open-air parks.

### Temperature

Below 60°F:
-0.2 to -0.5 runs

60–75°F:
Neutral

76–85°F:
+0.2 to +0.4 runs

86°F+:
+0.4 to +0.8 runs

### Wind

I evaluate wind by direction, strength, and how it interacts with the stadium.

#### Wind Out

5–10 mph:
+0.2 runs

11–15 mph:
+0.4 runs

16–20 mph:
+0.7 runs

20+ mph:
+1.0 run

#### Wind In

5–10 mph:
-0.2 runs

11–15 mph:
-0.5 runs

16–20 mph:
-0.8 runs

20+ mph:
-1.2 runs

#### Crosswind

Usually:
±0.0 to ±0.2

Unless paired with unusual park geometry.

### Rain

Light rain probability alone does not change the projection.

Delay risk increases volatility and lowers confidence. A delay can shorten a starter outing or create bullpen chaos, so weather risk affects staking even when the raw run estimate is unchanged.

### Dome / Roof Closed

Ignore weather entirely.

---

# 4. PITCHING & BULLPEN

## Starting Pitchers

I use a blended starter evaluation with skill first and recent form second.

Priority:

1. AGG xFIP/SIERA
2. Current-season FIP/xERA
3. K-BB%
4. Stuff+
5. L14
6. L3

### AGG Baseline

AGG metrics are the anchor.

AGG xFIP/SIERA:

<3.40:
-0.4 to -0.7 runs

3.40–3.80:
-0.2 to -0.4

4.20–4.60:
+0.2 to +0.4 runs

>4.60:
+0.4 to +0.8 runs

### Stuff+

95–104:
Neutral

105–110:
-0.1

111–120:
-0.2

120+:
-0.3

Below 95:
+0.1 to +0.3

### K-BB%

20%+:
Under leaning

15–20%:
Mild Under

10–15%:
Neutral

Below 10%:
Over leaning

### L14 Form

L14 can refine the estimate but does not override the longer-sample skill base.

Difference between AGG and L14:

±0.2 to ±0.5 run modifier

If sample quality is weak, I cut that weight roughly in half.

### Contact Quality Allowed

HH% and Brl% allowed:

Strong suppression:
-0.1 to -0.3

Poor suppression:
+0.1 to +0.3

If a pitcher shows weak underlying contact suppression and a low strikeout floor, I am more willing to price in crooked-inning risk.

---

## Bullpen

Bullpen state matters because totals are often won or lost after the starters leave.

### Availability Tiers

Fresh bullpen:

T1 full
T2 full
T3 mostly available

Adjustment:
-0.2 to -0.5

Average bullpen:

Neutral

Taxed bullpen:

Missing multiple T1/T2 arms

Adjustment:
+0.3 to +0.8

### Usage

Recent outings:

25+ pitches previous day:
Likely unavailable

20+ pitches multiple times in last 3 days:
Fatigue penalty

If both bullpens are taxed:

+0.5 to +1.0 runs

I care more about reliever availability than season-long bullpen ERA. Totals are highly sensitive to who can actually pitch tonight, not just to the generic quality label attached to the bullpen.

---

# 5. EDGE, STAKING & SLATE INTEGRATION

After all adjustments:

Projected Total =
Base Total + Offense + Pitching + Bullpen + Park + Weather

### Edge Calculation

Edge =
Projected Total − Posted Total

Positive edge favors the Over.
Negative edge favors the Under.

## Staking Philosophy

Totals are more fragile than they first appear. Bullpen usage, late weather confirmation, lineup scratches, and market efficiency around obvious weather spots all make small projected gaps less trustworthy than they look on paper. Because of that, I want a real cushion over the number before risking bankroll.

I also receive my own running results history, but I will not overfit to a handful of wins or losses. Small samples in totals are noisy. Threshold changes should come from sustained evidence, not a short streak.

## Totals Edge Gate

My minimum actionable totals edge is **0.8 runs**.

That means:

* **<0.5 runs:** No bet
* **0.5 to 0.7 runs:** Lean only
* **0.8+ runs:** Eligible for a wager

Reasoning:
A sub-0.8 run discrepancy is usually too thin once vig, lineup uncertainty, bullpen volatility, and late market correction are accounted for. I would rather pass than force marginal totals.

## 1-Unit vs 3-Unit Threshold

### 1 Unit

**0.8 to 1.5 runs** = standard playable edge

This is my default bet size for totals. Most legitimate totals positions belong here.

### 3 Units

**1.6+ runs** = candidate for a 3-unit wager, but only if all of the following are true:

* Confirmed starters
* No major lineup uncertainty
* No severe weather uncertainty or meaningful delay risk
* At least **three independent drivers** support the same side of the total
  * typically some combination of starter quality, bullpen state, platoon offense, and environment
* The edge is not built primarily on one volatile assumption
* Market has not moved so far that the available number is materially worse than the one that created the edge

### Extra Caution in Extreme-Variance Environments

In unusually volatile scoring environments, I require more than the baseline 3u threshold.

Examples:

* Very strong wind
* Coors-type run environment
* Bullpen game or opener uncertainty
* Multiple unstable or short-leash pitchers
* Delay risk that could disrupt starter usage

In those spots, **1.6 to 1.9 runs is usually still only 1 unit**, and I generally want **2.0+ runs** plus clean confirmation before going to 3 units.

Reasoning:
A large raw edge in a chaotic run environment is less reliable than the same edge in a stable game state. I reserve 3u totals for situations where both the number and the underlying structure are strong.

## Slate Ceiling Interaction

Totals do **not** get a separate ceiling.

They count against the **same unified slate ceiling** defined in my main sides method.

If I bet:

* one side and one total on different games, both count
* one side and one total on the same game, **both still count**

I treat each staked market as real exposure on the bankroll. Same-game side/total combinations can be correlated, so they do not receive special treatment or a free extra slot. If both markets on one game are attractive, each must stand on its own merit.

### Market Movement

I use movement as confirmation, not as the core projection.

#### Supports Position

Movement toward my side:
Confidence increases

#### Opposes Position

Movement against my side:
Re-check assumptions, weather, bullpen availability, and lineups

#### Significant Moves

A 0.5-run move or major juice shift can change staking confidence by one tier, but it does not create a bet by itself.

---

# 6. WHAT I FADE

Automatic or near-automatic pass situations:

### TBD Starter

Mandatory pass.

### Severe Data Uncertainty

* Small-sample starter with limited trustworthy innings
* Incomplete bullpen availability
* Meaningful lineup ambiguity
* Uncertain weather inputs

### Extreme Weather

* Forecast likely to cause delays
* Swirling or unstable wind patterns that are hard to model

### Contradictory Signals

Examples:

* Elite pitching but extreme Over weather
* Weak offenses but badly taxed bullpens
* Park suppresses runs but both starters project for short outings

If the projected edge exists but confidence in the mechanism is low, I pass.

### Extreme-Variance Environments

Games where scoring distribution becomes abnormally wide due to:

* Very strong wind
* Coors-like conditions
* Multiple unstable pitchers
* Bullpen-game structures

These require materially larger edges, especially for 3u.

### Poor Market Number

If only stale or suspect prices are available, that totals market is absent for me.

---

# 7. FINAL DECISION RULE

My totals projection is driven primarily by:

1. Team scoring/prevention baseline
2. Platoon offensive strength
3. Starting pitcher quality
4. Bullpen availability
5. Weather
6. Park effects
7. Market confirmation

I bet totals only when multiple independent factors align in the same direction. Single-factor edges are usually not enough. My objective is not to predict every total more accurately than the market, but to isolate the subset of games where my projected run environment differs enough from the posted number to justify risk with disciplined staking.
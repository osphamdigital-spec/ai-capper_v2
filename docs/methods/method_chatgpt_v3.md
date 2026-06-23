My card remains side-first and price-sensitive. I build each game from expected run share, not narrative. My objective is long-term, risk-adjusted bankroll growth with an emphasis on beating the close. Default action is PASS.

1) Starter foundation

I begin with the starting pitchers and use a weighted pitching grade:

- 45% skill base: xFIP, SIERA, K-BB%, Stuff+
- 35% contact risk: xERA, HH%, Barrel%
- 20% recent shape: last 14 days and last 3 starts, only as a modifier

I treat ERA and pitcher W-L as mostly noise. If current ERA disagrees sharply with xFIP/SIERA/xERA, I trust the estimators over the ERA. For small-sample starters, I lean heavily on aggregate skill and treat uncertainty as a stake suppressor; those games are never 3-unit plays.

Small-sample confidence haircut on totals (added v4, promoted 2026-06-21): when a total's edge is driven primarily by one or both starters carrying a small-sample flag, the run projection is built on an unstable input, so I (a) apply a confidence haircut to my projected total — pulling it back toward the market number before measuring the gap — and (b) require a larger run-edge to act than my normal totals gate (see 7A). A small-sample starter makes the run distribution wide; a point-estimate edge that looks bettable at full size is usually one fragile assumption carrying the whole thesis. I would rather pass a real edge than stake a noisy one at full conviction.

2) Offense through platoon context

Team wRC+ versus the starter’s handedness is the backbone of the offensive adjustment. Named hitters matter most when the aggregate team profile is close. Barrel% and hard-hit% are confirmation tools, not primary drivers. I do not chase recent scoring unless it is supported by contact quality and matchup fit.

3) Bullpen and late-game equity

Bullpen adjustment is essential. I grade bullpens by underlying quality and by the freshness of the actual leverage arms likely to decide the game. “Top relievers unavailable or gassed” matters more than season bullpen ERA. A strong starter edge gets downgraded if his bullpen is compromised and the opponent’s leverage group is fresh.

4) Park and weather

- Coors gets a major volatility adjustment; I avoid run lines there.
- Wind and heat matter only when direction and strength clearly support the run environment.
- If weather is unavailable or unreliable, I avoid totals and keep side confidence modest.

5) Market step and price discipline

I compare my fair price to the best available non-suspect number, not to the market median. Stale or suspect books are ignored. I prefer moneylines. I use run lines only when my projected run gap is meaningfully larger than the market’s and the park suppresses variance enough to justify the extra condition.

6) Probability conversion

I project team runs from starter, offense, bullpen, and park/weather adjustments, then convert projected runs to win probability with a Pythagorean-style win expectation. I lightly regress toward the market to reduce overfitting. I am not trying to outsmart the entire market on every game; I am trying to isolate the places where my number still clears the available price after that regression.

7) Staking discipline — v4

A) Edge gate

- Sides (ML or RL): minimum edge = 3.5 percentage points over implied probability.
- Totals (Over/Under): minimum edge = 0.7 runs versus the posted total, as determined by my separate totals process. When the edge is driven primarily by a small-sample starter, this gate rises to 1.0 runs (after the confidence haircut described in section 1), reflecting the wider run distribution behind an unstable starter projection.

Reasoning: I want a gate high enough to clear normal model error and market noise, but not so high that I only create a tiny sample of bets that is hard to evaluate from my own history. My process already filters aggressively through starters, platoons, bullpens, park, weather, and price quality, so a 3.5-point side gate is selective without being paralyzing. For totals, 0.7 runs is the minimum margin where I believe the number is meaningfully different from the market rather than just model jitter.

B) Slate ceiling

- Maximum 3 bets per slate.
- This is a combined ceiling across both markets: sides and totals count toward the same limit.

Reasoning: My edge is strongest in concentration, not volume. A combined cap prevents me from stacking correlated exposure or forcing action just because a slate is large. If more than three bets qualify, I keep the three with the cleanest model-to-price gap, the least lineup/weather fragility, and the strongest expected CLV profile.

C) 1-unit vs 3-unit threshold

- 1 unit:
  - Sides with edge from 3.5 to 6.9 percentage points
  - Totals with edge from 0.7 to 0.99 runs
- 3 units:
  - Sides with edge of 7.0+ percentage points
  - Totals with edge of 1.0+ runs
  - And only when the handicap is clean across the major components: starter edge, platoon context, bullpen/freshness, and park/weather all support the bet with no major fragility flag

Automatic 1-unit downgrade even if raw edge qualifies for 3 units:

- small-sample starter
- lineup-sensitive game where one or two key bats materially swing the projection
- bullpen freshness uncertainty
- weather uncertainty
- edge driven mostly by one noisy input, such as recent form or ERA luck
- volatile environment that increases distribution width more than my model confidence, even if the mean shows value

Reasoning: 3-unit bets should be rare, multi-angle mispricings, not merely “my biggest number.” The account report separates 1-unit and 3-unit results, so this threshold is something I can actually audit over time. I want 3-unit bets to represent my best-priced, best-supported positions, not my mood or my place on the leaderboard.

D) Best bet

- Best bet = my single highest-conviction 3-unit play.
- If there is no qualifying 3-unit play, there is no best bet.

8) Automatic passes

I pass automatically when:

- a starter is TBD
- the game is postponed
- the available market is stale or suspect
- the edge is created mainly by recent form, ERA luck, or other noisy short-term signals
- signals conflict and I have no clear bullpen or platoon separator
- the matchup is highly lineup-sensitive and key bats are unconfirmed
- the favorite price demands too much perfection for the quality of the edge

9) Bankroll and feedback discipline

I start from a real bankroll and treat every stake as real exposure. I do not chase losses, press because I am behind on the leaderboard, or tighten up simply because I am ahead. Short samples can mislead; CLV matters more than a 10- or 20-bet win rate.

I use my account-history report mainly to audit:

- whether my 3-unit bets are actually outperforming my 1-unit bets in price quality and CLV
- whether a bet type is producing consistently poor CLV, which is more actionable than short-run W-L
- whether I am staying selective enough to avoid thin, forced action

I do not change my gates or stake thresholds on a tiny sample. Until I have a meaningful body of settled bets, the right conclusion from the history may simply be “draw no conclusion.”

10) Final operating principle

Default action is PASS. I want a small card of prices I would still respect near the close. My method is built to win on process before it wins on variance: solid projection inputs, disciplined price comparison, limited slate exposure, and 3-unit aggression only when both the number and the shape of the matchup are unusually clean.
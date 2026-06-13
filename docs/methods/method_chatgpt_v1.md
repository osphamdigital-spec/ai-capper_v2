My card is side-first and price-sensitive. I build each game from expected run share, not narrative.

1) Start with the starters. I use a weighted pitching grade:
- 45% skill base: xFIP, SIERA, K-BB%, Stuff+
- 35% contact risk: xERA, HH%, Barrel%
- 20% recent shape: last-14 and last-3, but only as a modifier
I treat ERA/W-L as mostly noise. If a pitcher’s current ERA disagrees sharply with xFIP/SIERA/xERA, I fade the ERA. For small-sample starters, I lean almost entirely on aggregate skill and cap at 1 unit.

2) Add offense through platoon context. Team wRC+ vs the starter’s handedness is the backbone; listed key bats matter only when the team aggregate is close. Barrel%/hard-hit% are used as confirmation, not primary drivers. I do not overreact to L10 runs unless it matches contact quality.

3) Bullpen adjustment is essential late-game equity. I grade pens by season quality plus freshness of actual high-leverage arms. “0 of 3 fresh” matters more than raw bullpen ERA. A strong starter edge is downgraded if his bullpen is taxed and the opponent’s leverage group is fresh.

4) Park/weather adjustment:
- Big upgrade to totals volatility and underdog upset risk at Coors; I avoid RLs there.
- Wind/heat only matter if direction/speed clearly support run environment.
- If weather is unavailable, I avoid totals and keep side confidence modest.

5) Market step. I compare my fair ML to the best available non-suspect price, not the median. Stale/suspect books are ignored. I prefer MLs; RLs only when my projected run gap is large and the park suppresses variance.

Probability conversion:
I project team runs from starter + offense + bullpen + park/weather adjustments, then convert projected runs to win probability with a Pythagorean-style win expectation, lightly regressed toward market to avoid overfitting. I only bet when my final win probability exceeds implied probability by 4+ points.

Automatic passes:
- TBD/postponed/suspect market
- Edge created mainly by recent form or ERA luck
- Conflicting signals with no clear bullpen or platoon separator
- Unconfirmed lineup-sensitive games where a few key bats drive the matchup
- Any favorite requiring too much perfection at a bad price

Default action is PASS. I want few bets, clear edges, and prices I’d still like near close.
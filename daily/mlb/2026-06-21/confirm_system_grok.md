# LINEUP CONFIRM-CHECK — SYSTEM INSTRUCTIONS
# MLB  2026-06-21  model: grok

Lineups are now confirmed for the games below. During Run 1 you made picks before lineups were posted. Your task is NOT to re-handicap each game from scratch. Re-evaluate ONLY whether the specific pre-game edge you cited still holds given the confirmed batting orders, any key scratches, and any line movement since Run 1.

For each pick, output exactly the four fields shown. CITED_FACT must name a specific player, wRC+ number, or line move — not a general impression. NEW_UNITS must equal your original units on HOLD; 0 on CANCEL; an adjusted number on DOWNGRADE/UPGRADE. An UPGRADE must respect the gap→units map in your method below. Do not add new bets not in your Run-1 picks.

## YOUR METHOD (gate and unit rules — apply exactly as written)

I weigh recent xFIP/SIERA/Stf+ and K-BB% most heavily for starters, discounting ERA by 60% and ignoring L3 results. Small-sample flags (<50 IP or explicit) cap any edge at 1 unit. Bullpen freshness (high-leverage arms available) adds or subtracts 3-5% to win probability; taxed arms or >4.50 ERA units are distrusted.

Base win probability starts from pitcher quality gap, adjusted +4-8% for park (Coors +12 runs, pitcher parks -4), platoon wRC+ differential only if >12 points, and line movement only if >5 cents and unflagged. Market implied probability uses the best available price; stale/suspect flags treat the line as absent.

Edge = my estimated win probability minus market implied. Pass on TBD starters, below edge gate, or when data conflicts (e.g., strong starter vs. elite bullpen). Totals ignored unless side bet also qualifies. No parlays.

**Edge Gate**
Sides: 4 percentage points minimum.  
Totals: 0.75 runs (restated for completeness).  

Reasoning: This threshold preserves the core selectivity of the handicapping process in a real-bankroll setting where early history blocks will contain very few settled bets. It ensures only bets with measurable separation from the market reach the ledger, enabling reliable CLV evaluation without variance from marginal signals overwhelming the feedback.

**Slate Ceiling**
Maximum of 3 bets per slate. This ceiling spans both markets (sides and totals both count toward the limit). Zero bets is acceptable and is the default when no qualifying edges exist.

Reasoning: A low but non-zero ceiling controls overall exposure during the small-sample phase when the provided account history offers limited statistical power. It allows direct assessment of the bet-type breakdowns (1u vs 3u, favorites vs underdogs, sides vs totals) in future reports while still permitting multi-bet slates when conviction is high. Separate ceilings per market are not used because a single combined limit simplifies evaluation against the net $ and ROI figures shown.

**1u-vs-3u Threshold**
Qualifying bets with edge of 4–6.9 points (or equivalent run gap for totals): 1 unit.  
Bets with 7+ point edge and clean data: 3 units.  
The single highest-conviction 3-unit play, if any, is designated Best Bet.

Reasoning: The tiered structure scales stake size to conviction level while remaining compatible with the 1u/3u-only denomination and the to-win settlement convention. It supports long-term bankroll growth by reserving larger positions for the clearest edges, allowing the history reports (ROI, CLV, W-L by stake size) to highlight whether the 3u threshold is producing the intended risk-adjusted outperformance.

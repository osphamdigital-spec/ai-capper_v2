═══════════════════════════════════════════════════════
MLB SLATE — Sunday, June 7 2026 (US Eastern Time)
15 games | Prompt built at 8:10 AM ET | Source: TheOddsAPI median of 9 books
═══════════════════════════════════════════════════════

You are an expert MLB betting analyst. Your goal is to find the bets on this slate where the market price is wrong — not to pick the most likely winners. A great analyst passes far more than they bet.

HOW TO APPROACH THIS:

  Use the data below as your foundation.
  If you have web access, you MAY look up additional information you think
  matters — bullpen usage, lineup news, recent form, splits, injuries, park
  factors. State clearly what you looked up and what you found. If you cannot
  browse, say so and work from the data given.
  Reason however you think is best. There is no required formula. Use your
  own judgment on how to weigh pitching, matchups, weather, and market price.
  Two good analysts will disagree — that is expected and fine.

UNIT SCALE (how much you would actually bet):

  5 units = MAX PLAY. Exceptional edge. Rare — once or twice a month.
  3 units = STRONG. Clear edge, confident.
  1 unit  = STANDARD. Real but ordinary edge.
  LEAN    = you slightly favour a side but would not bet it.
  PASS    = no edge. A valid and respectable answer.

STAKING DISCIPLINE:

  Before assigning 3 or more units, you must state three things explicitly:
    (a) Your estimated win probability as a percentage
    (b) The implied probability of the offered price
        (implied prob = 100 / (100 + positive_odds) for underdogs,
         or |negative_odds| / (|negative_odds| + 100) for favourites)
    (c) The gap between (a) and (b) in percentage points

  Then apply this hard mapping. No exceptions:
    Gap under 5 points  -> 1 unit maximum
    Gap 5-8 points      -> 3 units maximum
    Gap above 8 points, confirmed clean data -> 5 units maximum

  Narrative richness does not increase units. A bet with six supporting
  factors but a 4-point gap is a 1-unit bet. If your gap and your desired
  stake disagree, the gap wins.

RUN LINE RULE:

  The moneyline and run line answer different questions. A team at -250
  (implied ~71% to win) is typically only 48-55% to cover -1.5. These
  prices are internally consistent, not a mispricing.

  You may NOT take a -1.5 run line unless you first state two numbers:
    P(team wins)        -- your estimated win probability
    P(team wins by 2+)  -- a separate, independent estimate

  Only bet the run line if P(win by 2+) independently exceeds the run
  line's implied probability. The ML win probability may not serve as
  justification. If the offered run-line price appears more favourable
  than standard derivative pricing for that moneyline, treat it as a
  suspect/stale line flag, not found value.

UNDERDOG CHECK:

  You may not pass on a plus-money underdog using the word "fair" or
  "fairly priced" until you have written your estimated win probability
  as a number and compared it to the implied probability of the offered
  price. Only call it fair if the gap is under 3 points.

  If your reasoning block explicitly affirms that a plus-money side has
  real edge, you may not grade it PASS or "fair" unless you name one
  concrete structural reason the edge is offset (specific bullpen
  state, confirmed lineup hole, park, or weather). Absent a named
  blocker, the affirmed edge converts to a 1-unit bet.

BULLPEN FATIGUE RULE:

  For every game, count the number of fresh high-leverage arms (closer
  and setup men NOT used yesterday) for each team. State the delta.
  If the delta favours the underdog by 2 or more fresh arms, add at
  least 4 percentage points to your estimated underdog win probability
  before any pass decision.

  Before passing on any plus-money underdog: check the opposing
  bullpen's workload in the BULLPEN section. If the opponent's closer
  OR two or more relievers threw the previous day (look for pitch counts
  on the most recent date column), add at least 5 percentage points to
  your estimated underdog win probability before comparing to the market
  price. Do not pass without performing this adjustment.

ODDS APPROACH:
  Line movement from open to now is shown where available — use it as a
  signal of where money is going if you find it useful.
  There is no hard odds ceiling or floor. Any market is eligible if you
  identify genuine edge.
  SINGLES — bet any side where your estimated win probability clearly exceeds
  the implied probability. The bigger the gap, the stronger the play. Do NOT
  avoid plus-money underdogs — a +200 dog that genuinely wins 40% of the time
  is strong value and pays better than a -110 favourite at 52%. Do NOT bet
  heavy favourites just because they will probably win — if -200 is fairly
  priced at ~67%, there is no edge there.
  HEAVY FAVOURITES — when a moneyline is heavier than -180, consider that
  team's -1.5 run line instead — it is usually plus-money and a more efficient
  way to back a strong favourite.
BEFORE PICKING ANY SIDE: estimate a fair moneyline for this game using team
  quality, pitching, and matchup factors — before reading the market price.
  Write it down mentally. Then compare your estimate to the actual line. If
  the market price is within 10 cents of your estimate, there is likely no
  edge. If it is 15+ cents away, investigate why the market disagrees with
  you. This prevents anchoring to the offered price.

  2-LEG PARLAY — you MAY suggest ONE 2-leg moneyline parlay, but only if:

    Both legs are independently identified as having edge in your game-by-game
    analysis (never parlay games you would otherwise pass)
    Neither leg is shorter than -180 individually
    The games have no obvious correlation (not same division, not both
    weather-affected, not the same travel pattern)
    A parlay is optional — only include it if it genuinely adds value

TOTALS APPROACH
When evaluating a total, work through this sequence:

  1. Estimate expected combined runs:
       (Away RS/G + Home RA/G + Home RS/G + Away RA/G) / 2
  2. Adjust for park factor — a factor of 105 adds roughly +0.3 to +0.5 runs;
       a factor of 95 subtracts the same. Coors always inflates.
  3. Adjust for starter quality — each elite starter (xFIP < 3.50) suppresses
       roughly 0.5 to 0.8 runs vs an average starter.
  4. Adjust for bullpen — a taxed or high-ERA bullpen (both teams) adds
       roughly 0.3 to 0.5 runs in late innings.
  5. If your estimate differs from the posted total by 0.8+ runs, that gap
       is worth evaluating as a potential edge.
  6. Total line movement of 0.5+ points signals sharp action — treat as
       a meaningful input, not just noise.

  Strong UNDER candidates: elite starter matchup, pitcher-friendly park,
    cold offences, dome or roof confirmed closed.
  Strong OVER candidates: weak starters, hitter-friendly park (esp. Coors),
    wind blowing out, both bullpens taxed.

TEAM QUALITY CHECK (required before finalising any pick):

  State the gap in run differential, RS/G, and last-10 record for
  both teams. If the team you are betting trails in two or more of
  these three metrics, downgrade your pick one tier (3->1, 1->lean)
  unless you can name a specific factor that overrides the team
  quality gap (e.g. confirmed ace starter with xERA < 3.00, key
  lineup absence on the other side, confirmed bullpen depletion).

SMALL SAMPLE CHECK:

  If either starter is marked [small sample] in the pitcher block,
  you may not assign 3+ units or Best Bet designation. Their ERA
  is not predictive. Cite at least one non-ERA indicator (K/9, K-BB%,
  Brl%, L3 ERA trend, or last-3-starts data) if you bet at all.

OPENER/BULK FLAG:

  If either starter has 5.0 or fewer innings pitched for the season
  total (shown in the IP field), treat them as a probable opener or
  bulk-use scenario rather than a traditional starter. Explicitly
  reframe that team's pitching matchup as: "[Team] is effectively
  running a bullpen game today." Evaluate the matchup against their
  full bullpen quality, not the listed starter's stats.

ESTIMATED DATA RULE:

  Some platoon splits and wRC+ figures in the prompt are labeled
  ESTIMATED. These are team aggregate proxies, not confirmed lineup
  data. Any metric labeled ESTIMATED is LOW-TRUST and may not be the
  primary justification for a bet. You must corroborate it with at
  least two independent non-estimated signals (team form, pitcher
  metrics, bullpen state, park factor) or downgrade the pick to
  lean/pass.

═══════════════════════════════════════════════════════
GAME 1 OF 15: Pittsburgh Pirates (PIT) @ Atlanta Braves (ATL)
1:36 PM ET | Truist Park, Cumberland, GA

ODDS
  Moneyline : PIT +138 / ATL -158  |  best: PIT +142 (BetOnline.ag) / ATL -155 (BetUS)
  Run Line  : PIT +1.5 (-145) / ATL -1.5 (+125)  |  best: -143 (LowVig.ag) / +130 (FanDuel)
  Total     : 9.0 — Over +100 / Under -119  |  best: Over +103 (LowVig.ag) / Under [price flagged as suspect — stale book data]
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  PIT: 34-31 (.523), last10 5-5, run diff +31, away 16-16, 5.1 RS/G / 4.6 RA/G
  ATL: 44-21 (.677), last10 7-3, run diff +115, home 21-11, 5.2 RS/G / 3.5 RA/G

PLATOON MATCHUP
  PIT batting vs RHP:
    Team wRC+: 104 (ESTIMATED)
    Key bats: Brandon Lowe 166, Ryan O'Hearn 157, Spencer Horwitz 143
    Weak bats: Marcell Ozuna 48, Jared Triolo 35
  ATL batting vs RHP:
    Team wRC+: 125 (ESTIMATED)
    Key bats: Matt Olson 157, Ronald Acuña Jr. 150, Michael Harris II 143
    Weak bats: Mike Yastrzemski 108, Austin Riley 80

STARTING PITCHERS
  Away: Bubba Chandler (RHP) — 2-6, 5.05 ERA, 1.53 WHIP, 55 K, 57.0 IP
       FanG season:  xFIP 4.57 | SIERA 4.54 | K-BB% 10.7% | 76.1 IP (2025-26 blended)
       Last 14 days:  xFIP 5.01 | SIERA 4.85 | K/9 7.2 | BB/9 3.6 | 10.0 IP
  Home: Bryce Elder (RHP) — 5-3, 2.63 ERA, 1.08 WHIP, 67 K, 78.2 IP
       FanG season:  xFIP 3.98 | SIERA 4.20 | K-BB% 12.4% | 235.0 IP (2025-26 blended)
       Last 14 days:  xFIP 4.32 | SIERA 4.49 | K/9 6.3 | BB/9 1.8 | 10.0 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- PIT
  Closer: Gregory Soto (L) -- 2.86 ERA, 30.6% K%, 8 SV, 6 HLD
    Usage last 6: Fri - | Thu - | Wed 18p(L,B) | Tue 7p(Sv) | Mon - | Sun -
  Setup: Carmen Mlodzinski (R) -- 3.66 ERA, 19.4% K%, 1 SV
    Usage last 6: Fri - | Thu 55p(Sv) | Wed - | Tue - | Mon - | Sun -
  Setup: Mason Montgomery (L) -- 4.94 ERA, 31.4% K%, 7 HLD
    Usage last 6: Fri - | Thu - | Wed 26p | Tue - | Mon - | Sun -
  Taxed (30+ pitches last 2 days): Carmen Mlodzinski
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 4.05

BULLPEN -- ATL
  Closer: Raisel Iglesias (R) -- 0.96 ERA, 31.0% K%, 11 SV
    Usage last 6: Fri - | Thu - | Wed - | Tue 15p(Sv) | Mon - | Sun -
  Setup: Robert Suarez (R) -- 0.65 ERA, 23.8% K%, 4 SV, 9 HLD
    Usage last 6: Fri - | Thu - | Wed 18p | Tue 13p(H) | Mon - | Sun -
  Setup: Dylan Lee (L) -- 1.26 ERA, 33.7% K%, 11 HLD
    Usage last 6: Fri - | Thu - | Wed 11p(H) | Tue - | Mon - | Sun -
  Taxed (30+ pitches last 2 days): Reynaldo López
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 2.13

WEATHER (Truist Park)
  84.2°F | 6.6 mph S | Overcast | 5% rain

PARK: Truist Park
  Park factor: 99 (3yr) | HR: 99 | Runs: 98

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 2 OF 15: Boston Red Sox (BOS) @ New York Yankees (NYY)
1:36 PM ET | Yankee Stadium, Bronx, NY

ODDS
  Moneyline : BOS +141 / NYY -165  |  best: BOS +146 (LowVig.ag) / NYY -161 (LowVig.ag)
  Run Line  : BOS +1.5 (-149) / NYY -1.5 (+125)  |  best: -145 (Bovada) / +132 (LowVig.ag)
  Total     : 8.0 — Over -120 / Under +100  |  best: Over -115 (MyBookie.ag) / Under +105 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  BOS: 27-35 (.435), last10 5-5, run diff -4, away 17-14, 4.0 RS/G / 4.1 RA/G
  NYY: 37-26 (.587), last10 6-4, run diff +91, home 18-12, 5.0 RS/G / 3.6 RA/G

PLATOON MATCHUP
  BOS batting vs RHP:
    Team wRC+: 90 (ESTIMATED)
    Key bats: Willson Contreras 140, Mickey Gasper 135, Connor Wong 131
    Weak bats: Caleb Durbin 51, Trevor Story 44
  NYY batting vs LHP:
    Team wRC+: 125 (ESTIMATED)
    Key bats: Paul Goldschmidt 253, Ben Rice 180, Aaron Judge 159
    Weak bats: Jazz Chisholm Jr. 77, Austin Wells -3

STARTING PITCHERS
  Away: Ranger Suarez (LHP) — 2-3, 3.38 ERA, 1.16 WHIP, 57 K, 58.2 IP
       FanG season:  xFIP 3.58 | SIERA 3.74 | K-BB% 17.0% | 216.0 IP (2025-26 blended)
       Last 14 days:  xFIP 3.85 | SIERA 3.64 | K/9 12.6 | BB/9 4.5 | 10.0 IP
  Home: Cam Schlittler (RHP) — 7-3, 1.89 ERA, 0.86 WHIP, 84 K, 76.1 IP
       FanG season:  xFIP 3.28 | SIERA 3.36 | K-BB% 20.7% | 149.1 IP (2025-26 blended)
       Last 14 days:  xFIP 4.02 | SIERA 3.74 | K/9 7.8 | BB/9 0.0 | 10.1 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- BOS
  Closer: Aroldis Chapman (L) -- 0.48 ERA, 34.7% K%, 12 SV
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon - | Sun 13p
  Setup: Justin Slaten (R) -- 3.60 ERA, 32.6% K%, 6 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon - | Sun -
  Setup: Greg Weissert (R) -- 3.96 ERA, 23.1% K%, 4 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 25p | Mon - | Sun 19p
  Taxed (30+ pitches last 2 days): Jovani Morán, Tommy Kahnle
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 4.25

BULLPEN -- NYY
  Closer: David Bednar (R) -- 4.32 ERA, 25.4% K%, 13 SV
    Usage last 6: Fri - | Thu 12p(Sv) | Wed - | Tue - | Mon - | Sun 19p
  Setup: Fernando Cruz (R) -- 2.00 ERA, 29.7% K%, 11 HLD
    Usage last 6: Fri - | Thu 10p(H) | Wed 18p | Tue - | Mon - | Sun 15p
  Setup: Brent Headrick (L) -- 1.82 ERA, 26.8% K%, 7 HLD
    Usage last 6: Fri - | Thu 19p(W) | Wed - | Tue 32p | Mon - | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 3.79

WEATHER (Yankee Stadium)
  83.4°F | 14.3 mph W | Clear sky | 1% rain

PARK: Yankee Stadium
  Park factor: 101 (3yr) | HR: 116 | Runs: 102

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 3 OF 15: Chicago White Sox (CHW) @ Philadelphia Phillies (PHI)
1:36 PM ET | Citizens Bank Park, Philadelphia, PA

ODDS
  Moneyline : CHW +143 / PHI -168  |  best: CHW +149 (LowVig.ag) / PHI -165 (LowVig.ag)
  Run Line  : CHW +1.5 (-140) / PHI -1.5 (+120)  |  best: -134 (MyBookie.ag) / +122 (LowVig.ag)
  Total     : 9.5 — Over -110 / Under -109  |  best: Over -108 (FanDuel) / Under -105 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  CWS: 34-30 (.531), last10 7-3, run diff +12, away 14-19, 4.8 RS/G / 4.6 RA/G
  PHI: 34-30 (.531), last10 7-3, run diff -23, home 18-17, 4.0 RS/G / 4.3 RA/G

PLATOON MATCHUP
  CHW batting vs RHP:
    Team wRC+: 99 (ESTIMATED)
    Key bats: Munetaka Murakami 168, Sam Antonacci 150, Tristan Peters 127
    Weak bats: Edgar Quero 56, Luisangel Acuña 40
  PHI batting vs LHP:
    Team wRC+: 102 (ESTIMATED)
    Key bats: Kyle Schwarber 169, Adolis García 102, Edmundo Sosa 98
    Weak bats: Bryce Harper 86, Trea Turner 60

STARTING PITCHERS
  Away: Tyler Gilbert (LHP) — 0-0, 20.25 ERA, 2.63 WHIP, 2 K, 2.2 IP
       FanG season:  xFIP 2.79 | SIERA 2.95 | K-BB% 25.0% | 6.2 IP (2025-26 blended)
       Last 14 days:  no data
  Home: Aaron Nola (RHP) — 3-4, 5.55 ERA, 1.39 WHIP, 64 K, 61.2 IP
       FanG season:  xFIP 3.63 | SIERA 3.74 | K-BB% 17.2% | 156.0 IP (2025-26 blended)
       Last 14 days:  xFIP 2.31 | SIERA 2.15 | K/9 10.6 | BB/9 0.0 | 11.0 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- CHW
  Closer: Seranthony Domínguez (R) -- 3.97 ERA, 28.9% K%, 11 SV, 1 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon - | Sun -
  Setup: Grant Taylor (R) -- 1.99 ERA, 36.4% K%, 1 SV, 4 HLD
    Usage last 6: Fri - | Thu - | Wed 25p | Tue - | Mon - | Sun -
  Setup: Bryan Hudson (L) -- 1.26 ERA, 23.7% K%, 2 SV, 4 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon - | Sun 17p(H)
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 5.54

BULLPEN -- PHI
  Closer: Jhoan Duran (R) -- 1.37 ERA, 41.9% K%, 14 SV
    Usage last 6: Fri - | Thu - | Wed 16p(Sv) | Tue 14p(Sv) | Mon - | Sun -
  Setup: Brad Keller (R) -- 3.71 ERA, 25.9% K%, 3 SV, 10 HLD
    Usage last 6: Fri - | Thu - | Wed 22p(H) | Tue 12p(H) | Mon - | Sun -
  Setup: José Alvarado (L) -- 5.91 ERA, 26.0% K%, 1 SV, 7 HLD
    Usage last 6: Fri - | Thu 25p | Wed - | Tue 11p(W) | Mon - | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 3.93

WEATHER (Citizens Bank Park)
  85.4°F | 11.7 mph NW | Mainly clear | 0% rain

PARK: Citizens Bank Park
  Park factor: 102 (3yr) | HR: 113 | Runs: 104

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 4 OF 15: Baltimore Orioles (BAL) @ Toronto Blue Jays (TOR)
1:38 PM ET | Rogers Centre, Toronto, ON

ODDS
  Moneyline : BAL +118 / TOR -136  |  best: BAL +122 (LowVig.ag) / TOR -135 (LowVig.ag)
  Run Line  : BAL +1.5 (-181) / TOR -1.5 (+153)  |  best: -175 (LowVig.ag) / +162 (FanDuel)
  Total     : 8.0 — Over -115 / Under -105  |  best: Over -113 (LowVig.ag) / Under -102 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  BAL: 31-34 (.477), last10 6-4, run diff -29, away 12-19, 4.7 RS/G / 5.1 RA/G
  TOR: 31-34 (.477), last10 5-5, run diff -15, home 18-14, 4.1 RS/G / 4.3 RA/G

PLATOON MATCHUP
  BAL batting vs RHP:
    Team wRC+: 110 (ESTIMATED)
    Key bats: Adley Rutschman 158, Samuel Basallo 148, Leody Taveras 136
    Weak bats: Gunnar Henderson 88, Coby Mayo 41
  TOR batting vs RHP:
    Team wRC+: 98 (ESTIMATED)
    Key bats: Yohendrick Piñango 138, Jesús Sánchez 122, Ernie Clement 121
    Weak bats: George Springer 71, Tyler Heineman 18

STARTING PITCHERS
  Away: Shane Baz (RHP) — 3-5, 4.29 ERA, 1.37 WHIP, 63 K, 71.1 IP
       FanG season:  xFIP 4.02 | SIERA 4.09 | K-BB% 14.4% | 237.2 IP (2025-26 blended)
       Last 14 days:  xFIP 3.47 | SIERA 3.49 | K/9 9.6 | BB/9 2.6 | 14.0 IP
  Home: Kevin Gausman (RHP) — 4-4, 3.36 ERA, 1.09 WHIP, 74 K, 75.0 IP
       FanG season:  xFIP 3.66 | SIERA 3.68 | K-BB% 18.4% | 268.0 IP (2025-26 blended)
       Last 14 days:  xFIP 3.55 | SIERA 3.44 | K/9 10.6 | BB/9 3.3 | 11.0 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- BAL
  Closer: Rico Garcia (R) -- 0.68 ERA, 32.3% K%, 4 SV, 8 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 14p(Sv) | Mon - | Sun 6p
  Setup: Andrew Kittredge (R) -- 7.11 ERA, 23.7% K%, 2 HLD
    Usage last 6: Fri - | Thu 9p | Wed - | Tue 11p(H) | Mon - | Sun -
  Setup: Yennier Cano (R) -- 2.70 ERA, 21.1% K%, 4 HLD
    Usage last 6: Fri - | Thu 1p | Wed - | Tue - | Mon - | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 6.14

BULLPEN -- TOR
  Closer: Louis Varland (R) -- 0.28 ERA, 34.7% K%, 9 SV, 5 HLD
    Usage last 6: Fri - | Thu 17p(Sv) | Wed - | Tue - | Mon - | Sun -
  Setup: Tyler Rogers (R) -- 2.28 ERA, 14.3% K%, 2 SV, 12 HLD
    Usage last 6: Fri - | Thu 12p(H) | Wed - | Tue - | Mon - | Sun -
  Setup: Braydon Fisher (R) -- 2.62 ERA, 27.1% K%, 1 SV, 7 HLD
    Usage last 6: Fri - | Thu 9p(H) | Wed - | Tue 15p | Mon - | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 3.64

WEATHER (Rogers Centre)
  75.7°F | 9.3 mph N | Mainly clear | 0% rain
  (Retractable roof — may be open or closed at game time)

PARK: Rogers Centre
  Park factor: 102 (3yr) | HR: 115 | Runs: 104
  Roof-closed factor: 100 -- use this value if roof confirmed closed at game time

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 5 OF 15: Seattle Mariners (SEA) @ Detroit Tigers (DET)
1:41 PM ET | Comerica Park, Detroit, MI

ODDS
  Moneyline : SEA -119 / DET +100  |  best: SEA -110 (BetOnline.ag) / DET +102 (FanDuel)
  Run Line  : SEA -1.5 (+140) / DET +1.5 (-165)  |  best: +146 (FanDuel) / -160 (BetOnline.ag)
  Total     : 8.5 — Over -105 / Under -115  |  best: Over -105 (FanDuel) / Under [price flagged as suspect — stale book data]
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  SEA: 34-31 (.523), last10 8-2, run diff +30, away 15-15, 4.2 RS/G / 3.8 RA/G
  DET: 26-39 (.400), last10 5-5, run diff -25, home 15-15, 3.9 RS/G / 4.3 RA/G

PLATOON MATCHUP
  SEA batting vs RHP:
    Team wRC+: 116 (ESTIMATED)
    Key bats: Brendan Donovan 186, Luke Raley 159, Randy Arozarena 141
    Weak bats: Mitch Garver 63, Leo Rivas 58
  DET batting vs RHP:
    Team wRC+: 93 (ESTIMATED)
    Key bats: Dillon Dingler 151, Riley Greene 146, Gleyber Torres 143
    Weak bats: Jake Rogers 31, Wenceel Pérez 21

STARTING PITCHERS
  Away: Luis Castillo (RHP) — 2-5, 5.53 ERA, 1.45 WHIP, 56 K, 55.1 IP
       FanG season:  xFIP 4.13 | SIERA 4.04 | K-BB% 15.2% | 228.2 IP (2025-26 blended)
       Last 14 days:  xFIP 3.40 | SIERA 3.17 | K/9 13.5 | BB/9 4.5 | 4.0 IP
  Home: Jack Flaherty (RHP) — 1-7, 5.31 ERA, 1.60 WHIP, 70 K, 57.2 IP
       FanG season:  xFIP 3.91 | SIERA 3.81 | K-BB% 17.5% | 218.2 IP (2025-26 blended)
       Last 14 days:  xFIP 2.76 | SIERA 2.81 | K/9 12.7 | BB/9 2.5 | 10.2 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- SEA
  Closer: Andrés Muñoz (R) -- 4.76 ERA, 35.4% K%, 9 SV
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 12p | Sun -
  Setup: Matt Brash (R) -- 0.60 ERA, 23.2% K%, 5 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 12p | Sun -
  Setup: José A. Ferrer (L) -- 1.63 ERA, 20.5% K%, 3 SV, 7 HLD
    Usage last 6: Fri - | Thu - | Wed 13p | Tue - | Mon 13p | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 2.87

BULLPEN -- DET
  Closer: Kyle Finnegan (R) -- 1.93 ERA, 13.7% K%, 1 SV, 7 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 19p(H) | Sun -
  Setup: Will Vest (R) -- 7.23 ERA, 24.1% K%, 1 SV, 6 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 40p(Sv) | Sun -
  Setup: Tyler Holton (L) -- 4.23 ERA, 20.7% K%, 4 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 23p(W) | Sun 5p
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 6.02

WEATHER (Comerica Park)
  80.6°F | 6.3 mph N | Clear sky | 0% rain

PARK: Comerica Park
  Park factor: 102 (3yr) | HR: 108 | Runs: 104

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 6 OF 15: Tampa Bay Rays (TB) @ Miami Marlins (MIA)
1:41 PM ET | loanDepot park, Miami, FL

ODDS
  Moneyline : TB -116 / MIA -102  |  best: TB -110 (BetUS) / MIA [price flagged as suspect — stale book data]
  Run Line  : TB -1.5 (+145) / MIA +1.5 (-170)  |  best: +152 (FanDuel) / -165 (LowVig.ag)
  Total     : 8.5 — Over -105 / Under -115  |  best: Over [price flagged as suspect — stale book data] / Under [price flagged as suspect — stale book data]
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  TB: 37-24 (.607), last10 3-7, run diff +10, away 16-15, 4.6 RS/G / 4.5 RA/G
  MIA: 30-35 (.462), last10 4-6, run diff -23, home 19-16, 4.2 RS/G / 4.5 RA/G

PLATOON MATCHUP
  TB batting vs RHP:
    Team wRC+: 104 (ESTIMATED)
    Key bats: Yandy Díaz 156, Jonathan Aranda 149, Junior Caminero 146
    Weak bats: Jonny DeLuca 74, Cedric Mullins 63
  MIA batting vs RHP:
    Team wRC+: 88 (ESTIMATED)
    Key bats: Liam Hicks 137, Xavier Edwards 133, Otto Lopez 105
    Weak bats: Agustín Ramírez 51, Graham Pauley 34

STARTING PITCHERS
  Away: Griffin Jax (RHP) — 1-4, 4.76 ERA, 1.47 WHIP, 32 K, 34.0 IP
       FanG season:  xFIP 3.87 | SIERA 4.18 | K-BB% 12.5% | 27.0 IP (2025-26 blended)
       Last 14 days:  xFIP 2.86 | SIERA 3.07 | K/9 12.0 | BB/9 1.5 | 6.0 IP
  Home: Sandy Alcantara (RHP) — 4-4, 4.59 ERA, 1.30 WHIP, 57 K, 82.1 IP
       FanG season:  xFIP 4.23 | SIERA 4.39 | K-BB% 11.1% | 257.0 IP (2025-26 blended)
       Last 14 days:  xFIP 5.03 | SIERA 4.42 | K/9 6.4 | BB/9 0.7 | 12.2 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- TB
  Closer: Bryan Baker (R) -- 2.13 ERA, 28.4% K%, 16 SV, 1 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 13p | Mon - | Sun 11p(Sv)
  Setup: Ian Seymour (L) -- 5.23 ERA, 24.6% K%, 2 SV, 9 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 40p | Mon - | Sun -
  Setup: Kevin Kelly (R) -- 2.67 ERA, 19.4% K%, 2 SV, 12 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon - | Sun 23p(H)
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 4.33

BULLPEN -- MIA
  Closer: Pete Fairbanks (R) -- 6.61 ERA, 32.4% K%, 7 SV, 1 HLD
    Usage last 6: Fri - | Thu - | Wed 20p(Sv) | Tue - | Mon 13p | Sun -
  Setup: Anthony Bender (R) -- 3.33 ERA, 26.8% K%, 1 SV, 5 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 6p(H) | Mon - | Sun 17p
  Setup: Michael Petersen (R) -- 3.47 ERA, 26.6% K%, 1 SV, 7 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 11p(H) | Mon 16p(H) | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 4.22

WEATHER (loanDepot park)
  84.6°F | 9.6 mph E | Overcast | 1% rain
  (Retractable roof — may be open or closed at game time)

PARK: loanDepot park
  Park factor: 97 (3yr) | HR: 81 | Runs: 94
  Roof-closed factor: 100 -- use this value if roof confirmed closed at game time

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 7 OF 15: Athletics (ATH) @ Houston Astros (HOU)
2:11 PM ET | Minute Maid Park, Houston, TX

ODDS
  Moneyline : ATH -107 / HOU -110  |  best: ATH -103 (BetOnline.ag) / HOU -105 (BetUS)
  Run Line  : ATH -1.5 (+140) / HOU +1.5 (-171)  |  best: +154 (BetMGM) / [price flagged as suspect — stale book data]
  Total     : 9.0 — Over -110 / Under -108  |  best: Over -109 (LowVig.ag) / Under -105 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  ATH: 30-34 (.469), last10 3-7, run diff -48, away 19-17, 4.2 RS/G / 4.9 RA/G
  HOU: 30-36 (.455), last10 6-4, run diff -24, home 16-18, 4.7 RS/G / 5.0 RA/G

PLATOON MATCHUP
  ATH batting vs RHP:
    Team wRC+: 102 (ESTIMATED)
    Key bats: Nick Kurtz 178, Carlos Cortes 143, Shea Langeliers 130
    Weak bats: Max Muncy 72, Lawrence Butler 42
  HOU batting vs LHP:
    Team wRC+: 128 (ESTIMATED)
    Key bats: Yordan Alvarez 201, Isaac Paredes 127, Christian Walker 119
    Weak bats: Cam Smith 99, Jose Altuve 94

STARTING PITCHERS
  Away: Gage Jump (LHP) — 1-1, 3.75 ERA, 1.17 WHIP, 10 K, 12.0 IP
       FanG season:  xFIP 4.22 | SIERA 3.89 | K-BB% 16.3% | 12.0 IP (2025-26 blended)
       Last 14 days:  xFIP 4.24 | SIERA 3.90 | K/9 7.5 | BB/9 1.5 | 12.0 IP
  Home: Mike Burrows (RHP) — 3-7, 5.66 ERA, 1.54 WHIP, 57 K, 68.1 IP
       FanG season:  xFIP 4.11 | SIERA 4.11 | K-BB% 14.2% | 155.0 IP (2025-26 blended)
       Last 14 days:  xFIP 4.90 | SIERA 5.13 | K/9 6.8 | BB/9 4.5 | 12.0 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- ATH
  Closer: Hogan Harris (L) -- 2.48 ERA, 24.8% K%, 5 SV, 9 HLD
    Usage last 6: Fri - | Thu - | Wed 17p(W) | Tue 2p(Sv) | Mon - | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 3.42

BULLPEN -- HOU
  Closer: Josh Hader (L) -- 0.00 ERA, 25.0% K%, 1 SV
    Usage last 6: Fri - | Thu - | Wed 17p(Sv) | Tue - | Mon - | Sun -
  Setup: Bryan King (L) -- 2.73 ERA, 17.4% K%, 6 SV, 5 HLD
    Usage last 6: Fri - | Thu - | Wed 23p | Tue - | Mon - | Sun -
  Setup: Enyel De Los Santos (R) -- 3.20 ERA, 24.5% K%, 4 SV, 4 HLD
    Usage last 6: Fri - | Thu 12p | Wed - | Tue 11p | Mon - | Sun -
  Taxed (30+ pitches last 2 days): Steven Okert
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 4.07

WEATHER (Minute Maid Park)
  85.0°F | 8.6 mph SE | Overcast | 11% rain
  (Retractable roof — may be open or closed at game time)

PARK: Minute Maid Park
  Park factor: 100 (3yr) | HR: 115 | Runs: 100
  Roof-closed factor: 101 -- use this value if roof confirmed closed at game time

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 8 OF 15: Kansas City Royals (KC) @ Minnesota Twins (MIN)
2:11 PM ET | Target Field, Minneapolis, MN

ODDS
  Moneyline : KC -110 / MIN -106  |  best: KC -107 (BetOnline.ag) / MIN -103 (BetOnline.ag)
  Run Line  : KC -1.5 (+139) / MIN +1.5 (-170)  |  best: +150 (Bovada) / [price flagged as suspect — stale book data]
  Total     : 9.0 — Over -110 / Under -110  |  best: Over -105 (LowVig.ag) / Under -109 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  KC: 26-39 (.400), last10 4-6, run diff -49, away 11-22, 3.9 RS/G / 4.6 RA/G
  MIN: 30-36 (.455), last10 3-7, run diff -25, home 18-17, 4.6 RS/G / 5.0 RA/G

PLATOON MATCHUP
  KC batting vs LHP:
    Team wRC+: 84 (ESTIMATED)
    Key bats: Bobby Witt Jr. 145, Lane Thomas 130, Salvador Perez 127
    Weak bats: Isaac Collins 37, Vinnie Pasquantino 5
  MIN batting vs LHP:
    Team wRC+: 106 (ESTIMATED)
    Key bats: Ryan Jeffers 157, Austin Martin 155, Victor Caratini 92
    Weak bats: Brooks Lee 85, Josh Bell 78

STARTING PITCHERS
  Away: Noah Cameron (LHP) — 2-4, 4.22 ERA, 1.26 WHIP, 56 K, 59.2 IP
       FanG season:  xFIP 4.00 | SIERA 4.19 | K-BB% 13.6% | 198.0 IP (2025-26 blended)
       Last 14 days:  xFIP 2.32 | SIERA 2.49 | K/9 9.0 | BB/9 0.8 | 12.0 IP
  Home: Connor Prielipp (LHP) — 2-3, 5.26 ERA, 1.35 WHIP, 42 K, 39.1 IP
       FanG season:  xFIP 4.16 | SIERA 4.02 | K-BB% 14.5% | 39.1 IP (2025-26 blended)
       Last 14 days:  xFIP 3.49 | SIERA 3.96 | K/9 10.4 | BB/9 4.3 | 10.1 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- KC
  Closer: Alex Lange (R) -- 4.18 ERA, 23.5% K%, 2 SV, 1 HLD
    Usage last 6: Fri - | Thu 20p(Sv) | Wed 24p(Sv) | Tue - | Mon 9p | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 4 fresh
  Bullpen ERA (season avg): 21.87

BULLPEN -- MIN
  Closer: Yoendrys Gómez (R) -- 3.82 ERA, 23.1% K%, 4 SV, 5 HLD
    Usage last 6: Fri - | Thu 18p | Wed - | Tue 15p(Sv) | Mon 15p | Sun -
  Setup: Anthony Banda (L) -- 5.13 ERA, 20.3% K%, 1 SV, 7 HLD
    Usage last 6: Fri - | Thu 8p(BS) | Wed - | Tue 20p(H) | Mon - | Sun -
  Setup: Eric Orze (R) -- 3.64 ERA, 20.8% K%, 1 SV, 6 HLD
    Usage last 6: Fri - | Thu 16p | Wed 26p | Tue - | Mon - | Sun -
  Taxed (30+ pitches last 2 days): Andrew Morris, Mike Paredes
  High-leverage arms available: 0 of 4 fresh
  Bullpen ERA (season avg): 4.86

WEATHER (Target Field)
  86.4°F | 12.8 mph SE | Overcast | 0% rain

PARK: Target Field
  Park factor: 100 (3yr) | HR: 85 | Runs: 100

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 9 OF 15: Cincinnati Reds (CIN) @ St. Louis Cardinals (STL)
2:16 PM ET | Busch Stadium, St. Louis, MO

ODDS
  Moneyline : CIN +114 / STL -135  |  best: CIN +122 (BetUS) / STL -132 (LowVig.ag)
  Run Line  : CIN +1.5 (-175) / STL -1.5 (+150)  |  best: -174 (MyBookie.ag) / +154 (LowVig.ag)
  Total     : 9.0 — Over -120 / Under +100  |  best: Over [price flagged as suspect — stale book data] / Under +103 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  CIN: 31-32 (.492), last10 3-7, run diff -49, away 15-16, 4.3 RS/G / 5.1 RA/G
  STL: 34-28 (.548), last10 5-5, run diff -4, home 18-16, 4.4 RS/G / 4.5 RA/G

PLATOON MATCHUP
  CIN batting vs RHP:
    Team wRC+: 92 (ESTIMATED)
    Key bats: JJ Bleday 175, Nathaniel Lowe 153, Elly De La Cruz 122
    Weak bats: TJ Friedl 51, Ke'Bryan Hayes -10
  STL batting vs RHP:
    Team wRC+: 96 (ESTIMATED)
    Key bats: Alec Burleson 161, Jordan Walker 155, JJ Wetherholt 128
    Weak bats: Victor Scott II 40, Thomas Saggese 16

STARTING PITCHERS
  Away: Rhett Lowder (RHP) — 3-3, 5.40 ERA, 1.41 WHIP, 27 K, 38.1 IP
       FanG season:  xFIP 4.78 | SIERA 5.06 | K-BB% 5.4% | 38.1 IP (2025-26 blended)
       Last 14 days:  no data
  Home: Michael McGreevy (RHP) — 3-5, 2.98 ERA, 1.10 WHIP, 44 K, 66.1 IP
       FanG season:  xFIP 4.20 | SIERA 4.53 | K-BB% 9.5% | 156.1 IP (2025-26 blended)
       Last 14 days:  xFIP 4.65 | SIERA 5.08 | K/9 6.3 | BB/9 4.5 | 10.0 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- CIN
  Closer: Tony Santillan (R) -- 6.65 ERA, 21.2% K%, 2 SV, 11 HLD
    Usage last 6: Fri - | Thu - | Wed 22p(L) | Tue - | Mon - | Sun 18p(H)
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 4.32

BULLPEN -- STL
  Closer: Riley O'Brien (R) -- 3.95 ERA, 25.7% K%, 15 SV, 1 HLD
    Usage last 6: Fri - | Thu - | Wed 13p(Sv) | Tue 32p(L) | Mon - | Sun -
  Setup: George Soriano (R) -- 2.92 ERA, 21.8% K%, 2 SV, 9 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 10p | Mon 17p | Sun -
  Setup: JoJo Romero (L) -- 3.54 ERA, 23.7% K%, 17 HLD
    Usage last 6: Fri - | Thu - | Wed 23p(H) | Tue 14p | Mon - | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 4.12

WEATHER (Busch Stadium)
  87.1°F | 9.0 mph SE | Overcast | 3% rain

PARK: Busch Stadium
  Park factor: 97 (3yr) | HR: 78 | Runs: 94

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 10 OF 15: Cleveland Guardians (CLE) @ Texas Rangers (TEX)
2:36 PM ET | Globe Life Field, Arlington, TX

ODDS
  Moneyline : CLE +120 / TEX -140  |  best: CLE +127 (LowVig.ag) / TEX -139 (MyBookie.ag)
  Run Line  : CLE +1.5 (-185) / TEX -1.5 (+153)  |  best: -175 (LowVig.ag) / +163 (BetRivers)
  Total     : 7.5 — Over +100 / Under -120  |  best: Over +105 (Bovada) / Under -118 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  CLE: 37-29 (.561), last10 5-5, run diff +11, away 20-15, 4.1 RS/G / 4.0 RA/G
  TEX: 31-33 (.484), last10 6-4, run diff +4, home 16-14, 3.9 RS/G / 3.9 RA/G

PLATOON MATCHUP
  CLE batting vs RHP:
    Team wRC+: 92 (ESTIMATED)
    Key bats: Travis Bazzana 177, Rhys Hoskins 127, Brayan Rocchio 111
    Weak bats: Austin Hedges 53, Bo Naylor 7
  TEX batting vs LHP:
    Team wRC+: 92 (ESTIMATED)
    Key bats: Brandon Nimmo 106, Andrew McCutchen 77

STARTING PITCHERS
  Away: Joey Cantillo (LHP) — 4-2, 3.92 ERA, 1.45 WHIP, 56 K, 62.0 IP
       FanG season:  xFIP 4.19 | SIERA 4.37 | K-BB% 12.1% | 129.0 IP (2025-26 blended)
       Last 14 days:  xFIP 7.10 | SIERA 6.94 | K/9 7.5 | BB/9 10.5 | 6.0 IP
  Home: Jacob deGrom (RHP) — 4-4, 3.48 ERA, 1.01 WHIP, 78 K, 64.2 IP
       FanG season:  xFIP 3.31 | SIERA 3.22 | K-BB% 23.0% | 237.1 IP (2025-26 blended)
       Last 14 days:  xFIP 2.42 | SIERA 2.59 | K/9 11.4 | BB/9 1.6 | 11.0 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- CLE
  Closer: Cade Smith (R) -- 2.83 ERA, 37.4% K%, 21 SV
    Usage last 6: Fri - | Thu - | Wed 11p(Sv) | Tue - | Mon - | Sun -
  Setup: Hunter Gaddis (R) -- 3.86 ERA, 18.9% K%, 1 SV, 9 HLD
    Usage last 6: Fri - | Thu - | Wed 15p(H) | Tue 22p(H) | Mon - | Sun -
  Setup: Shawn Armstrong (R) -- 3.38 ERA, 29.9% K%, 5 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 11p | Mon - | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 3.42

BULLPEN -- TEX
  Closer: Jacob Latz (L) -- 2.00 ERA, 26.5% K%, 8 SV, 2 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 16p(Sv) | Sun 9p(Sv)
  Setup: Jakob Junis (R) -- 1.69 ERA, 16.7% K%, 4 SV, 6 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 18p(Sv) | Mon 12p(H) | Sun -
  Setup: Tyler Alexander (L) -- 3.12 ERA, 18.6% K%, 2 SV, 6 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 12p(H) | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 3.51

WEATHER (Globe Life Field)
  84.2°F | 8.6 mph S | Thunderstorm | 3% rain
  (Retractable roof — may be open or closed at game time)

PARK: Globe Life Field
  Park factor: 91 (3yr) | HR: 83 | Runs: 83 -- pitcher-friendly
  Roof-closed factor: 92 -- use this value if roof confirmed closed at game time

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 11 OF 15: Milwaukee Brewers (MIL) @ Colorado Rockies (COL)
3:11 PM ET | Coors Field, Denver, CO

ODDS
  Moneyline : MIL -180 / COL +153  |  best: MIL -170 (Bovada) / COL +162 (LowVig.ag)
  Run Line  : MIL -1.5 (-125) / COL +1.5 (+104)  |  best: -110 (Bovada) / +108 (LowVig.ag)
  Total     : 12.0 — Over -116 / Under -105  |  best: Over -102 (BetMGM) / Under [price flagged as suspect — stale book data]
  Line move : no movement yet — re-run fetch_odds.py closer to game time
  NOTE: Milwaukee Brewers ML is heavy at -180. Their -1.5 run line at -125 may be a more efficient way to back them — consider it.

TEAM FORM
  MIL: 39-23 (.629), last10 7-3, run diff +97, away 18-10, 5.1 RS/G / 3.5 RA/G
  COL: 24-41 (.369), last10 4-6, run diff -91, home 12-18, 4.3 RS/G / 5.7 RA/G

PLATOON MATCHUP
  MIL batting vs LHP:
    Team wRC+: 55 (ESTIMATED)
    Key bats: Jake Bauers 109, William Contreras 100, Brice Turang 62
    Weak bats: Sal Frelick 9, Luis Rengifo 2
  COL batting vs LHP:
    Team wRC+: 76 (ESTIMATED)
    Key bats: Hunter Goodman 96, Willi Castro 95, Kyle Karros 83
    Weak bats: Ezequiel Tovar 52, TJ Rumfield 52

STARTING PITCHERS
  Away: Shane Drohan (LHP) — 2-1, 2.87 ERA, 1.15 WHIP, 33 K, 31.1 IP
       FanG season:  xFIP 4.99 | SIERA 5.55 | K-BB% 3.1% | 6.2 IP (2025-26 blended)
       Last 14 days:  xFIP 3.55 | SIERA 3.70 | K/9 11.2 | BB/9 4.5 | 4.0 IP
  Home: Kyle Freeland (LHP) — 1-6, 8.06 ERA, 1.71 WHIP, 43 K, 48.0 IP
       FanG season:  xFIP 4.34 | SIERA 4.38 | K-BB% 12.1% | 210.2 IP (2025-26 blended)
       Last 14 days:  xFIP 4.75 | SIERA 4.51 | K/9 7.5 | BB/9 0.9 | 9.2 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- MIL
  Closer: Trevor Megill (R) -- 4.09 ERA, 31.1% K%, 8 SV, 6 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 10p | Mon - | Sun 13p(Sv)
  Setup: Abner Uribe (R) -- 4.03 ERA, 24.2% K%, 5 SV, 7 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 14p(H) | Mon - | Sun 12p(H)
  Setup: Aaron Ashby (L) -- 2.17 ERA, 32.9% K%, 2 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 29p(H) | Mon - | Sun -
  Taxed (30+ pitches last 2 days): Grant Anderson
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 2.87

BULLPEN -- COL
  Closer: Antonio Senzatela (R) -- 1.30 ERA, 20.0% K%, 3 SV, 2 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 17p(W,B) | Sun -
  Setup: Juan Mejia (R) -- 5.79 ERA, 23.8% K%, 3 SV, 4 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 16p | Mon - | Sun 21p
  Setup: Jaden Hill (R) -- 3.43 ERA, 24.5% K%, 10 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 16p(H) | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 4.12

WEATHER (Coors Field)
  93.8°F | 3.6 mph N | Clear sky | 0% rain

PARK: Coors Field
  Park factor: 114 (3yr) | HR: 106 | Runs: 130 -- hitter-friendly
  Altitude park (5,280 ft) -- significant run inflation expected

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 12 OF 15: Washington Nationals (WAS) @ Arizona Diamondbacks (AZ)
3:16 PM ET | Chase Field, Phoenix, AZ

ODDS
  Moneyline : WAS +113 / AZ -133  |  best: WAS +118 (BetRivers) / AZ -127 (LowVig.ag)
  Run Line  : WAS +1.5 (-181) / AZ -1.5 (+153)  |  best: -175 (LowVig.ag) / +164 (FanDuel)
  Total     : 8.0 — Over -115 / Under -105  |  best: Over -110 (Bovada) / Under -102 (FanDuel)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  WSH: 33-32 (.508), last10 5-5, run diff +8, away 21-12, 5.4 RS/G / 5.3 RA/G
  AZ: 33-31 (.516), last10 3-7, run diff -14, home 20-14, 4.3 RS/G / 4.6 RA/G

PLATOON MATCHUP
  WAS batting vs RHP:
    Team wRC+: 100 (ESTIMATED)
    Key bats: James Wood 175, CJ Abrams 171, Curtis Mead 155
    Weak bats: Brady House 50, Nasim Nuñez 24
  AZ batting vs RHP:
    Team wRC+: 85 (ESTIMATED)
    Key bats: Nolan Arenado 126, Corbin Carroll 122, Gabriel Moreno 112
    Weak bats: Alek Thomas 46, Jorge Barrosa 17

STARTING PITCHERS
  Away: Cade Cavalli (RHP) — 3-3, 3.62 ERA, 1.42 WHIP, 74 K, 64.2 IP
       FanG season:  xFIP 3.83 | SIERA 3.83 | K-BB% 14.7% | 113.1 IP (2025-26 blended)
       Last 14 days:  xFIP 3.02 | SIERA 3.52 | K/9 10.6 | BB/9 4.1 | 11.0 IP
  Home: Michael Soroka (RHP) — 7-3, 3.49 ERA, 1.19 WHIP, 66 K, 67.0 IP
       FanG season:  xFIP 3.83 | SIERA 3.63 | K-BB% 18.4% | 150.1 IP (2025-26 blended)
       Last 14 days:  xFIP 3.77 | SIERA 3.97 | K/9 6.8 | BB/9 0.8 | 12.0 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- WAS
  Closer: Clayton Beeter (R) -- 3.18 ERA, 24.3% K%, 4 SV, 2 HLD
    Usage last 6: Fri - | Thu - | Wed 28p(L) | Tue - | Mon - | Sun 16p(Sv)
  Setup: Brad Lord (R) -- 2.58 ERA, 20.8% K%, 3 HLD
    Usage last 6: Fri - | Thu - | Wed 29p | Tue - | Mon - | Sun -
  Setup: Orlando Ribalta (R) -- 1.65 ERA, 20.3% K%, 2 SV, 2 HLD
    Usage last 6: Fri - | Thu - | Wed 21p | Tue - | Mon - | Sun 29p(H)
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 4.34

BULLPEN -- AZ
  Closer: Paul Sewald (R) -- 3.47 ERA, 29.5% K%, 15 SV
    Usage last 6: Fri - | Thu 14p(W) | Wed - | Tue - | Mon 13p(Sv) | Sun -
  Setup: Kevin Ginkel (R) -- 2.96 ERA, 30.2% K%, 4 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 11p | Mon - | Sun 13p
  Setup: Juan Morillo (R) -- 2.52 ERA, 30.5% K%, 1 SV, 8 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue 19p | Mon - | Sun 31p
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 3.09

WEATHER (Chase Field)
  100.4°F | 9.7 mph SW | Mainly clear | 0% rain
  (Retractable roof — may be open or closed at game time)

PARK: Chase Field
  Park factor: 101 (3yr) | HR: 89 | Runs: 102
  Roof-closed factor: 104 -- use this value if roof confirmed closed at game time

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 13 OF 15: Los Angeles Angels (LAA) @ Los Angeles Dodgers (LAD)
4:11 PM ET | Dodger Stadium, Los Angeles, CA

ODDS
  Moneyline : LAA +177 / LAD -210  |  best: LAA +188 (BetRivers) / LAD -198 (LowVig.ag)
  Run Line  : LAA +1.5 (-118) / LAD -1.5 (-101)  |  best: -115 (LowVig.ag) / [price flagged as suspect — stale book data]
  Total     : 8.5 — Over -109 / Under -110  |  best: Over -105 (FanDuel) / Under -108 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time
  NOTE: Los Angeles Dodgers ML is heavy at -210. Their -1.5 run line at -101 may be a more efficient way to back them — consider it.

TEAM FORM
  LAA: 24-41 (.369), last10 3-7, run diff -59, away 11-23, 4.3 RS/G / 5.2 RA/G
  LAD: 42-23 (.646), last10 7-3, run diff +141, home 22-11, 5.2 RS/G / 3.1 RA/G

PLATOON MATCHUP
  LAA batting vs RHP:
    Team wRC+: 93 (ESTIMATED)
    Key bats: Mike Trout 146, Vaughn Grissom 125, Zach Neto 112
    Weak bats: Jo Adell 54, Logan O'Hoppe 44
  LAD batting vs RHP:
    Team wRC+: 115 (ESTIMATED)
    Key bats: Shohei Ohtani 163, Freddie Freeman 146, Dalton Rushing 134
    Weak bats: Alex Call 78, Mookie Betts 58

STARTING PITCHERS
  Away: José Soriano (RHP) — 6-4, 2.72 ERA, 1.21 WHIP, 85 K, 76.0 IP
       FanG season:  xFIP 3.58 | SIERA 3.98 | K-BB% 11.7% | 245.0 IP (2025-26 blended)
       Last 14 days:  xFIP 6.50 | SIERA 6.23 | K/9 10.2 | BB/9 10.2 | 9.2 IP
  Home: Emmet Sheehan (RHP) — 3-2, 4.50 ERA, 1.16 WHIP, 62 K, 58.0 IP
       FanG season:  xFIP 3.26 | SIERA 3.16 | K-BB% 22.9% | 117.2 IP (2025-26 blended)
       Last 14 days:  xFIP 3.91 | SIERA 3.68 | K/9 8.0 | BB/9 0.7 | 12.1 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- LAA
  Closer: Kirby Yates (R) -- 3.86 ERA, 29.3% K%, 1 SV
    Usage last 6: Fri - | Thu - | Wed 17p | Tue - | Mon 10p(L) | Sun -
  Setup: Sam Bachman (R) -- 2.22 ERA, 25.4% K%, 10 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon - | Sun -
  Setup: Chase Silseth (R) -- 1.74 ERA, 22.2% K%, 5 HLD
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 20p | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 3.88

BULLPEN -- LAD
  Closer: Tanner Scott (L) -- 2.42 ERA, 31.3% K%, 6 SV, 5 HLD
    Usage last 6: Fri - | Thu 8p(L) | Wed - | Tue 20p(Sv) | Mon - | Sun -
  Setup: Will Klein (R) -- 2.45 ERA, 25.2% K%, 1 SV, 8 HLD
    Usage last 6: Fri - | Thu 16p(H) | Wed - | Tue 23p(H) | Mon - | Sun 18p
  Setup: Alex Vesia (L) -- 2.14 ERA, 33.7% K%, 2 SV, 8 HLD
    Usage last 6: Fri - | Thu 12p(BS) | Wed - | Tue - | Mon 9p | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 3.59

WEATHER (Dodger Stadium)
  74.7°F | 9.2 mph SW | Clear sky | 0% rain

PARK: Dodger Stadium
  Park factor: 102 (3yr) | HR: 135 | Runs: 104

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 14 OF 15: New York Mets (NYM) @ San Diego Padres (SD)
4:11 PM ET | Petco Park, San Diego, CA

ODDS
  Moneyline : NYM -107 / SD -110  |  best: NYM -104 (BetOnline.ag) / SD -106 (BetOnline.ag)
  Run Line  : NYM -1.5 (+152) / SD +1.5 (-186)  |  best: +159 (DraftKings) / [price flagged as suspect — stale book data]
  Total     : 7.5 — Over -115 / Under -104  |  best: Over -106 (BetRivers) / Under [price flagged as suspect — stale book data]
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  NYM: 28-36 (.438), last10 6-4, run diff -9, away 13-21, 4.0 RS/G / 4.2 RA/G
  SD: 33-30 (.524), last10 2-8, run diff -14, home 17-17, 3.8 RS/G / 4.0 RA/G

PLATOON MATCHUP
  NYM batting vs RHP:
    Team wRC+: 96 (ESTIMATED)
    Key bats: Jared Young 192, Juan Soto 178, A.J. Ewing 119
    Weak bats: Bo Bichette 57, Tyrone Taylor 22
  SD batting vs RHP:
    Team wRC+: 83 (ESTIMATED)
    Key bats: Gavin Sheets 149, Ty France 138, Miguel Andujar 112
    Weak bats: Jake Cronenworth 58, Freddy Fermin 0

STARTING PITCHERS
  Away: Huascar Brazobán (RHP) — 3-1, 2.25 ERA, 1.00 WHIP, 26 K, 32.0 IP
       FanG season:  xFIP 5.50 | SIERA 5.72 | K-BB% 2.3% | 10.0 IP (2025-26 blended)
  Home: Randy Vásquez (RHP) — 5-3, 3.31 ERA, 1.22 WHIP, 50 K, 65.1 IP
       FanG season:  xFIP 5.25 | SIERA 5.15 | K-BB% 6.6% | 194.1 IP (2025-26 blended)
       Last 14 days:  xFIP 5.83 | SIERA 6.00 | K/9 4.2 | BB/9 1.7 | 10.2 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- NYM
  Closer: Devin Williams (R) -- 5.40 ERA, 34.8% K%, 8 SV
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon 18p | Sun -
  Setup: Luke Weaver (R) -- 2.67 ERA, 25.0% K%, 7 HLD
    Usage last 6: Fri - | Thu - | Wed 10p | Tue - | Mon 15p | Sun -
  Setup: Brooks Raley (L) -- 1.54 ERA, 27.0% K%, 10 HLD
    Usage last 6: Fri - | Thu - | Wed 16p | Tue - | Mon 19p(BS) | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 2.68

BULLPEN -- SD
  Closer: Mason Miller (R) -- 0.72 ERA, 51.0% K%, 17 SV
    Usage last 6: Fri - | Thu - | Wed - | Tue - | Mon - | Sun -
  Setup: Jason Adam (R) -- 1.71 ERA, 14.9% K%, 1 SV, 12 HLD
    Usage last 6: Fri - | Thu - | Wed 20p(L) | Tue 6p | Mon - | Sun 19p
  Setup: Adrian Morejon (L) -- 4.75 ERA, 27.3% K%, 1 SV, 11 HLD
    Usage last 6: Fri - | Thu 28p | Wed - | Tue - | Mon - | Sun 13p
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 2.80

WEATHER (Petco Park)
  70.5°F | 9.2 mph SW | Mainly clear | 0% rain

PARK: Petco Park
  Park factor: 94 (3yr) | HR: 94 | Runs: 88 -- pitcher-friendly

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════
GAME 15 OF 15: San Francisco Giants (SF) @ Chicago Cubs (CHC)
8:21 PM ET | Wrigley Field, Chicago, IL

ODDS
  Moneyline : SF +105 / CHC -119  |  best: SF +109 (BetUS) / CHC -117 (BetRivers)
  Run Line  : SF -1.5 (+165) / CHC +1.5 (-205)  |  best: +172 (DraftKings) / [price flagged as suspect — stale book data]
  Total     : 8.0 — Over -105 / Under -115  |  best: Over [price flagged as suspect — stale book data] / Under -113 (LowVig.ag)
  Line move : no movement yet — re-run fetch_odds.py closer to game time

TEAM FORM
  SF: 26-39 (.400), last10 4-6, run diff -49, away 14-23, 4.2 RS/G / 4.9 RA/G
  CHC: 34-31 (.523), last10 5-5, run diff +4, home 20-14, 4.6 RS/G / 4.6 RA/G

PLATOON MATCHUP
  SF batting vs RHP:
    Team wRC+: 109 (ESTIMATED)
    Key bats: Jung Hoo Lee 145, Casey Schmitt 134, Willy Adames 129
    Weak bats: Matt Chapman 86, Harrison Bader 31
  CHC batting vs RHP:
    Team wRC+: 105 (ESTIMATED)
    Key bats: Ian Happ 165, Michael Conforto 142, Michael Busch 132
    Weak bats: Dansby Swanson 81, Matt Shaw 59

STARTING PITCHERS
  Away: Trevor McDonald (RHP) — 2-3, 4.50 ERA, 1.15 WHIP, 31 K, 34.0 IP
       FanG season:  xFIP 2.98 | SIERA 3.06 | K-BB% 17.5% | 47.0 IP (2025-26 blended)
       Last 14 days:  xFIP 3.82 | SIERA 3.93 | K/9 7.9 | BB/9 4.0 | 11.1 IP
  Home: Jameson Taillon (RHP) — 2-5, 5.13 ERA, 1.26 WHIP, 57 K, 66.2 IP
       FanG season:  xFIP 4.43 | SIERA 4.38 | K-BB% 13.4% | 196.1 IP (2025-26 blended)
       Last 14 days:  xFIP 4.42 | SIERA 4.25 | K/9 7.9 | BB/9 2.4 | 11.1 IP

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- SF
  Closer: Keaton Winn (R) -- 2.30 ERA, 22.5% K%, 1 SV, 11 HLD
    Usage last 6: Fri - | Thu - | Wed 15p(Sv) | Tue - | Mon - | Sun -
  Setup: Erik Miller (L) -- 4.08 ERA, 32.1% K%, 2 SV, 8 HLD
    Usage last 6: Fri - | Thu - | Wed 11p(H) | Tue 14p | Mon - | Sun -
  Taxed (30+ pitches last 2 days): JT Brubaker
  High-leverage arms available: 0 of 1 fresh
  Bullpen ERA (season avg): 5.31

BULLPEN -- CHC
  Closer: Daniel Palencia (R) -- 1.98 ERA, 25.0% K%, 3 SV
    Usage last 6: Fri - | Thu - | Wed 15p | Tue 12p | Mon - | Sun -
  Setup: Jacob Webb (R) -- 2.45 ERA, 29.1% K%, 1 SV, 4 HLD
    Usage last 6: Fri - | Thu - | Wed 16p(H) | Tue - | Mon - | Sun -
  Setup: Caleb Thielbar (L) -- 4.05 ERA, 25.0% K%, 2 SV, 2 HLD
    Usage last 6: Fri - | Thu - | Wed 16p(BS) | Tue - | Mon - | Sun -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 5.44

WEATHER (Wrigley Field)
  71.7°F | 9.3 mph NE | Overcast | 6% rain

PARK: Wrigley Field
  Park factor: 98 (3yr) | HR: 108 | Runs: 96

PLATE UMPIRE: Not yet assigned

═══════════════════════════════════════════════════════

NOW MAKE YOUR PICKS.
Respond with one block per game — EVERY game, including passes and leans.
A pass is data, not a non-answer. Use this exact format:

## GAME: {AWAY_ABBR} @ {HOME_ABBR}
PICK: [team + ML, or team + RL, or Over, or Under, or PASS, or LEAN: side]
PRICE: [exact american odds e.g. -128, or N/A]
UNITS: [5 / 3 / 1 / LEAN / PASS]
EDGE: [THIN / REAL / STRONG / NONE]
REASON: [2-4 sentences in your own words]
LOOKED UP: [what you researched beyond the data, or "nothing, used provided data only"]

If you have a qualifying 2-leg parlay, add ONE block after the games:

## PARLAY
LEG 1: {team} ML {price}
LEG 2: {team} ML {price}
COMBINED PRICE: {parlay payout e.g. +195}
TRUE PROBABILITY ESTIMATE: {your estimate both legs win}
UNITS: [1 or 2 — parlays capped at 2 units maximum]
REASON: [why both legs have independent edge and are not correlated]

Then end with:

## SLATE SUMMARY
BEST BET: [single highest-conviction play, with game and units]
WHY THIS ONE: [1-2 sentences on why it beats your other picks]

Do not add any text outside these blocks.

═══════════════════════════════════════════════════════
MODEL-SPECIFIC INSTRUCTION
═══════════════════════════════════════════════════════

Before assigning 3 or more units to a bet involving a starting
pitcher, explicitly state the pitcher's FIP or xERA if available. If
you cannot justify the sustainability of the ERA, cap the bet at 1
unit or PASS. When citing line movement as a reason to bet a run line,
you must explicitly cross-reference the total line movement — if the
total has dropped significantly, you must explain why a multi-run
victory is still the most probable outcome in a low-scoring game
script before committing to the run line.
When your analysis identifies a starting pitcher with an xERA or FIP
that is 1.5+ runs higher than their ERA, you must explicitly evaluate
the opposing team's moneyline as a bet. Do not dismiss the edge by
saying the pitcher is "unpredictable" or an "unreliable anchor" --
bad underlying metrics are precisely what creates edge on the opponent.
Before betting a run line or assigning 2 or more units, explicitly
compare the pitcher's last-14-day K/9 and Hard Hit Rate (HH%) to their
season averages. If last-14 K/9 has dropped below 7.0 or HH% has spiked
above 40%, cap the bet at 1 unit or PASS regardless of how strong their
season xFIP appears.

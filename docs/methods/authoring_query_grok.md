You are joining an MLB betting experiment as an independent professional handicapper.
Each day you receive a standardized data slate and operate under fixed competition
rules. Within those rules, your handicapping method is entirely your own to design.
Below is (1) the competition rules you operate under, and (2) a representative sample
of the exact data you will receive each day. Design your own handicapping method for
finding betting edge in this data. Write it as a concise method document (target 400
words or fewer) you will follow each day. Be specific about what you weigh, what you
distrust, how you convert the data into a win-probability estimate, and what makes you
pass. This is YOUR system — do not reproduce a generic checklist. Output ONLY the
method document, no preamble.

---

## PART 1 — COMPETITION RULES (fixed for all competitors)

# SYSTEM INSTRUCTIONS -- AI CAPPER MLB
# Model: grok
# These instructions are sent as the system prompt on every call.

You are an independent professional sports bettor competing in a long-running
MLB forecasting experiment. You design and apply your own handicapping method.
There is no house methodology to follow. Do not try to reverse-engineer what
the operator wants — there is no preferred way to handicap.

Your objective is long-term unit-weighted ROI. You are not an analyst and not a
content producer. Passing is the correct action on most games. A slate with no
bet is a valid, often correct, outcome.

HOW YOU ARE SCORED
Performance is unit-weighted ROI measured against closing line value (CLV).
CLV is the strongest available indicator of process quality: short-term results
are noisy, and a losing wager with positive CLV can reflect better forecasting
than a winning wager with negative CLV. Your estimated probability, the implied
probability, and the gap are tracked across every bet to evaluate your
calibration over time.

WHAT IS FIXED (the competition rules — identical for every competitor):

EDGE GATE
A bet requires at least a 4 percentage-point gap between your estimated win
probability and the market's implied probability. Below 4 points: LEAN or PASS.

UNIT MAP
  Gap 4 to under 7 pts   -> 1 unit
  Gap 7+ pts, clean data -> 3 units (the ceiling; nothing rates higher)
  Gap under 4 pts        -> LEAN or PASS, zero stake

SLATE CEILINGS (hard, not targets)
  1-7 games:  1 bet max
  8-14 games: 2 bets max
  15+ games:  3 bets max

DATA INTEGRITY (non-negotiable)
  Either starter TBD             -> PASS that game.
  Starter flagged [small sample] -> no 3-unit play on that game.
  Price flagged stale/suspect    -> treat that market as absent.
  Postponed game                 -> PASS.

HOW YOU REASON IS YOURS
You decide how to weigh pitching, bullpen, offense, park, weather, line
movement, stake size relative to price, and anything else in the data. You
decide what matters and what to ignore. When you bet, state your win-probability
estimate and the gap as numbers so your calibration can be measured. Beyond
that, the method is yours to apply and defend using only the information
available in this slate.

OUTPUT FORMAT — MANDATORY, MACHINE-PARSED. NO DEVIATION.
One block per game, including passes. No text before the first ## GAME: block.
No prose between blocks. All reasoning lives in the REASON field.

## GAME: {AWAY_ABBR} @ {HOME_ABBR}
PICK: [team abbr + ML, or RL, or Over {line}, or Under {line}, or PASS, or LEAN: side]
PRICE: [exact American odds e.g. -128, or N/A for PASS]
UNITS: [3 / 1 / LEAN / PASS]
EDGE: [gap in percentage points e.g. "6.2 pts", or "none" for PASS]
TOTAL LEAN: [Over / Under / No lean]
REASON: [2-4 sentences, your own words]
LOOKED UP: [data gaps noted, or "nothing, used provided data only"]

Separate each block with ---

If you have a qualifying 2-leg parlay, add ONE block after all games:
## PARLAY
LEG 1: {team abbr} ML {price}
LEG 2: {team abbr} ML {price}
COMBINED PRICE: {parlay payout e.g. +195}
TRUE PROBABILITY ESTIMATE: {your estimate both legs win}
UNITS: [1 or 2 — capped at 2 units]
REASON: [why both legs have independent, uncorrelated edge]

End with:
## SLATE SUMMARY
BEST BET: [your 3-unit play and game, or "NO BEST BET -- no 3-unit play identified today"]
WHY THIS ONE: [1-2 sentences only if a 3-unit play exists]

START YOUR RESPONSE WITH ## GAME: — NOTHING BEFORE IT.

---

## PART 2 — SAMPLE DATA SLATE

═══════════════════════════════════════════════════════
MLB SLATE — Thursday, June 11 2026 (US Eastern Time)
8 games | Prompt built at 5:20 AM ET | Source: TheOddsAPI median of 9 books
═══════════════════════════════════════════════════════

GAME 1: AZ @ MIA  1:11 PM ET  loanDepot park, Miami, FL

  ML:-104/-112  RL:+153/-186  TT:8.5(-112/-107)
  best-ML:[price flagged as suspect — stale book data]/-110 (BetOnline.ag) best-TT:O-108 (FanDuel)/U-103 (LowVig.ag)
  Line move : ML unchanged | Total unchanged

TEAM FORM
  AZ 34-33 L10:3-7 rdiff:-22 away 13-19 RS/RA:4.3/4.6 L10RS:2.7 Brl%:7.2 HH%:38.1
  MIA 33-35 L10:7-3 rdiff:-8 home 22-16 RS/RA:4.3/4.4 L10RS:4.6 Brl%:6.3 HH%:37.6

PLATOON MATCHUP
  vs_RHP: wRC+:85(AGG) key:Moreno127,Carroll125,Arenado120
  vs_RHP: wRC+:89(AGG) key:Hicks134,Edwards130,Lopez111

STARTING PITCHERS
  Away: Merrill Kelly (RHP) — 5-4 | ERA 5.71 FIP 6.12 xERA 7.26 | K/9 5.7 HH% 44.1 Brl% 16.4 | 58.1 IP
       AGG: xFIP 4.17 SIERA 4.28 K-BB%:13.0% | Stf+: 91 242.1IP
       L14: xFIP 5.94 SIERA 5.52 K/9:5.2 BB/9:4.3 10.1IP
       L3: 7.0/2/4/2 | 5.1/2/2/2 | 5.0/7/4/3 L3ERA:5.71  (IP/ER/K/BB)
  Home: Tyler Phillips (RHP) — 0-1 | ERA 2.08 FIP 3.63 xERA 3.58 | K/9 7.5 HH% 34.8 Brl% 6.3 | 43.1 IP
       AGG: xFIP 3.88 SIERA 4.27 K-BB%:10.6% | Stf+: 93 11.1IP
       L14: xFIP 3.78 SIERA 4.24 K/9:3.6 BB/9:1.8 5.0IP
       L2: 3.2/0/4/2 | 5.0/3/2/1 L2ERA:3.12  (IP/ER/K/BB)

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- AZ
  Closer: Paul Sewald (R) -- 3.47 ERA, 29.5% K%, 15 SV
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat - | Fri -
  Setup: Kevin Ginkel (R) -- 2.81 ERA, 29.4% K%, 4 HLD
    Usage last 6: Wed - | Tue 8p | Mon - | Sun 16p | Sat - | Fri -
  Setup: Juan Morillo (R) -- 2.42 ERA, 31.2% K%, 1 SV, 8 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat 10p | Fri -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 3.10

BULLPEN -- MIA
  Closer: Pete Fairbanks (R) -- 7.00 ERA, 30.1% K%, 7 SV, 2 HLD
    Usage last 6: Wed - | Tue 24p(W) | Mon - | Sun - | Sat 39p(H) | Fri -
  Setup: Anthony Bender (R) -- 2.96 ERA, 28.7% K%, 2 SV, 6 HLD
    Usage last 6: Wed - | Tue 11p(H) | Mon - | Sun 24p(Sv) | Sat 22p | Fri -
  Setup: Michael Petersen (R) -- 3.42 ERA, 27.5% K%, 1 SV, 8 HLD
    Usage last 6: Wed - | Tue 26p | Mon - | Sun 17p(H) | Sat 26p | Fri -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 3 fresh
  Bullpen ERA (season avg): 4.72

WEATHER
  wx:unavailable

PARK: loanDepot park
  Park factor: 97 (3yr) | HR: 81 | Runs: 94
  Roof-closed factor: 100 -- use this value if roof confirmed closed at game time

PLATE UMPIRE: Not yet assigned

GAME 2: MIN @ DET  1:11 PM ET  Comerica Park, Detroit, MI

  ML:+106/-123  RL:-185/+158  TT:9.0(-122/+100)
  best-ML:+111 (BetOnline.ag)/-122 (FanDuel) best-TT:O-101 (DraftKings)/U+111 (LowVig.ag)
  Line move : ML unchanged | Total unchanged

TEAM FORM
  MIN 31-38 L10:4-6 rdiff:-30 away 13-20 RS/RA:4.6/5.0 L10RS:4.6 Brl%:8.4 HH%:36.2
  DET 28-40 L10:6-4 rdiff:-20 home 17-16 RS/RA:4.0/4.3 L10RS:5.3 Brl%:9.1 HH%:39.0

PLATOON MATCHUP
  vs_RHP: wRC+:95(AGG) key:Jeffers166,Buxton155,Larnach129
  vs_RHP: wRC+:93(AGG) key:Dingler154,McGonigle142,Greene141

STARTING PITCHERS
  Away: Zebby Matthews (RHP) — 2-3 | ERA 4.15 FIP 4.52 xERA 3.00 | K/9 7.7 HH% 36.9 Brl% 12.3 | 30.1 IP
       AGG: xFIP 3.91 SIERA 3.87 K-BB%:17.2% | Stf+: 100 109.2IP
       L14: xFIP 5.03 SIERA 5.07 K/9:7.2 BB/9:4.8 11.1IP
       L3: 6.0/3/6/1 | 4.1/7/7/2 | 7.0/2/2/4 L3ERA:6.23  (IP/ER/K/BB)
  Home: Keider Montero (RHP) — 2-4 | ERA 3.95 FIP 4.16 xERA 3.43 | K/9 6.0 HH% 42.6 Brl% 8.7 | 66.0 IP
       AGG: xFIP 4.69 SIERA 4.66 K-BB%:10.4% | Stf+: 96 124.0IP
       L14: xFIP 4.98 SIERA 4.84 K/9:4.1 BB/9:0.8 11.0IP
       L3: 5.2/4/7/1 | 6.0/0/4/0 | 5.0/4/1/1 L3ERA:4.32  (IP/ER/K/BB)

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- MIN
  Closer: Yoendrys Gómez (R) -- 3.90 ERA, 22.4% K%, 5 SV, 5 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat 14p | Fri -
  Setup: Anthony Banda (L) -- 4.66 ERA, 21.1% K%, 1 SV, 9 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat - | Fri 14p(H)
  Setup: Travis Adams (R) -- 7.43 ERA, 25.8% K%, 2 SV, 1 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat - | Fri 16p(Sv)
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 4.87

BULLPEN -- DET
  Closer: Will Vest (R) -- 6.53 ERA, 25.3% K%, 1 SV, 6 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 10p(W) | Sat - | Fri 18p
  Setup: Tyler Holton (L) -- 4.40 ERA, 20.0% K%, 5 HLD
    Usage last 6: Wed - | Tue 16p | Mon - | Sun 9p | Sat - | Fri 15p(H)
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 0 of 1 fresh
  Bullpen ERA (season avg): 4.61

WEATHER
  wx:79.3F Overcast wind:10.1mph W 3%rain

PARK: Comerica Park
  Park factor: 102 (3yr) | HR: 108 | Runs: 104

PLATE UMPIRE: Not yet assigned

GAME 3: STL @ NYM  1:11 PM ET  Citi Field, Flushing, NY

  ML:+120/-143  RL:-170/+145  TT:9.0(-105/-115)
  best-ML:+122 (FanDuel)/-135 (BetOnline.ag) best-TT:O-102 (LowVig.ag)/U-112 (BetRivers)
  Line move : ML +120->+121 | Total unchanged

TEAM FORM
  STL 37-28 L10:7-3 rdiff:+12 away 18-12 RS/RA:4.5/4.3 L10RS:5.3 Brl%:7.5 HH%:40.2
  NYM 29-38 L10:5-5 rdiff:-19 home 15-17 RS/RA:4.0/4.3 L10RS:4.4 Brl%:9.2 HH%:41.7

PLATOON MATCHUP
  vs_RHP: wRC+:96(AGG) key:Burleson167,Walker154,Wetherholt123
  vs_RHP: wRC+:93(AGG) key:Soto169,Young155,Ewing129

STARTING PITCHERS
  Away: Hunter Dobbins (RHP) — 1-0 | ERA 2.77 FIP 3.56 xERA — | K/9 9.7 HH% 57.1 Brl% 23.8 | 13.0 IP  [small sample — treat ERA with caution]
       AGG: xFIP 4.12 SIERA 4.34 K-BB%:10.8% | Stf+: 96 57.1IP
       L14: no data
       L1: 4.1/3/4/5 L1ERA:6.23  (IP/ER/K/BB)
  Home: Christian Scott (RHP) — 2-0 | ERA 2.50 FIP 3.10 xERA 4.23 | K/9 10.2 HH% 31.6 Brl% 3.9 | 36.0 IP
       AGG: xFIP 4.23 SIERA 4.09 K-BB%:14.7% | Stf+: 108 36.0IP
       L14: xFIP 3.94 SIERA 4.00 K/9:9.3 BB/9:3.4 10.2IP
       L3: 5.2/0/5/2 | 5.0/1/8/2 | 5.2/0/3/2 L3ERA:0.55  (IP/ER/K/BB)

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- STL
  Closer: Riley O'Brien (R) -- 3.68 ERA, 25.2% K%, 17 SV, 1 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 15p(Sv) | Sat 23p(Sv) | Fri -
  Setup: George Soriano (R) -- 3.08 ERA, 20.9% K%, 2 SV, 9 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 17p(BS) | Sat 13p(W) | Fri -
  Setup: JoJo Romero (L) -- 3.34 ERA, 24.0% K%, 17 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 8p | Sat - | Fri -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 3.83

BULLPEN -- NYM
  Closer: Devin Williams (R) -- 5.57 ERA, 35.1% K%, 8 SV
    Usage last 6: Wed - | Tue - | Mon - | Sun 20p | Sat - | Fri -
  Setup: Luke Weaver (R) -- 2.48 ERA, 23.3% K%, 7 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 18p | Sat - | Fri 7p
  Setup: Brooks Raley (L) -- 1.48 ERA, 28.2% K%, 10 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 14p | Sat - | Fri -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 2.95

WEATHER
  wx:94.0F Clear sky wind:9.0mph W 1%rain

PARK: Citi Field
  Park factor: 100 (3yr) | HR: 97 | Runs: 100

PLATE UMPIRE: Not yet assigned

GAME 4: TEX @ KC  2:11 PM ET  Kauffman Stadium, Kansas City, MO

  ML:+102/-119  RL:-185/+155  TT:10.0(-116/-103)
  best-ML:+104 (FanDuel)/-112 (BetOnline.ag) best-TT:O[price flagged as suspect — stale book data]/U[price flagged as suspect — stale book data]
  Line move : ML unchanged | Total unchanged

TEAM FORM
  TEX 33-34 L10:7-3 rdiff:+14 away 16-20 RS/RA:4.0/3.8 L10RS:4.7 Brl%:7.8 HH%:40.7
  KC 28-40 L10:6-4 rdiff:-48 home 16-18 RS/RA:3.9/4.6 L10RS:4.9 Brl%:8.5 HH%:41.8

PLATOON MATCHUP
  vs_RHP: wRC+:98(AGG) key:Jung140,Duran117,Pederson113
  vs_RHP: wRC+:90(AGG) key:Caglianone123,Jr.114,Pasquantino108

STARTING PITCHERS
  Away: Kumar Rocker (RHP) — 2-5 | ERA 3.54 FIP 4.15 xERA 4.62 | K/9 7.2 HH% 42.6 Brl% 7.7 | 61.0 IP
       AGG: xFIP 4.36 SIERA 4.49 K-BB%:10.0% | Stf+: 94 117.2IP
       L14: xFIP 5.30 SIERA 5.41 K/9:5.7 BB/9:3.3 11.0IP
       L3: 5.0/4/5/2 | 6.0/0/2/3 | 5.0/2/5/1 L3ERA:3.38  (IP/ER/K/BB)
  Home: Michael Wacha (RHP) — 4-4 | ERA 3.44 FIP 3.96 xERA 3.95 | K/9 7.4 HH% 38.0 Brl% 7.2 | 81.0 IP
       AGG: xFIP 4.46 SIERA 4.50 K-BB%:11.7% | Stf+: 96 253.2IP
       L14: xFIP 4.82 SIERA 5.15 K/9:5.9 BB/9:3.4 10.2IP
       L3: 7.0/2/5/2 | 5.0/6/5/4 | 5.2/4/2/0 L3ERA:6.11  (IP/ER/K/BB)

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- TEX
  Closer: Jacob Latz (L) -- 1.80 ERA, 27.3% K%, 10 SV, 2 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat - | Fri 35p(Sv)
  Setup: Jakob Junis (R) -- 1.57 ERA, 18.5% K%, 4 SV, 6 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat - | Fri -
  Setup: Cole Winn (R) -- 5.40 ERA, 25.3% K%, 1 SV, 5 HLD
    Usage last 6: Wed - | Tue 8p | Mon - | Sun - | Sat - | Fri -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 3.25

BULLPEN -- KC
  Closer: Alex Lange (R) -- 4.06 ERA, 25.2% K%, 4 SV, 1 HLD
    Usage last 6: Wed - | Tue 19p(Sv) | Mon - | Sun - | Sat 28p(Sv) | Fri -
  Setup: Lucas Erceg (R) -- 6.29 ERA, 19.0% K%, 12 SV, 2 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 15p(Sv) | Sat 15p | Fri -
  Setup: Daniel Lynch IV (L) -- 1.93 ERA, 25.4% K%, 1 SV, 8 HLD
    Usage last 6: Wed - | Tue 13p(H) | Mon - | Sun - | Sat 12p | Fri -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 4 fresh
  Bullpen ERA (season avg): 22.25

WEATHER
  wx:unavailable

PARK: Kauffman Stadium
  Park factor: 99 (3yr) | HR: 85 | Runs: 98

PLATE UMPIRE: Not yet assigned

GAME 5: CHC @ COL  3:11 PM ET  Coors Field, Denver, CO

  ML:-153/+130  RL:+100/-120  TT:11.0(-115/-106)
  best-ML:-145 (LowVig.ag)/+131 (LowVig.ag) best-TT:O[price flagged as suspect — stale book data]/U[price flagged as suspect — stale book data]
  Line move : ML unchanged | Total unchanged

TEAM FORM
  CHC 34-34 L10:3-7 rdiff:-2 away 14-19 RS/RA:4.5/4.6 L10RS:3.1 Brl%:7.9 HH%:40.3
  COL 26-42 L10:5-5 rdiff:-94 home 14-19 RS/RA:4.3/5.7 L10RS:5.7 Brl%:6.7 HH%:37.2

PLATOON MATCHUP
  vs_RHP: wRC+:104(AGG) key:Happ164,Conforto134,Busch130
  vs_RHP: wRC+:89(AGG) key:Moniak163,Johnston136,Goodman131

STARTING PITCHERS
  Away: Edward Cabrera (RHP) — 3-3 | ERA 4.99 FIP 4.89 xERA 4.47 | K/9 8.3 HH% 39.2 Brl% 12.0 | 57.2 IP
       AGG: xFIP 3.71 SIERA 3.84 K-BB%:16.2% | Stf+: 101 195.1IP
       L14: xFIP 2.63 SIERA 2.76 K/9:14.7 BB/9:2.5 3.2IP
       L3: 4.2/3/2/3 | 3.0/1/2/2 | 3.2/8/6/1 L3ERA:9.53  (IP/ER/K/BB)
  Home: Ryan Feltner (RHP) — 2-1 | ERA 4.22 FIP 4.72 xERA 6.32 | K/9 6.5 HH% 46.9 Brl% 13.6 | 32.0 IP
       AGG: xFIP 4.44 SIERA 4.57 K-BB%:9.8% | Stf+: 91 62.1IP
       L14: xFIP 4.31 SIERA 4.55 K/9:4.5 BB/9:1.5 12.0IP
       L3: 2.0/2/3/1 | 6.0/0/2/0 | 6.0/1/4/2 L3ERA:1.93  (IP/ER/K/BB)

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- CHC
  Closer: Daniel Palencia (R) -- 2.87 ERA, 23.9% K%, 3 SV
    Usage last 6: Wed - | Tue - | Mon - | Sun 16p | Sat 19p | Fri -
  Setup: Jacob Webb (R) -- 2.76 ERA, 27.8% K%, 1 SV, 4 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 7p | Sat 32p | Fri -
  Setup: Caleb Thielbar (L) -- 3.86 ERA, 27.1% K%, 2 SV, 3 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat 11p | Fri 13p
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 3 of 3 fresh
  Bullpen ERA (season avg): 5.58

BULLPEN -- COL
  Closer: Antonio Senzatela (R) -- 2.11 ERA, 21.5% K%, 3 SV, 2 HLD
    Usage last 6: Wed - | Tue 22p | Mon - | Sun - | Sat - | Fri 39p(BS)
  Setup: Juan Mejia (R) -- 6.23 ERA, 24.5% K%, 3 SV, 4 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat 19p | Fri 22p(L)
  Setup: Seth Halvorsen (R) -- 2.40 ERA, 20.6%, 2 HLD
    Usage last 6: Wed - | Tue 14p | Mon - | Sun - | Sat - | Fri 13p
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 5.78

WEATHER
  wx:76.4F Clear sky wind:9.4mph NE 0%rain

PARK: Coors Field
  Park factor: 114 (3yr) | HR: 106 | Runs: 130 -- hitter-friendly
  Altitude park (5,280 ft) -- significant run inflation expected
  (High-scoring environment -- margin-of-victory outcomes carry very high variance here.)

PLATE UMPIRE: Not yet assigned

GAME 6: LAD @ PIT  6:41 PM ET  PNC Park, Pittsburgh, PA

  ML:-161/+135  RL:+100/-120  TT:9.5(-105/-115)
  best-ML:-156 (FanDuel)/+146 (BetOnline.ag) best-TT:O[price flagged as suspect — stale book data]/U[price flagged as suspect — stale book data]
  Line move : ML unchanged | Total unchanged

TEAM FORM
  LAD 43-25 L10:6-4 rdiff:+141 away 21-13 RS/RA:5.4/3.3 L10RS:6.0 Brl%:10.0 HH%:41.3
  PIT 35-33 L10:5-5 rdiff:+22 home 19-16 RS/RA:5.1/4.8 L10RS:6.3 Brl%:8.1 HH%:40.6

PLATOON MATCHUP
  vs_RHP: wRC+:112(AGG) key:Ohtani163,Rushing158,Freeman153
  vs_LHP: wRC+:158(AGG) key:Reynolds177,Cruz139

STARTING PITCHERS
  Away: Justin Wrobleski (LHP) — 7-2 | ERA 2.62 FIP 3.27 xERA 3.84 | K/9 5.8 HH% 41.2 Brl% 7.2 | 68.2 IP
       AGG: xFIP 4.52 SIERA 4.59 K-BB%:10.4% | Stf+: 95 75.2IP
       L14: xFIP 2.33 SIERA 2.56 K/9:9.0 BB/9:0.0 13.0IP
       L3: 5.0/5/4/2 | 7.0/1/9/0 | 6.0/0/4/0 L3ERA:3.00  (IP/ER/K/BB)
  Home: Mitch Keller (RHP) — 5-3 | ERA 4.81 FIP 3.59 xERA 4.35 | K/9 6.8 HH% 38.8 Brl% 5.8 | 73.0 IP
       AGG: xFIP 4.18 SIERA 4.30 K-BB%:12.4% | Stf+: 94 249.1IP
       L14: xFIP 4.77 SIERA 4.51 K/9:9.3 BB/9:4.2 8.2IP
       L3: 6.0/1/5/3 | 4.0/7/5/1 | 4.2/6/4/3 L3ERA:8.59  (IP/ER/K/BB)

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- LAD
  Closer: Tanner Scott (L) -- 2.60 ERA, 30.8% K%, 6 SV, 5 HLD
    Usage last 6: Wed - | Tue 17p | Mon - | Sun - | Sat - | Fri 12p
  Setup: Will Klein (R) -- 2.33 ERA, 27.0% K%, 1 SV, 8 HLD
    Usage last 6: Wed - | Tue 21p(W) | Mon - | Sun - | Sat - | Fri -
  Setup: Alex Vesia (L) -- 2.86 ERA, 33.3% K%, 2 SV, 9 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 31p | Sat - | Fri -
  Taxed (30+ pitches last 2 days): Blake Treinen
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 4.38

BULLPEN -- PIT
  Closer: Gregory Soto (L) -- 3.38 ERA, 29.3% K%, 9 SV, 6 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat - | Fri -
  Setup: Dennis Santana (R) -- 5.00 ERA, 17.7% K%, 2 SV, 4 HLD
    Usage last 6: Wed - | Tue 31p | Mon - | Sun - | Sat - | Fri 7p
  Setup: Evan Sisk (L) -- 1.27 ERA, 31.3% K%, 3 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 26p(BS) | Sat - | Fri 28p
  Taxed (30+ pitches last 2 days): Dennis Santana, Brandan Bidois
  High-leverage arms available: 2 of 3 fresh
  Bullpen ERA (season avg): 4.38

WEATHER
  wx:80.1F Overcast wind:17.0mph SW 18%rain

PARK: PNC Park
  Park factor: 98 (3yr) | HR: 75 | Runs: 96

PLATE UMPIRE: Not yet assigned

GAME 7: SEA @ BAL  7:06 PM ET  Oriole Park at Camden Yards, Baltimore, MD

  ML:-114/-104  RL:+144/-170  TT:8.5(-110/-110)
  best-ML:-107 (BetOnline.ag)/-102 (FanDuel) best-TT:O-110 (FanDuel)/U-102 (LowVig.ag)
  Line move : ML unchanged | Total unchanged

TEAM FORM
  SEA 36-33 L10:6-4 rdiff:+28 away 17-17 RS/RA:4.2/3.8 L10RS:4.0 Brl%:8.7 HH%:39.3
  BAL 32-37 L10:5-5 rdiff:-30 home 20-17 RS/RA:4.7/5.1 L10RS:5.8 Brl%:8.4 HH%:43.4

PLATOON MATCHUP
  vs_RHP: wRC+:118(AGG) key:Donovan186,Arozarena158,Canzone152
  vs_RHP: wRC+:109(AGG) key:Rutschman143,Basallo139,Holliday128

STARTING PITCHERS
  Away: Bryan Woo (RHP) — 5-4 | ERA 3.74 FIP 2.96 xERA 2.91 | K/9 8.8 HH% 43.6 Brl% 6.7 | 77.0 IP
       AGG: xFIP 3.43 SIERA 3.35 K-BB%:21.5% | Stf+: 110 263.2IP
       L14: xFIP 1.79 SIERA 2.04 K/9:10.8 BB/9:0.0 13.1IP
       L3: 4.2/4/4/2 | 7.0/0/9/0 | 6.1/5/7/0 L3ERA:4.50  (IP/ER/K/BB)
  Home: Kyle Bradish (RHP) — 3-7 | ERA 3.89 FIP 4.24 xERA 4.01 | K/9 8.8 HH% 37.4 Brl% 11.0 | 69.1 IP
       AGG: xFIP 3.68 SIERA 3.85 K-BB%:16.1% | Stf+: 101 101.1IP
       L14: xFIP 4.52 SIERA 5.04 K/9:5.7 BB/9:4.9 11.0IP
       L3: 6.0/1/3/2 | 7.0/0/4/3 | 4.0/5/3/3 L3ERA:3.18  (IP/ER/K/BB)

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- SEA
  Closer: Andrés Muñoz (R) -- 5.18 ERA, 34.3% K%, 10 SV
    Usage last 6: Wed - | Tue - | Mon 20p(Sv) | Sun 19p(L,B) | Sat - | Fri -
  Setup: José A. Ferrer (L) -- 2.10 ERA, 19.7% K%, 3 SV, 8 HLD
    Usage last 6: Wed - | Tue 43p(W,B) | Mon - | Sun 18p(H) | Sat 15p | Fri -
  Taxed (30+ pitches last 2 days): José A. Ferrer
  High-leverage arms available: 0 of 2 fresh
  Bullpen ERA (season avg): 2.94

BULLPEN -- BAL
  Closer: Rico Garcia (R) -- 1.29 ERA, 31.0% K%, 4 SV, 8 HLD
    Usage last 6: Wed - | Tue 15p(L) | Mon - | Sun 13p | Sat - | Fri -
  Setup: Andrew Kittredge (R) -- 7.24 ERA, 23.1% K%, 2 HLD
    Usage last 6: Wed - | Tue 19p | Mon - | Sun - | Sat - | Fri -
  Setup: Yennier Cano (R) -- 2.38 ERA, 21.2% K%, 4 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun 10p | Sat - | Fri 16p
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 6.06

WEATHER
  wx:unavailable

PARK: Oriole Park at Camden Yards
  Park factor: 103 (3yr) | HR: 115 | Runs: 106

PLATE UMPIRE: Not yet assigned

GAME 8: ATL @ CHW  7:41 PM ET  Guaranteed Rate Field, Chicago, IL

  ML:-119/-100  RL:+139/-167  TT:8.5(-113/-108)
  best-ML:-116 (FanDuel)/[price flagged as suspect — stale book data] best-TT:O-108 (FanDuel)/U-105 (DraftKings)
  Line move : ML unchanged | Total unchanged

TEAM FORM
  ATL 45-23 L10:6-4 rdiff:+114 away 23-12 RS/RA:5.1/3.5 L10RS:4.3 Brl%:9.5 HH%:40.2
  CWS 36-31 L10:6-4 rdiff:+10 home 22-11 RS/RA:4.7/4.6 L10RS:5.2 Brl%:9.2 HH%:39.9

PLATOON MATCHUP
  (home starter hand unknown -- showing both splits)
  vs_LHP: wRC+:151(AGG) key:Baldwin201,Olson135,II135
  vs_RHP: wRC+:123(AGG) key:Olson154,Jr.147,II145
  vs_LHP: wRC+:151(AGG) key:Vargas226,Meidroth167,Murakami127

STARTING PITCHERS
  Away: Martín Pérez (LHP) — 4-3 | ERA 3.02 FIP 3.98 xERA 4.32 | K/9 7.5 HH% 42.0 Brl% 7.7 | 56.2 IP
       AGG: xFIP 4.71 SIERA 4.77 K-BB%:8.9% | Stf+: 86 100.0IP
       L14: xFIP 4.51 SIERA 5.08 K/9:6.3 BB/9:4.5 10.0IP
       L3: 5.2/1/2/2 | 5.0/2/2/3 | 5.0/3/5/2 L3ERA:3.45  (IP/ER/K/BB)
  Home: TBD
  NOTE: TBD starter -- pass on this game unless starter confirmed before your submission. Do not estimate edge without confirmed pitcher data.

LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time

BULLPEN -- ATL
  Closer: Raisel Iglesias (R) -- 1.21 ERA, 30.6% K%, 13 SV
    Usage last 6: Wed - | Tue 24p(L) | Mon - | Sun - | Sat 20p(Sv) | Fri 20p(Sv)
  Setup: Robert Suarez (R) -- 0.61 ERA, 22.5% K%, 4 SV, 10 HLD
    Usage last 6: Wed - | Tue 7p | Mon - | Sun - | Sat - | Fri 10p(H)
  Setup: Dylan Lee (L) -- 1.16 ERA, 34.8% K%, 13 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat 20p(H) | Fri 12p(H)
  Taxed (30+ pitches last 2 days): Dylan Dodd
  High-leverage arms available: 1 of 3 fresh
  Bullpen ERA (season avg): 2.04

BULLPEN -- CHW
  Closer: Seranthony Domínguez (R) -- 3.60 ERA, 27.6% K%, 11 SV, 2 HLD
    Usage last 6: Wed - | Tue 13p | Mon - | Sun - | Sat - | Fri 11p
  Setup: Sean Newcomb (L) -- 2.29 ERA, 22.9% K%, 1 SV, 5 HLD
    Usage last 6: Wed - | Tue - | Mon - | Sun - | Sat 29p(H) | Fri -
  Taxed (30+ pitches last 2 days): none
  High-leverage arms available: 1 of 1 fresh
  Bullpen ERA (season avg): 5.33

WEATHER
  wx:81.9F Thunderstorm wind:12.6mph S 27%rain

PARK: Guaranteed Rate Field
  Park factor: 98 (3yr) | HR: 100 | Runs: 96

PLATE UMPIRE: Not yet assigned


BEFORE SUBMITTING: verify each bet clears the 4-pt minimum edge gate.
Apply slate ceiling, team quality check, and small-sample checks.

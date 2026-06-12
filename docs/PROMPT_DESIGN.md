# PROMPT DESIGN — AI CAPPER
# Last updated: 2026-06-10

This document shows the exact prompt template as it appears when `build_prompt.py`
generates a prompt. It is the reference for reviewing or modifying the prompt format.

The prompt is divided into four parts:
1. **Header** — date, game count, data freshness
2. **Instructions** — fixed text sent to every model on every slate
3. **Game blocks** — one block per game, repeated for every game on the slate
4. **Output format** — the required response structure that `log_picks.py` will parse

Generated prompts are saved to `daily/{sport}/{date}/prompt.md`.

---

## PART 1 — HEADER

```
═══════════════════════════════════════════════════════
MLB SLATE — Wednesday, June 3 2026 (US Eastern Time)
15 games | Prompt built at 10:10 PM ET | Source: TheOddsAPI median of 9 books
═══════════════════════════════════════════════════════
```

**Dynamic fields:**
- Sport label (MLB / NBA / NHL / NFL)
- Weekday, month, day, year of the slate (US Eastern Time)
- Game count
- Build time (shows how fresh the data is — if built at 4 AM ET, umpires won't be assigned yet)
- Book count (max across all games — typically 9)

---

## PART 2 — INSTRUCTIONS (fixed text, same every day)

```
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

  3 units = STRONG PLAY. Clear, identified market mispricing.
            Minimum 7-point probability gap. Confirmed clean data.
            Rare -- a few times per week across all models combined.
            This is the ceiling. There is no higher rating.
  1 unit  = STANDARD PLAY. Real but ordinary edge. 4-7 point gap.
            The most common published rating.
  LEAN    = Slight lean exists. Gap under 4 points. Zero stake.
            Noted in the log. Never published as a bet.
  PASS    = No edge found. The correct answer on most games.

STAKING DISCIPLINE:

  Before assigning any bet, state three things explicitly:
    (a) Your estimated win probability as a percentage
    (b) The implied probability of the offered price
        (implied prob = 100 / (100 + positive_odds) for underdogs,
         or |negative_odds| / (|negative_odds| + 100) for favourites)
    (c) The gap between (a) and (b) in percentage points

  Then apply this hard mapping. No exceptions:
    Gap under 4 points       -> LEAN or PASS. Never a bet.
    Gap 4-7 points           -> 1 unit maximum
    Gap 7+ points, confirmed clean data -> 3 units maximum

  3 units is the ceiling. There is no higher rating.
  Narrative richness does not increase units. A bet with six supporting
  factors but a 5-point gap is a 1-unit bet. If your gap and your desired
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

BULLPEN FATIGUE RULE:

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
  2-LEG PARLAY — you MAY suggest ONE 2-leg moneyline parlay, but only if:

    Both legs are independently identified as having edge in your game-by-game
    analysis (never parlay games you would otherwise pass)
    Neither leg is shorter than -180 individually
    The games have no obvious correlation (not same division, not both
    weather-affected, not the same travel pattern)
    A parlay is optional — only include it if it genuinely adds value
```

**Notes:**
- The `{sport_label}` substitution makes the opening line adapt to NBA/NHL when those scripts are added.
- The "heavy favourites" note was added in Task 2. Threshold is -180. See `build_prompt.py:_heavy_fav_notes()`.
- The plus-money dog language was intentional — we want models to consider underdogs with genuine edge.
- The parlay rules are strict: both legs must have independent edge, neither shorter than -180.
- **TOTALS APPROACH** instruction block is appended after the PARLAY rules (before game blocks). It requires models to state a TOTAL LEAN (Over / Under / No lean) for every game regardless of whether they place a side bet. Uses a 7-step sequence: baseline RS/G estimate (using L10 RS/G where available), park factor adjustment, starter quality adjustment (xFIP), bullpen fatigue adjustment, wind adjustment, gap threshold (0.8+ runs = lean, 1.2+ = potential bet), and line movement. Expanded 2026-06-08 to add L10 RS/G, wind guidance, retractable-roof park-factor direction, and opener/small-sample adjustments.

---

## PART 3 — GAME BLOCK (one per game, repeated)

```
═══════════════════════════════════════════════════════
GAME {N} OF {TOTAL}: {Away Team} ({AWAY}) @ {Home Team} ({HOME})
{H:MM PM} ET | {Venue}, {City}

ODDS
  Moneyline : {AWAY} {away_ml} / {HOME} {home_ml}  |  best: {AWAY} {away_best} ({book}) / {HOME} {home_best} ({book})
  Run Line  : {AWAY} +1.5 ({away_rl_price}) / {HOME} -1.5 ({home_rl_price})  |  best: {away_best} ({book}) / {home_best} ({book})
  Total     : {line} — Over {over_price} / Under {under_price}  |  best: Over {over_best} ({book}) / Under {under_best} ({book})
  Line move : ML {away_open}->{away_now} / {home_open}->{home_now} | Total {total_open}->{total_now}
  [NOTE: ML moved toward {ABBR} by {N} pts — possible roster/lineup change...]
                                                     (only when move > 30 pts)
  [NOTE: {Team} ML is heavy at {ml}. Their -1.5 run line at {rl_price} is plus-money ... — consider it.]
                                                     (only when ML heavier than -180)

TEAM FORM
  {AWAY}: {W}-{L} ({pct}), last10 {w}-{l}, run diff {+/-n}, away {W}-{L}, {rs_g} RS/G / {ra_g} RA/G, L10 RS/G {n}
  {HOME}: {W}-{L} ({pct}), last10 {w}-{l}, run diff {+/-n}, home {W}-{L}, {rs_g} RS/G / {ra_g} RA/G, L10 RS/G {n}

PLATOON MATCHUP                                      [only when FanGraphs static files are loaded]
  {AWAY} batters vs {H}HP:  wRC+ {n} | wOBA {n} | OPS {n}  (team aggregate)
  {HOME} batters vs {H}HP:  wRC+ {n} | wOBA {n} | OPS {n}  (team aggregate)
  (Side omitted when pitcher hand is unknown/TBD. Shows CONFIRMED lineup wRC+ stats when
   lineups are confirmed; falls back to SEASON AGGREGATE from splits_vs_LHP/RHP.txt)

STARTING PITCHERS
  Away: {Name} ({H}HP) — {W}-{L} | ERA {era} FIP {fip} xERA {xera} | K/9 {k9} HH% {hh} Brl% {brl} | {ip} IP
        Season: xFIP {n} | SIERA {n} | K-BB% {n}%                    [from FanGraphs static]
        Last 14d: ERA {n} | FIP {n} | K% {n}% BB% {n}% | {ip} IP     [from FanGraphs static]
        Last 3 starts: {Mon D} vs {OPP} {ip} IP {er} ER | ... | L3 ERA: {era}
  Home: {Name} ({H}HP) — {W}-{L} | ERA {era} FIP {fip} xERA {xera} | K/9 {k9} HH% {hh} Brl% {brl} | {ip} IP
        Season: xFIP {n} | SIERA {n} | K-BB% {n}%
        Last 14d: ERA {n} | FIP {n} | K% {n}% BB% {n}% | {ip} IP
        Last 3 starts: {Mon D} vs {OPP} {ip} IP {er} ER | ... | L3 ERA: {era}
  (FIP omitted if components missing. xFIP/SIERA/K-BB% omitted if pitcher not in FanGraphs
   static files. Last-3-starts line only appears when fetch_pitcher_advanced.py has run.)

LINEUPS (confirmed)                                  [only when fetch_lineups.py has run + confirmed]
  {AWAY}: {C.Name POS}, {C.Name POS}, {C.Name POS}, {C.Name POS}, {C.Name POS} ...
  {AWAY} IL: {Name POS}, {Name POS}
  {HOME}: ...
  {HOME} IL: none
LINEUPS: not yet confirmed — run fetch_lineups.py closer to game time
                                                     [shows when fetch ran but too early]
  (Section omitted entirely when fetch_lineups.py has never run)

BULLPEN -- {AWAY}                                    [static FanGraphs data preferred; fetch_bullpen.py fallback]
  {Name} (CL) — IP {n} | ERA {n} | K% {n}% | {Jun 5} {n}p | {Jun 4} {n}p | ...
  {Name} (SU) — IP {n} | ERA {n} | K% {n}% | {Jun 5} {n}p | {Jun 4} {n}p | ...
BULLPEN -- {HOME}
  ...
  (Static Bullpen.txt shows role, ERA, K%, and last 6 days pitch counts with actual dates.
   Falls back to fetch_bullpen.py format — closer + taxed relievers — when static absent.)

WEATHER ({Venue})
  {temp}°F | {wind_mph} mph {wind_dir} | {conditions} | {precip}% rain
  (Retractable roof — if open, use outdoor park factors; if closed, use roof-closed park factors shown below.)
                                                     [only if roof=retractable]
  [PPD RISK: {n}% precipitation — postponement possible]
                                                     [only if roof=outdoor AND precip >= 50%]
  {Venue} — indoor dome, weather not applicable             [only if roof=dome]

PARK FACTORS ({Venue})                               [only when FanGraphs static files are loaded]
  Overall {n} | R {n} | HR {n} | H {n} | 2B {n} | 3B {n} | BB {n}  (3yr, all conditions)
  Roof closed: Overall {n} | HR {n} | H {n}                          [only if retractable roof]
  (100 = league average. >100 = hitter-friendly, <100 = pitcher-friendly.)

PLATE UMPIRE: {Name or "Not yet assigned"}
```

**Real example — Game 7, CLE @ NYY, June 3 2026 (with all sections populated):**

```
═══════════════════════════════════════════════════════
GAME 7 OF 15: Cleveland Guardians (CLE) @ New York Yankees (NYY)
7:06 PM ET | Yankee Stadium, Bronx, NY

ODDS
  Moneyline : CLE +141 / NYY -160  |  best: CLE +145 (LowVig.ag) / NYY -155 (BetRivers)
  Run Line  : CLE +1.5 (-157) / NYY -1.5 (+135)  |  best: -151 (MyBookie.ag) / +140 (BetRivers)
  Total     : 7.5 — Over +100 / Under -120  |  best: Over +102 (DraftKings) / Under +107 (LowVig.ag)
  Line move : ML +141->+110 | Total unchanged
  [NOTE: ML moved toward CLE by 31 pts — possible roster/lineup change. Treat pitcher
  and lineup data as potentially stale and verify if you have web access.]

TEAM FORM
  CLE: 34-27 (.557), last10 5-5, run diff +1, away 17-13, 4.1 RS/G / 4.1 RA/G
  NYY: 36-23 (.610), last10 6-4, run diff +98, home 17-9, 5.2 RS/G / 3.5 RA/G

STARTING PITCHERS
  Away: Gavin Williams (RHP) — 8-3 | ERA 3.07 FIP 2.91 xERA 3.41 | K/9 10.4 HH% 33.1 Brl% 6.2 | 76.1 IP
        Last 3 starts: Jun 1 vs HOU 6.0 IP 1 ER | May 27 vs CLE 5.2 IP 3 ER | May 21 vs DET 7.0 IP 0 ER | L3 ERA: 2.45
  Home: Gerrit Cole (RHP) — 1-0 | ERA 0.00 FIP 1.84 xERA 2.89 | K/9 8.6 HH% 28.4 Brl% 4.1 | 12.2 IP
        Last 1 start: Jun 1 vs BOS 12.2 IP 0 ER | L1 ERA: 0.00  [small sample]

LINEUPS (confirmed)
  CLE: S.Kwan LF, J.Gimenez 2B, J.Ramírez 3B, J.Naylor 1B, T.Hedges C ...
  CLE IL: none
  NYY: J.Soto RF, A.Judge DH, G.Torres SS, A.Verdugo LF, A.Rizzo 1B ...
  NYY IL: G.Stanton DH, T.Trevino C

BULLPEN
  CLE: ERA 3.41 | Closer: E.Clase (available)
       No heavy usage last 2 days
  NYY: ERA 3.88 | Closer: C.Holmes (available)
       Taxed: R.Marinaccio (38p yesterday)

WEATHER (Yankee Stadium)
  71.4°F | 10.2 mph SE | Clear sky | 1% rain

PLATE UMPIRE: Phil Cuzzi
```

**Data sources per field:**

| Field | Source | Script |
|---|---|---|
| Moneyline / Run Line / Total (consensus) | TheOddsAPI — median of N books | `fetch_odds.py` |
| best: price (book) | TheOddsAPI — max price across all books | `fetch_odds.py` |
| Line move | Opening snapshot vs current snapshot | `fetch_odds.py` (run twice) |
| Large move flag (> 30 pts) | Computed from snapshot diff | `build_prompt.py:_big_move_note()` |
| Heavy-favourite NOTE | Computed from moneyline > -180 | `build_prompt.py:_heavy_fav_notes()` |
| Team form (season record, run diff, L10 W-L) | MLB Stats API `/standings?hydrate=team,record` | `fetch_teamstats.py` |
| L10 RS/G (last-10-games runs scored per game) | MLB Stats API `/teams/{id}/stats?stats=gameLog` | `fetch_teamstats.py` |
| Starting pitchers (season) | MLB Stats API `/schedule?hydrate=probablePitcher` + `/people/{id}` | `fetch_pitchers.py` |
| Pitcher advanced (xERA, HH%, Brl%, K/9) | Baseball Savant via pybaseball | `fetch_pitcher_advanced.py` |
| FIP | Computed from HR, BB, HBP, K, IP via FIP formula | `fetch_pitcher_advanced.py` |
| Pitcher last-3-starts rolling form | MLB Stats API `/people/{id}/stats?stats=gameLog` | `fetch_pitcher_advanced.py` |
| Confirmed lineups + batting order | MLB Stats API `/game/{gamePk}/lineups` | `fetch_lineups.py` |
| IL absences | MLB Stats API `/teams/{teamId}/roster?rosterType=40Man` | `fetch_lineups.py` |
| Bullpen ERA + reliever usage (fallback) | MLB Stats API boxscores last 3 days | `fetch_bullpen.py` |
| Bullpen role / usage / ERA / K% (preferred) | FanGraphs `Bullpen.txt` (manual download) | `load_static_data.py:load_bullpen()` |
| Platoon splits (wRC+/wOBA/OPS vs LHP/RHP) | FanGraphs `splits_vs_LHP.txt`, `splits_vs_RHP.txt` | `load_static_data.py` |
| Home/away batter splits | FanGraphs `splits_home.txt`, `splits_away.txt` | `load_static_data.py` |
| Starter xFIP / SIERA / K-BB% (season) | FanGraphs `pitchers_xfip_siera.txt` (manual download) | `load_static_data.py:load_pitchers_season()` |
| Starter last-14-day stats | FanGraphs `pitchers_last14.txt` (manual download) | `load_static_data.py:load_pitchers_last14()` |
| Park factors (all conditions) | FanGraphs `park_factors_all.txt` (manual download) | `load_static_data.py:load_park_factors()` |
| Park factors (roof closed) | FanGraphs `park_factors_roof_closed.txt` (manual download) | `load_static_data.py:load_park_factors_roof_closed()` |
| Weather | Open-Meteo API (by stadium lat/lon) | `fetch_weather.py` |
| Plate umpire | MLB Stats API `/game/{gamePk}/boxscore` | `fetch_umpires.py` |

**TEAM FORM split logic:**
- Away team shows their **away record** (road performance is the relevant context)
- Home team shows their **home record** (home performance is the relevant context)

---

## PART 4 — OUTPUT FORMAT (required response structure)

```
NOW MAKE YOUR PICKS.
Respond with one block per game — EVERY game, including passes and leans.
A pass is data, not a non-answer. Use this exact format:

## GAME: {AWAY_ABBR} @ {HOME_ABBR}
PICK: [team + ML, or team + RL, or Over, or Under, or PASS, or LEAN: side]
PRICE: [exact american odds e.g. -128, or N/A]
UNITS: [3 / 1 / LEAN / PASS]
EDGE: [gap in percentage points e.g. "6.2 pts" -- or "none" for PASS]
TOTAL LEAN: [Over / Under / No lean — required for every game]
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
```

**Why this structure:**

| Field | Purpose |
|---|---|
| `## GAME: TOR @ ATL` | Parse anchor — `log_picks.py` splits on `## GAME:` to get one chunk per game |
| `PICK:` | Side — maps to team name + market type. Standardised values only. |
| `PRICE:` | Odds at pick time — stored for CLV calculation when closing lines are fetched |
| `UNITS:` | Stake tier — used for unit-weighted ROI calculation |
| `EDGE:` | Probability gap in percentage points -- e.g. "6.2 pts". Enables quantitative calibration tracking. Replaces THIN/REAL/STRONG/NONE label system as of v3.1. |
| `TOTAL LEAN:` | Model's totals assessment — every game, even PASS games. Enables tracking of totals accuracy vs side accuracy independently |
| `REASON:` | Kept for display and model comparison — not parsed numerically |
| `LOOKED UP:` | Transparency field -- models state what external information they referenced beyond the prompt data. Web search is currently disabled at the API level for all models; this field will show 'nothing, used provided data only' for all automated models until web search is re-enabled. |
| `## PARLAY` | Optional — only included when both legs independently have edge |
| `## SLATE SUMMARY` | Best bet must be a 3-unit play. If no 3-unit play exists, outputs "NO BEST BET -- no 3-unit play identified today". Never elevated from 1-unit plays. The headline number for the leaderboard. |

---

## KNOWN BEHAVIOURS

- **Line move row shows "no movement yet"** when `fetch_odds.py` has only been run once that day. Run it again in the afternoon to see actual movement.
- **Large move flag** fires when the ML moves > 30 pts between opening and current snapshot. Signals possible late roster/injury news. Defined in `build_prompt.py:_big_move_note()`.
- **Umpire shows "Not yet assigned"** when built before ~1-2 hours before first pitch. Re-run `fetch_umpires.py` then `build_prompt.py` to update.
- **Heavy-favourite NOTE** fires when any team's ML is strictly worse than -180. Threshold defined in `build_prompt.py:_heavy_fav_notes()`.
- **TBD pitchers** appear when MLB Stats API hasn't published the probable starter yet. Normal early in the day for afternoon games. PLATOON MATCHUP omits the side where the pitcher hand is unknown.
- **Last-3-starts line** appears only when `fetch_pitcher_advanced.py` has run. Omitted silently if fewer than 1 start exists.
- **xFIP/SIERA/K-BB% lines** appear only when the pitcher is found in `pitchers_xfip_siera.txt`. Matched via fuzzy name matching (difflib). Omitted silently if not found.
- **Last-14-days line** shows "no data" if the pitcher is in the season file but absent from the last-14 file (e.g. pitched recently but less than 14 days of data). Omitted entirely if not in either file.
- **PLATOON MATCHUP** omitted entirely when `load_static_data.py` files are missing. When lineups are confirmed, shows per-player wRC+ labeled CONFIRMED; otherwise shows team-aggregate from splits files labeled SEASON AGGREGATE (not ESTIMATED — the data is real FanGraphs data, just not lineup-specific).
- **BULLPEN -- {TEAM} header format** (not "BULLPEN" on a shared line) — each team gets its own BULLPEN header. Static FanGraphs data preferred over fetch_bullpen.py data when both are available.
- **PARK FACTORS** omitted entirely when `park_factors_all.txt` is missing. Roof-closed row only appears when the venue has a retractable roof AND `park_factors_roof_closed.txt` has data for that team.
- **LINEUPS section omitted entirely** when `fetch_lineups.py` has not run. Shows "not yet confirmed" when it ran but lineups aren't posted yet (normal for morning runs). Lineups typically post 2-3 hours before first pitch.
- **Dome weather** shows a one-line note instead of a forecast. Open-Meteo is not called for dome stadiums.
- **Retractable roof** gets an actionable park-factor guidance line appended: "if open, use outdoor park factors; if closed, use roof-closed park factors shown below." This replaced a generic caveat that didn't tell models what to do with the ambiguity.
- **Rain/PPD risk flag** appears on outdoor stadium games when precipitation probability is >= 50%. Shows as `[PPD RISK: N% precipitation — postponement possible]`. Not shown for dome or retractable-roof stadiums.
- **STAKING DISCIPLINE** is a fixed instruction block in Part 2 (after PROFESSIONAL STANDARD, before MINIMUM EDGE GATE) requiring models to state win probability, implied probability, and gap in percentage points before assigning any bet. Applies a hard gap-to-units mapping: gap <4 = LEAN or PASS, gap 4-7 = 1 unit max, gap 7+ with clean data = 3 units max. 3 units is the ceiling.
- **RUN LINE RULE** is a fixed instruction block in Part 2 (after STAKING DISCIPLINE) requiring models to state P(win) and P(win by 2+) as separate independent estimates before betting any -1.5 run line. ML implied probability may not serve as run line justification.
- **UNDERDOG CHECK** is a fixed instruction block in Part 2 (after RUN LINE RULE) prohibiting models from calling a plus-money underdog "fair" without writing a numeric win probability estimate and comparing to implied probability. Also requires a named concrete structural blocker before downgrading an affirmed edge to PASS.
- **BULLPEN FATIGUE RULE** is a fixed instruction block in Part 2 (after UNDERDOG CHECK) requiring models to count fresh high-leverage arms (closer + setup men not used yesterday) for each team, state the delta, and add 4+ percentage points to underdog win probability if the delta favours the dog by 2+. Also requires a 5-point probability adjustment before passing on any plus-money underdog when the opponent's closer or 2+ relievers pitched the previous day.
- **TOTALS APPROACH** is a fixed instruction block in Part 2 (before game blocks) directing models to synthesise L10 RS/G, park factors, wind, starter quality, and bullpen depth into a TOTAL LEAN for every game. Models are required to state Over / Under / No lean for every game regardless of whether they place a side bet. A 0.8+ run gap between estimate and posted total is a lean; a 1.2+ run gap is a potential 1-unit bet. Two-factor minimum: a lean converts to a bet only when at least two of the five totals factors (park, starter quality, bullpen, wind, run-scoring environment) independently support the same direction.
- **TEAM QUALITY CHECK** is a fixed instruction block in Part 2 (after TOTALS APPROACH, before game blocks) requiring models to state the gap in run differential, RS/G, and last-10 record for both teams, and downgrade any pick by one tier if the bet team trails in two or more of these three metrics without a named override factor.
- **SMALL SAMPLE CHECK** is a fixed instruction block in Part 2 (after TEAM QUALITY CHECK) requiring models to cite at least one non-ERA indicator (K/9, K-BB%, Brl%, or L3 ERA trend) before betting any starter marked [small sample], and prohibiting 3+ units or Best Bet designation on those starters.
- **OPENER/BULK FLAG** is a fixed instruction block in Part 2 (after SMALL SAMPLE CHECK) requiring models to reframe any starter with 5.0 or fewer total IP as a bullpen game and evaluate the full bullpen quality instead of the listed starter's stats.
- **ESTIMATED DATA RULE** is a fixed instruction block in Part 2 (after OPENER/BULK FLAG) explaining the two platoon data labels: CONFIRMED (from actual lineup) and SEASON AGGREGATE (FanGraphs team-level data). SEASON AGGREGATE may be cited as one supporting signal but not the primary bet justification. Requires corroboration with at least one independent signal before committing units.
- **Postponed games** are handled automatically by `grade_picks.py`: any game with status "postponed", "cancelled", or "suspended" is graded VOID and returns 0 units (no win, no loss). Models are instructed in the output format block to log postponed games as PASS with REASON: "Postponed — no result."
- **PROFESSIONAL BETTOR framing** is the opening identity block in Part 2. It replaces "You are an expert MLB betting analyst" with an explicit professional bettor identity, framing passing as the expected default and volume as a warning sign. Added v3.1 to address systematic over-betting identified in first 7 days of validation.
- **PROFESSIONAL STANDARD** is a fixed instruction block in Part 2 (after UNIT SCALE, before STAKING DISCIPLINE) establishing that 85-90% pass rate is the professional baseline and that finding 1 genuine bet on a 15-game slate is a strong day. Multiple 3-unit plays on the same slate is flagged as a calibration error.
- **MINIMUM EDGE GATE** is a fixed instruction block in Part 2 (after STAKING DISCIPLINE, before RUN LINE RULE) establishing 4 percentage points as the hard floor for any bet. Below 4 points is always LEAN or PASS regardless of narrative support, price attractiveness, or line movement.
- **SLATE DISCIPLINE CHECK** is a fixed instruction block in Part 2 (after OPENER/BULK FLAG, before ESTIMATED DATA RULE) setting hard bet ceilings: 1 bet max on 1-7 game slates, 2 bets max on 8-14 game slates, 3 bets max on 15+ game slates. Includes a self-audit filter: drop by gap (<5 pts), then by data quality (unconfirmed/estimated), then by inability to name a specific market inefficiency without referencing team quality or record.
- **Heavy chalk ceiling**: any moneyline shorter than -150 is capped at 1 unit maximum regardless of gap size. Applied in DeepSeek model instruction; noted here for tracking.
- **TBD starter auto-pass**: DeepSeek model instruction requires an automatic PASS on any game where either starter is listed TBD at pick time. Other models apply this as judgment.
- **BEST BET rule tightened (v3.1)** -- best bet must be a 3-unit play. If no game clears 3 units, the SLATE SUMMARY outputs "NO BEST BET -- no 3-unit play identified today". A 1-unit play is never elevated to best bet regardless of how it compares to other picks.
- **EDGE field changed to numeric (v3.1)** -- EDGE field now requires a specific percentage point gap (e.g. "6.2 pts") instead of the label system (THIN/REAL/STRONG/NONE). Enables quantitative calibration tracking in grades. Note: log_picks.py parser may need updating to handle numeric values in this field if it currently validates against the label enum.

---

## MODIFYING THE PROMPT

To change the **instructions** (unit scale, odds philosophy, parlay rules): edit the `build_prompt()` function in `scripts/build_prompt.py`, the `parts.append(...)` block for Part 2.

To change **game block layout**: edit `build_game_block()` in `scripts/build_prompt.py`.

To change the **output format**: edit the `parts.append(...)` block for Part 4 in `build_prompt()`. Note that `log_picks.py` parses on `## GAME:`, `PICK:`, `PRICE:`, `UNITS:`, `EDGE:`, `TOTAL LEAN:` — changing these field names requires matching changes in the parser. The `TOTAL LEAN` field was added 2026-06-08 to capture totals assessments for all games including passes.

To add a **new data section** (e.g. bullpen stats): add a fetch script → write to `context` in `games.json` → add a `fmt_*()` helper in `build_prompt.py` → insert into `build_game_block()`.

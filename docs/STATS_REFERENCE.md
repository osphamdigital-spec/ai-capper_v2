# STATS REFERENCE — AI CAPPER

All statistics currently used across every section of the daily prompt.
Organised by sport, then by data category. When a new sport is added, add a new
top-level section for it below MLB.

**How to read this doc:**
- **Stat** — the field name as it appears in the prompt or in `games.json`
- **What it means** — plain-language definition
- **Source** — where the number comes from
- **Why it matters** — how the AI should use it

---

## MLB

### ODDS & MARKET DATA
*Source: TheOddsAPI — consensus median of up to 9 books + best available per book*
*Script: `fetch_odds.py`*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Moneyline** | American odds to win the game outright. Negative = favourite, positive = underdog. | Core pick market. Gap between implied probability and your edge estimate = bet size. |
| **Run Line** | Always ±1.5 runs at a price. Favourite is -1.5, underdog is +1.5. | When a ML favourite is heavy (-200+), the -1.5 RL is often plus-money and more efficient. |
| **Total** | The over/under line (e.g. 8.5 runs). Over and Under each have a price. | Primary totals market. Use with park factors, weather, and platoon data. |
| **Opening snapshot** | The odds captured on the first fetch of that day — proxy for where the market opened. | Baseline for measuring line movement. Earlier fetch = better opening proxy. |
| **Current snapshot** | Most recent fetch. | Compared against opening to detect movement. |
| **Line movement (ML)** | Change in moneyline from opening to current, shown as `open→now`. | Consistent sharp money usually moves in one direction. 30+ pt move flags possible news. |
| **Line movement (Total)** | Change in the total line from opening to current. | Movement toward Over or Under signals where sharp money is going. |
| **Large move flag** | Auto-generated NOTE when ML moves >30 pts. Identifies which team received the money. | Signals possible late roster/injury news not yet reflected in the data. Treat all data as stale. |
| **Heavy-favourite flag** | Auto-generated NOTE when any team's ML is worse than -180. | Prompts consideration of the -1.5 Run Line as a more efficient way to back a heavy favourite. |
| **Best available** | Highest price found across all books for each side/market. | Shopping lines at the best price adds expected value independent of pick quality. |
| **Book count** | Number of bookmakers the consensus was drawn from. | Fewer books = less reliable consensus. |

---

### TEAM FORM
*Source: MLB Stats API `/standings?hydrate=team,record`*
*Script: `fetch_teamstats.py`*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **W-L record** | Season wins and losses. | Overall team quality baseline. |
| **Win pct** | W / (W + L), shown as .xxx. | Normalises record across unequal game counts. |
| **Last 10** | Wins and losses in the last 10 games. | Short-form signal — catches a team trending up or down before the season record shows it. |
| **Run differential** | Runs scored minus runs allowed across the season. | Better than W-L for measuring true team strength — luck-neutral. |
| **Home record** | W-L only in home games (shown for the home team). | Home advantage is real in MLB. A team that is 30-10 at home is a different beast than 10-30. |
| **Away record** | W-L only in road games (shown for the away team). | Some teams travel well; others collapse on the road. |
| **RS/G** | Runs scored per game. | Offensive quality at a glance. |
| **RA/G** | Runs allowed per game. | Combined pitching + defence quality. |

---

### STARTING PITCHERS — SEASON STATS
*Sources: MLB Stats API (ERA/WHIP/K/IP/W-L/hand) + Baseball Savant via pybaseball (advanced)*
*Scripts: `fetch_pitchers.py`, `fetch_pitcher_advanced.py`*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Hand** | L (left) or R (right). | Determines platoon matchup — opposite-hand hitters perform better. |
| **W-L** | Season wins and losses. | Context only — wins are pitcher-luck-heavy. Never bet primarily on W-L. |
| **ERA** | Earned run average (earned runs per 9 innings). | Baseline, but inflated by defence and luck. Always read alongside FIP and xERA. |
| **FIP** | Fielding Independent Pitching. Formula: `(13×HR + 3×(BB+HBP) - 2×K) / IP + 3.10`. | Strips out defence. Better ERA estimator than ERA itself. FIP >> ERA = likely lucky. FIP << ERA = likely unlucky. |
| **xERA** | Statcast expected ERA based on contact quality (exit velocity, launch angle). | Independent of outcomes — pure contact quality signal. Converging FIP + xERA = strong evidence. |
| **K/9** | Strikeouts per 9 innings. | Swing-and-miss ability. High K/9 = limits damage even when balls are in play. |
| **HH%** | Hard Hit % — share of balls in play classified as hard contact (exit velo ≥ 95 mph). | Measures how well the pitcher suppresses damaging contact. Lower is better. |
| **Brl%** | Barrel % — share of batted balls with optimal exit velo + launch angle for extra bases. | Best single-metric indicator of allowing home runs. Below 5% = excellent. Above 10% = concerning. |
| **IP** | Innings pitched this season. | Sample size. Below 30 IP = small sample — attached `[small sample]` flag. |
| **Small sample flag** | Shown when IP < 30. | All season stats are less predictive with small samples. Weight recent starts higher. |

---

### STARTING PITCHERS — FANGRAPHS ADVANCED
*Source: FanGraphs manual download — `pitchers_xfip_siera.txt`, `pitchers_last14.txt`*
*Script: `load_static_data.py`*
*Update frequency: Season file weekly; Last-14 file every 2-3 days*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **xFIP** | Expected FIP — same as FIP but replaces actual HR with expected HR based on fly ball rate × league HR/FB. | More stable than FIP because HR/FB is noisy. Best long-run ERA estimator. |
| **SIERA** | Skill-Interactive ERA — factors in ground ball rate, strikeouts, and walks. | Most sophisticated ERA estimator available. Accounts for pitcher-profile differences FIP misses. |
| **K-BB%** | Strikeout rate minus walk rate. | Single best in-season pitching quality metric. >15% = strong, <5% = concerning. |
| **BB/9** | Walks per 9 innings. | Command metric. High BB/9 pitchers walk themselves into trouble and inflate pitch counts. |
| **Last-14 ERA** | ERA over the trailing 14 days. | Catches recent fatigue, mechanical changes, or injury. Divergence from season ERA = recency signal. |
| **Last-14 FIP** | FIP over the trailing 14 days. | If last-14 FIP is low but ERA is high, pitcher has been unlucky recently — likely to improve. |
| **Last-14 K%** | Strikeout rate last 14 days. | Velocity/stuff check. Falling K% often precedes ERA deterioration. |
| **Last-14 BB%** | Walk rate last 14 days. | Command check. Rising BB% signals mechanical issues. |
| **Last-14 IP** | Innings in the last 14 days. | Sample size for the recent-form stats. |

---

### STARTING PITCHERS — RECENT STARTS
*Source: MLB Stats API game log endpoint*
*Script: `fetch_pitcher_advanced.py`*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Last 3 starts** | Date, opponent, IP, and ER for each of the last 3 outings. | Context behind the season numbers — catches a pitcher who had a bad blowup start that inflated ERA, or a dominant recent run not yet in the season line. |
| **Rolling ERA (L3)** | ERA computed across the last 3 starts only. | Quick form signal. Compare to season ERA: if L3 << season, pitcher is trending up. If L3 >> season, trending down. |

---

### PLATOON MATCHUP
*Source: FanGraphs batter splits — `splits_vs_LHP.txt`, `splits_vs_RHP.txt`*
*Script: `load_static_data.py`*
*Update frequency: Weekly*

Logic: Away batters face the HOME pitcher → their stats vs that hand are shown.
Home batters face the AWAY pitcher → their stats vs that hand are shown.
When lineups are confirmed, individual batter stats are shown. Otherwise, team aggregate.

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **wRC+** | Weighted Runs Created Plus — offensive production relative to league average (100 = avg). | Best single offensive metric. Accounts for park and league. >120 = excellent, <80 = weak. |
| **wOBA** | Weighted On-Base Average — linear weights for each way to reach base. | More accurate than OBP or SLG. League average ~.320. |
| **OPS** | On-base % + Slugging %. | Widely understood baseline. Less precise than wRC+ but useful for context. |
| **PA** | Plate appearances in the split. | Sample size. Shown as `(small sample)` when PA < 50. |
| **K%** | Strikeout rate in the split. | Platoon-specific whiff tendency. High K% vs a handedness = vulnerable. |
| **BB%** | Walk rate in the split. | On-base discipline. |
| **AVG** | Batting average in the split. | Legacy metric — least useful, included for context. |
| **Team wRC+** | Average wRC+ across the lineup (or confirmed order) vs that pitcher hand. | Quick read on how dangerous this lineup is today against this pitcher type. |
| **Key bats** | Top 3 individual wRC+ in the matchup. | Identifies who is especially dangerous or vulnerable in the specific platoon context. |
| **Weak bats** | Bottom 2 individual wRC+ in the matchup. | Tells the pitcher where to hunt for outs. |

---

### TEAM OFFENSIVE CONTACT QUALITY
*Source: FanGraphs manual download -- `team_barrels.txt`*
*Script: `load_static_data.py` -- `load_team_barrels()`*
*Update frequency: Weekly (or when significant roster changes occur)*
*Season: Current season only (2026)*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Brl%** | Barrel % -- share of batted balls with optimal exit velocity and launch angle. Team offensive aggregate. | Measures how dangerous a lineup is at generating extra-base damage. Above 9% = potent offense. Below 6% = contact-dependent. Compare against opposing pitcher's allowed Brl% for a matchup read. |
| **HardHit%** | Hard Hit % -- share of batted balls at exit velocity >= 95 mph. Team offensive aggregate. | Corroborates Brl%. A team with high HH% but low Brl% hits the ball hard but flat -- gap power without home run pop. |

Remap note: FanGraphs uses WSN for Washington; pipeline remaps to WSH
to match games.json abbreviations. All other teams match directly.

---

### BULLPEN — STATIC (PREFERRED)
*Source: FanGraphs manual download — `Bullpen.txt`*
*Script: `load_static_data.py`*
*Update frequency: Daily (re-download before each session)*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Role** | CL (Closer), SU (Setup), MR (Middle Relief), LR (Long Relief). | Role = leverage. The closer is used in the 9th; setup men in the 7th-8th. Middle relievers mop up. |
| **Last 6 days usage** | Pitch count on each of the last 6 days (blank = didn't pitch). | Core fatigue signal. A pitcher used 3 days in a row or 40+ pitches yesterday is likely unavailable or diminished. |
| **Pitches last appearance** | Pitch count in their most recent outing. | High pitch counts (40+) require more recovery time. |
| **ERA (season)** | Bullpen ERA for the full season. | Quality baseline. Below 3.50 = strong; above 4.50 = concerning. |
| **K%** | Strikeout rate for the reliever. | Swing-and-miss ability in high-leverage. Elite relievers typically 30%+ K%. |
| **BB/9** | Walks per 9 innings. | Command. High BB/9 relievers expand strike zones and create trouble. |
| **SV** | Saves this season. | Confirms who the closer actually is (vs projected). |
| **HLD** | Holds this season. | Confirms setup men role. |

---

### BULLPEN — DYNAMIC FALLBACK
*Source: MLB Stats API boxscores, last 3 days*
*Script: `fetch_bullpen.py`*
*Used only when `Bullpen.txt` static data is unavailable*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Team bullpen ERA** | Aggregate ERA across all relievers this season. | Quick-read pen quality. |
| **Closer name + availability** | Identified from saves leaders + boxscore recency. | Key in save situations. Unavailable closer = opportunity for weaker arms. |
| **Taxed relievers** | Names + reason (pitch count or consecutive days). | Core availability signal. A taxed pen = consider betting on early runs before they tire, or fading the team in close games. |

---

### LINEUPS & INJURIES
*Source: MLB Stats API — `/game/{gamePk}/lineups` and `/teams/{teamId}/roster?rosterType=40Man`*
*Script: `fetch_lineups.py`*
*Availability: Confirmed ~2-3 hours before first pitch*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Batting order** | First 5 batters shown (abbreviated name + position). | Identifies who is actually playing today, batting order, and whether key players are sitting. |
| **IL absences** | Players currently on the Injured List. | A missing middle-of-order bat can reduce expected runs by 0.5-1.0. Shown even when empty ("none"). |
| **Status** | "confirmed" or "not yet confirmed". | Morning lineups are not real — teams often shuffle before game time. |

---

### WEATHER
*Source: Open-Meteo API (by stadium lat/lon)*
*Script: `fetch_weather.py`*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Temperature (°F)** | Game-time temperature at the stadium. | Cold (<50°F) suppresses offence and favours unders. Heat (>90°F) boosts offence slightly. |
| **Wind speed (mph)** | Game-time wind at the stadium. | 10+ mph affects fly balls; 15+ significantly affects homer rates. |
| **Wind direction** | Cardinal direction the wind is blowing TOWARD. | Blowing out (toward CF) = huge hitter advantage. Blowing in = pitcher advantage. Swirling = unpredictable. |
| **Precipitation %** | Chance of rain at game time. | Rain delays affect bullpen arms (pitchers cool down). Over 50% = possible postponement. |
| **Conditions** | Sky description (clear, overcast, fog, etc.). | Overcast + humid can deaden the ball. |
| **Roof type** | Outdoor / Dome / Retractable. | Dome = weather not applicable. Retractable = check roof status closer to game time. |

---

### PARK FACTORS
*Source: FanGraphs manual download — `park_factors_all.txt`, `park_factors_roof_closed.txt`*
*Script: `load_static_data.py`*
*Update frequency: Once per season (3-year rolling averages)*

All factors are indexed to 100 = league average. Above 100 = inflated for that stat, below 100 = suppressed.

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Overall park factor** | General run-scoring environment vs league average. | Single best summary of whether this park helps hitters or pitchers. |
| **HR factor** | Home run rate at this park vs average. | Parks like Coors (high) and Petco (low) have dramatic HR effects. |
| **Runs factor** | Run-scoring rate at this park. | Directly feeds over/under assessment. Petco at 92 = expect 8% fewer runs than average. |
| **wOBA factor** | Contact quality environment. | More granular than runs factor — accounts for park effects on hit quality. |
| **Roof-closed factor** | Park factor specifically when the retractable roof is closed. | Chase Field with the roof closed plays very differently to open. Use this when roof is confirmed shut. |
| **Altitude note** | Coors Field only — 5,280 ft elevation produces significant run inflation. | Coors is the most extreme park factor in baseball. Always expect more runs. |

---

### PLATE UMPIRE
*Source: MLB Stats API — `/game/{gamePk}/boxscore`*
*Script: `fetch_umpires.py`*
*Availability: Assigned ~1-2 hours before first pitch; inferred before then*

| Stat | What it means | Why it matters |
|------|--------------|----------------|
| **Name** | Plate umpire for this game. | Some umpires call tight zones (fewer walks, more Ks → lower scoring) or wide zones (more walks → higher scoring). |
| **Status** | "assigned" (confirmed) or "inferred" (crew rotation estimate, ~85% accurate). | An inferred ump is useful context but treat with less confidence than assigned. |

---

### PLANNED ADDITIONS (NOT YET IN PIPELINE)

| Stat | Source | Status |
|------|--------|--------|
| **Stuff+** | FanGraphs | Deferred -- data access barrier under review |
| **Whiff Rate** | FanGraphs / Baseball Savant | Deferred -- data access barrier under review |
| **Predicted lineups** | FanGraphs Roster Tracker | Deferred -- IL absences and platoon sits |

---

## NBA
*(Coming — season starts Oct)*

Stats to add when the NBA pipeline is built:
- Team offensive rating / defensive rating
- Pace (possessions per game)
- Effective field goal % (eFG%)
- Player PER or BPM
- Rest days / back-to-back flags
- Home/away splits
- Spread + ML + total markets

---

## NHL
*(Coming — season starts Oct)*

Stats to add when the NHL pipeline is built:
- Goals for / against per game
- Power play % / penalty kill %
- Save % (starting goalie)
- Shot attempts / Corsi (puck possession)
- Back-to-back flags
- Home/away splits
- Puck line + ML + total markets

---

## NFL / NCAAF / NCAAB
*(Coming — respective seasons)*

---

## STAT GLOSSARY — QUICK REFERENCE

| Abbreviation | Full name |
|---|---|
| ERA | Earned Run Average (runs per 9 IP) |
| FIP | Fielding Independent Pitching |
| xERA | Expected ERA (Statcast contact quality) |
| xFIP | Expected FIP (using expected HR/FB rate) |
| SIERA | Skill-Interactive ERA |
| K% | Strikeout rate (strikeouts / plate appearances) |
| BB% | Walk rate (walks / plate appearances) |
| K-BB% | Strikeout rate minus walk rate |
| K/9 | Strikeouts per 9 innings |
| BB/9 | Walks per 9 innings |
| HH% | Hard Hit % (exit velo ≥ 95 mph) |
| Brl% | Barrel % (optimal exit velo + angle) |
| IP | Innings Pitched |
| wRC+ | Weighted Runs Created Plus (100 = league avg) |
| wOBA | Weighted On-Base Average |
| OPS | On-base + Slugging |
| PA | Plate Appearances (sample size) |
| AVG | Batting Average |
| ML | Moneyline |
| RL | Run Line (MLB) or Puck Line (NHL) |
| RS/G | Runs Scored per Game |
| RA/G | Runs Allowed per Game |
| SV | Saves |
| HLD | Holds |
| CL | Closer (bullpen role) |
| SU | Setup man (bullpen role) |
| IL | Injured List |

Create a new file at docs/DATA_ARCHITECTURE.md with exactly 
this content:

SOURCE PRIORITY HIERARCHY

ODDS
1. TheOddsAPI
2. Manual override (admin only)

MLB PITCHERS
1. MLB official source
2. Covers

WEATHER
1. Covers
2. Weather API (future)

UMPIRES
1. Covers

RESULTS
1. Official league source
2. Manual verification (admin only)

TEAM NAMES
1. Official league naming
2. TheOddsAPI naming
3. Internal abbreviation lookup table

GAME STATUS
1. Official league source
2. TheOddsAPI

---

ADDITIONAL TRACKING REQUIREMENTS

The Game object must support long-term model performance tracking.

Each model pick should record:
- model name
- submitted timestamp
- sport
- game_id
- bet type
- bet side
- odds at pick time
- units
- action (bet / lean / pass)
- result (win / loss / push / void)
- profit_units
- CLV
- closing line
- reasoning

Passes and leans must be tracked, not discarded.

Reason: The site is evaluating model behaviour, not just winning 
bets. A model that passes frequently should have measurable pass 
statistics. A model that issues many leans should have measurable 
lean statistics.

---

MODEL STATISTICS TO CALCULATE

For each model:
- Bets placed
- Passes
- Leans
- Wins
- Losses
- Pushes
- Void picks
- Win %
- Unit-weighted ROI
- Units risked
- Units won/lost
- Average stake size
- Average CLV
- Positive CLV %
- 1-unit record
- 3-unit record
- 5-unit record
- MLB record
- NBA record
- NFL record
- NHL record
- NCAAF record
- NCAAB record

---

CALIBRATION TRACKING

The system must be able to answer:
Do 5-unit plays outperform 3-unit plays?
Do 3-unit plays outperform 1-unit plays?

If not, the model's staking system is not calibrated.

Unit level must always be stored permanently even after grading.

---

CONSENSUS TRACKING

Consensus picks stored as their own object.

Fields:
- date
- sport
- game_id
- side
- agreeing_models
- model_count
- average_units
- result
- profit_units

Consensus performance tracked separately from individual model 
performance.

---

STRONGEST PLAY TRACKING

Store the daily strongest play as its own object.

Fields:
- date
- model
- game_id
- bet
- units
- result
- profit_units

This allows reporting:
- strongest play record
- strongest play ROI
- strongest play CLV

---

SKIP DAY TRACKING

Store every skipped day.

Fields:
- date
- sport
- reason
- active_games
- models_reporting

Examples:
- all models pass
- insufficient clean data
- slate unavailable
- data source failure

Skip days are part of the public record and should be queryable.

---

DESIGN RULE

Never store only today's state.

Every pick, pass, lean, consensus, strongest play, result and 
skip day must be historically queryable because the leaderboard, 
ROI calculations, calibration analysis and transparency claims 
all depend on permanent historical records.

Confirm it saved and show me the file path.
# AI CAPPER — TIMEZONE STANDARD & OPERATING PROCEDURE
**Version:** 1.0
**Last Updated:** May 29, 2026
**Purpose:** Eliminate all timezone confusion. One rule, followed every day.

---

## THE ONE RULE

**Always use the date shown on mlb.com/schedule as the canonical slate date.**
Your local Australian date is irrelevant. Ignore it entirely when building prompts.

---

## THE AEST TO US ET CONVERSION

| Your time (AEST) | US ET equivalent | MLB.com shows |
|---|---|---|
| Friday 6 AM | Thursday 4 PM | Thursday slate (games starting soon) |
| Friday 12 PM | Thursday 10 PM | Thursday slate (mid-game or finishing) |
| Friday 6 PM | Friday 4 AM | Friday slate posted, no games started |
| Friday 8 PM | Friday 6 AM | Friday slate — ideal build window |
| Friday 11 PM | Friday 9 AM | Friday slate — still pre-game |
| Saturday 6 AM | Friday 4 PM | Friday slate — first games starting |
| Saturday 12 PM | Friday 10 PM | Friday slate — mid-game or finishing |
| Saturday 6 PM | Saturday 4 AM | Saturday slate posted |

**AEST = ET + 14 hours (EDT daylight saving) or ET + 15 hours (EST standard, Nov-Mar)**

---

## THE GOLDEN BUILD WINDOW

**Friday 6 PM – 11 PM AEST = Friday 4 AM – 9 AM ET**

This is when:
- MLB.com shows the Friday US slate
- Zero games have started (earliest Friday game is ~1 PM ET = 3 AM AEST Saturday)
- Probable pitchers are confirmed
- Odds are live and final lines are close to what you'll bet
- Maximum time before first pitch

**Do your prompt build during this window every day.**
The equivalent window exists every day: Australian evening = US morning of that same calendar date.

---

## HOW TO CONFIRM THE CORRECT SLATE

**Step 1:** Open mlb.com/schedule on your device.

**Step 2:** Read the date at the top. That is today's MLB slate date. Write it down.

**Step 3:** Confirm at least 2 games show "Preview" or a future time. If most show "Live" or "Final" — you are too late. Move to the next day's slate.

**Step 4:** That MLB.com date goes into every field in the prompt. Never your local date.

---

## THE DAILY DATA PULL SEQUENCE

Run these in order, record the data, paste into the prompt:

| Step | Source | What to pull | URL |
|---|---|---|---|
| 1 | MLB.com | Confirmed slate date + all matchups + start times | mlb.com/schedule |
| 2 | Covers.com | Moneylines, run lines, totals, opening lines | covers.com/sport/baseball/mlb/odds |
| 3 | Covers.com | Game-time weather for all outdoor stadiums | covers.com/sport/mlb/weather |
| 4 | Covers.com | Plate umpire assignments | covers.com/sport/baseball/mlb/umpires |
| 5 | MLB.com or Rotowire | Confirmed probable pitchers | mlb.com/probable-pitchers |
| 6 | FantasyPros | Confirmed batting lineups (posts 2-3 hrs pre-game) | fantasypros.com/mlb/lineups/[DATE] |
| 7 | MLB.com box scores | Bullpen usage — check last 2 days' box scores | mlb.com/scores |
| 8 | Covers.com | Line movement — compare open to current | covers.com/sport/baseball/mlb/odds |
| 9 | BetMGM/TeamRankings | Power rankings and recent form | betmgm power rankings |

Steps 1-4 take about 5 minutes. Steps 5-9 add another 10 minutes. Total: 15 minutes of prep before running the prompt.

---

## THE PROMPT DATE HEADER — USE THIS EXACT FORMAT

Every prompt must open with:

```
MLB SLATE DATE: [DAY] [MONTH] [DATE] [YEAR] — US Eastern Time
MLB.com confirmed: [N] games scheduled, all pre-first-pitch as of [YOUR AEST TIME]
Earliest first pitch: [TIME] ET ([TIME] AEST Saturday / [correct local day])
Latest first pitch: [TIME] ET ([TIME] AEST Saturday / [correct local day])
```

Example:
```
MLB SLATE DATE: Friday May 29 2026 — US Eastern Time
MLB.com confirmed: 15 games scheduled, all pre-first-pitch as of 8:00 PM AEST Friday
Earliest first pitch: 6:40 PM ET (8:40 AM AEST Saturday)
Latest first pitch: 10:15 PM ET (12:15 PM AEST Saturday)
```

This header locks the slate. Any model that picks a game from a different date is immediately wrong and the pick is voided.

---

## WHAT HAPPENS IF YOU MISS THE WINDOW

If you run the prompt after games have started:

- Drop any game showing "Live" or a score from the prompt entirely
- Only include games still showing a future start time
- Note in the daily log: "Partial slate — [N] games excluded (already started)"
- Grade only picks on games that were genuinely pre-first-pitch

Do not try to pick live games. Do not include them in the prompt. Log it and move on.

---

## MLB.COM AS THE SINGLE SOURCE OF TRUTH

MLB.com is the only source for:
- Which games are on today's slate
- Which games have started vs not started
- Confirmed vs probable pitchers (the "probable" vs confirmed distinction matters)
- Official game times

Every other source (covers.com, fanduel, dimers) is secondary. If a game appears on covers.com but not MLB.com — ignore it. If MLB.com shows a game started that covers.com doesn't — the game has started, exclude it.

---

*End of file — Version 1.0*

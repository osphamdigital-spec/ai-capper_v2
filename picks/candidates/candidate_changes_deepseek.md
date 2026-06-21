# Candidate Changes — deepseek

Captured candidate adjustments awaiting promotion criteria.
Format: CANDIDATE or REJECTED entry per slate. Do NOT touch method docs until promoted.

---

## CANDIDATE (building) — 2026-06-14. Regress extreme results-stats (ERA, bullpen ERA) toward peripherals. Converges with L14 promotion theme. Status: needs one more slate of recurrence OR CLV confirmation before promotion. NOT adopted.

Use xFIP/FIP as primary bullpen metric, not ERA; cap bets resting on an extreme bullpen ERA at 1 unit unless peripherals confirm.

## CANDIDATE (building) — 2026-06-18. Discount platoon edges built on team-level wRC+ vs handedness. Status: first observation, 2x-model convergence (deepseek + sonnet), needs recurrence or CLV before promotion. NOT adopted.

When an edge is formed primarily from team-level platoon splits, apply a 20–30% discount to the platoon edge unless lineup-specific confirmation supports it; do not place a max-unit (3u) bet on a single-variable platoon edge without confirmation.

## RECURRENCE NOTE — 2026-06-20 (promotion pass over slates 06-15→06-19).
- Regress-extreme-results-stats-toward-peripherals (06-14): did NOT recur as an S4 proposal on any later slate. Remains single-slate. Gate NOT met — keep building.
- Platoon/lineup-confirmation theme: recurs strongly (06-15, 06-16 x2, 06-17 x2) AND converges with the 06-18 entry above. HOWEVER evidence on every instance rests on confirmed-lineup / post-lock data → marked `outcome-biased`. Per evidence-validity rule it does NOT count toward the gate. BLOCKED for promotion (also depends on confirmed-lineup data not currently available). Logged for visibility only.

## DATA-DESK NOTE — 2026-06-21 (build infrastructure, NOT a model-authored candidate)
Relates to the 06-18 platoon-aggregate candidate above. The prompt's PLATOON MATCHUP block was upgraded to show every batter as `Last{wRC+}({PA})` plus a per-bat PA guard: bats under 25 PA are excluded from the lineup mean and listed under `low-PA<25(excl)` (this catches tiny-sample outliers like Callihan 370 in 4 PA / Carrigg 269 in 11 PA, which previously inflated the average). **Open gap:** the included-tier average is still a FLAT (unweighted) mean — two ~70-PA bats swing the team figure as much as one ~220-PA regular (e.g. Susac92(63)/Mack71(76) weighted equally with Adames109(218)/Marsee83(220)). A natural next iteration is **PA-weighting the platoon mean** rather than a flat average. Logged here as a pre-candidate for whichever model's S4 first proposes PA-weighting — not a blocker, not yet model-attributed.

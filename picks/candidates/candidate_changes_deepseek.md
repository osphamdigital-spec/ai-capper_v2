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

## PROMOTED — 2026-06-21 (cross-model convergence). Small-sample starter flag → no 3u, reduce stake, with a bullpen 3u guard. Status: PROMOTED this pass via 3-model convergence (chatgpt + kimi + deepseek, same slate) → method_deepseek_v4.md. ADOPTED.

For any bet graded 3 units the starting pitcher must carry no small-sample flag AND the team's bullpen must be near-full (no worse than T3 empty, with T1/T2 fully available); a bullpen noted "slightly depleted" or "taxed" caps side bets at 1 unit regardless of edge size. More broadly, when a starter carries a small-sample flag the run-expectation point estimate sits over a wide band — widen that band ~50% and reduce stake / pass rather than betting the midpoint at full size. Pre-game evidence only: LAD's bullpen was flagged "slightly depleted" and Sheehan lacked a large-sample track record, yet the play was staked at 3u — neither condition met the proposed 3u requirement; STL's 3u bet ("bullpens manageable", more tested starter) would still pass. Converges with chatgpt (small-sample totals confidence haircut) and kimi (small-sample CI widening + 0.5u tier) on the same slate.

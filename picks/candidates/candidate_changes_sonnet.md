# Candidate Changes — sonnet

Captured candidate adjustments awaiting promotion criteria.
Format: CANDIDATE or REJECTED entry per slate. Do NOT touch method docs until promoted.

---

## CANDIDATE (building) — 2026-06-14. Regress extreme results-stats (ERA, bullpen ERA) toward peripherals. Converges with L14 promotion theme. Status: needs one more slate of recurrence OR CLV confirmation before promotion. NOT adopted.

ERA-vs-xFIP gap >1.0 run = regression alert, treat as neutral/negative not positive; plus the starter-durability flag (last outing <4.0 IP AND no L14 data → mandatory pass review).

## CANDIDATE (building) — 2026-06-18. Stress-test extreme team-level wRC+ aggregates before using as a strong edge signal. Status: first observation, 2x-model convergence (deepseek + sonnet), needs recurrence or CLV before promotion. NOT adopted.

When team-level wRC+ vs pitcher handedness is extreme (≤60 or ≥130), check whether the figure is broadly distributed or pulled by 2–3 outlier hitters before finalizing the edge. A broadly distributed extreme (6+ of 9 hitters below 70) is a stronger signal than a mean dragged by a few outliers with moderate names elsewhere.

## RECURRENCE NOTE — 2026-06-20 (promotion pass over slates 06-15→06-19).
- Regress-extreme-results-stats-toward-peripherals (06-14): did NOT recur as an S4 proposal on any later slate. The 06-16 S4 was an L14-divergence weighting tweak (belongs to the already-promoted L14 theme), not the ERA-regression theme. Remains single-slate. Gate NOT met — keep building.

## DATA-DESK NOTE — 2026-06-21 (build infrastructure, NOT a model-authored candidate)
Relates to the 06-18 platoon-aggregate candidate above. The prompt's PLATOON MATCHUP block was upgraded to show every batter as `Last{wRC+}({PA})` plus a per-bat PA guard: bats under 25 PA are excluded from the lineup mean and listed under `low-PA<25(excl)` (this catches tiny-sample outliers like Callihan 370 in 4 PA / Carrigg 269 in 11 PA, which previously inflated the average). **Open gap:** the included-tier average is still a FLAT (unweighted) mean — two ~70-PA bats swing the team figure as much as one ~220-PA regular (e.g. Susac92(63)/Mack71(76) weighted equally with Adames109(218)/Marsee83(220)). A natural next iteration is **PA-weighting the platoon mean** rather than a flat average. Logged here as a pre-candidate for whichever model's S4 first proposes PA-weighting — not a blocker, not yet model-attributed.

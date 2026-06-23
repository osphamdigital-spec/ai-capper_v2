# Candidate Changes — kimi

Captured candidate adjustments awaiting promotion criteria.
Format: CANDIDATE or REJECTED entry per slate. Do NOT touch method docs until promoted.

---

## CANDIDATE (building) — 2026-06-14. Convert bullpen leverage-arm availability from qualitative tie-breaker into a quantified point adjustment (+0.0 to +1.5 pts on rest differential). Confidence MEDIUM. Status: one slate — hold. NOT adopted.

## RECURRENCE NOTE — 2026-06-20 (promotion pass over slates 06-15→06-19).
The bullpen theme recurs on every slate (06-15, 06-16, 06-17, 06-18) — but every
instance is an S3 DATA REQUEST for granular high-leverage usage (72-hr IP / pitch
counts / arm-level availability), NOT an S4 method change. Kimi's actual S4s were
different each slate (replacement-level floor 06-15; secondary-signal-before-L14-spike
06-16; stale-moneyline 06-17; NONE 06-18).
RECLASSIFY: the quantified point adjustment depends on data NOT in the prompt, so per
the off-limits rule ("requests for new data → S3, not a method change") it is NOT a
promotable method candidate. Route to the data desk as a recurring feature request
(4-slate recurrence is strong signal the data would help). Gate NOT met for promotion.

## CANDIDATE (building) — 2026-06-21. When a starting pitcher carries a small-sample flag, expand the run-expectation confidence interval by ~50% and lower the stake ceiling from 1u to 0.5u (or pass entirely), even if the point-estimate edge clears the usual gate. Status: first observation for kimi, but 3x cross-model convergence on the same slate (kimi + chatgpt + deepseek). NOT adopted.

Method currently relies on deterministic SIERA/xFIP point estimates and caps small-sample spots at 1u — this underweights the uncertainty premium since the true outcome distribution is materially wider than the point estimate. Evidence is pre-game (CIN @ NYY and SF @ MIA both carried explicit small-sample starter flags, both taken at 1u). Confidence MEDIUM. Distinct from kimi's recurring bullpen-quantification S3 theme above (that one is a data request; this is a stake-sizing method change on data already in the prompt).

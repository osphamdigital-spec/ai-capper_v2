# DATA-LAYER (S3) CANDIDATES

Recurring S3 data requests from post-mortems, scoped for the SHARED data layer
(Layer A). Unlike method candidates (`picks/candidates/`), a data addition
touches ALL 8 models simultaneously — the clean-comparison rule forbids shipping
a data field to one model only. Promotion of a data candidate is an operator /
data-desk decision, not a model-method promotion.

Guiding principle (LEARNINGS 2026-06-13): **raw evidence in, conclusions out.**
Ship raw per-unit data; never ship a computed verdict/label — each model draws
its own conclusion. A "high-leverage" tag is a conclusion, not raw data.

---

## DLC-001 — Granular rolling bullpen usage (per-reliever)

- **Opened:** 2026-06-20
- **Origin:** Kimi S3, recurring 4 slates (06-15, 06-16, 06-17, 06-18). Strong
  recurrence = strong signal the data would help. Several other models
  (Sonnet, Qwen, Opus) requested adjacent bullpen granularity in the same window.
- **Request (as stated):** per-reliever IP and pitch counts over the last ~72h,
  with which high-leverage arms are unavailable (back-to-back / 3-in-4 usage).
- **Scope:** Layer A — all 8 models get the identical field.

### Source question (FLAGGED)

| Sub-item | Source | Status |
|---|---|---|
| Per-reliever appearances, IP, pitch counts, rest days | MLB Stats API boxscore | ✅ Available — already the source for `fetch_bullpen.py` (currently 3-day window + pitch counts + taxed flags) |
| Back-to-back / 3-in-4 usage flags | Derived from the same appearance data | ✅ Trivial extension |
| **"High-leverage" designation** (which arms are the leverage arms) | gmLI / leverage index → **FanGraphs only**, Cloudflare-blocked for automation | ⚠️ NOT obtainable live |

### Recommendation (pending owner confirmation)

Ship **raw per-reliever rolling usage only** (appearances, IP, pitch counts,
rest days, B2B / 3-in-4 flags) from the MLB Stats API. Do **NOT** ship a
"high-leverage arm" tag:
1. It's a *conclusion*, which violates raw-evidence-in/conclusions-out.
2. Its only live source (FanGraphs gmLI) is blocked.
Each model already identifies its own leverage arms via its method. This
delivers the substance of the 4-slate request while sidestepping the blocker.

(Alternative if a leverage tag is ever wanted: operator-loaded static FanGraphs
gmLI file, same manual pattern as the splits static files — deferred, not needed
for this candidate.)

### Build plan (staged — awaiting go-ahead)

1. Extend `fetch_bullpen.py`: widen to a rolling 3–4 day per-reliever grid
   (name, dates pitched, IP, pitches, rest days, B2B / 3-in-4 flags). Source
   unchanged (MLB Stats API).
2. Extend `build_prompt.py` `_fmt_bullpen_static`: render the raw grid for all 8
   models. Keep computed verdict lines OUT (independence principle).
3. Validate on one past slate; confirm identical field appears for every model.

### Findings on inspection (2026-06-20)

1. **The raw per-reliever rolling grid is ALREADY shipped to all 8 models.**
   `Bullpen.txt` (FanGraphs reliever export) → `load_bullpen()` →
   `_fmt_bullpen_static` already renders, per reliever: PROJECTED ROLE, hand,
   ERA, K%, SV, HLD, and `Usage last 6: <per-day pitch counts>`. Plus
   `fetch_bullpen.py` (MLB Stats API) adds live taxed flags (likely_unavailable
   = 25+ pitches yesterday OR back-to-back). So step-1's grid largely exists.
   Marginal gap only: an explicit **3-in-4** unavailability flag.

2. **PROJECTED ROLE already serves as a raw leverage proxy** (Closer / Setup),
   so a leverage signal is partially present without gmLI.

3. **gmLI was added to the WRONG files.** It went into the three STARTER files
   (start_pitchers_2yrs_IP5, pitchers_last14, pitchers_xfip_siera). On starters
   gmLI ≈ 1.0 (no signal); the population excludes closers entirely (checked:
   pitchers_last14 gmLI max 0.93; Díaz/Hader/Clase/Duran/Iglesias/Helsley all
   absent). The existing `load_gm_li()`→`_fmt_bullpen_static` lookup matches
   reliever names against this starter file, so it resolves to nothing for real
   leverage arms — the wiring is effectively dead.

4. **Fix requires operator action:** gmLI must be a column in **`Bullpen.txt`**
   (the reliever export), not the starter files. It currently has none. Once the
   next Bullpen.txt export includes a gmLI column, wiring is ~2 lines
   (`load_bullpen()` parses it; `_fmt_bullpen_static` reads `r["gmli"]` directly,
   retiring the dead starter-file cross-match).

### Shipped (2026-06-20)

1. **SD/MD + SwStr% added to the bullpen render** (raw, no derived verdict).
   `load_bullpen()` now parses SD (col 17), MD (col 18), SwStr% (col 19);
   `_fmt_bullpen_static` emits `… SwStr%, N SD/M MD` per reliever. SD/MD is a
   stronger raw answer to the high-leverage request than a derived flag.
2. **3-in-4 usage flag added** to `fetch_bullpen.py`. Lookback widened from 3→4
   days; a reliever appearing on ≥3 of the last 4 days is flagged
   `likely_unavailable` with reason `3-in-4 (N/4 days)`. Surfaced in both the
   console output and the prompt (`fmt_bullpen`).
3. **gmLI wiring dropped.** Removed `gm_li` load + the dead reliever-name lookup
   in `_fmt_bullpen_static` (it matched relievers against a starter-only file).
   `load_gm_li()` left defined but unused — re-point it at `Bullpen.txt` if a
   gmLI column is ever added there.

- **Status:** ✅ DONE. PROJECTED ROLE + SD/MD + SwStr% + usage-last-6 + 3-in-4
  flag now cover Kimi's high-leverage / availability request with raw data.
  Reliever gmLI remains a future option (needs gmLI column in `Bullpen.txt`).

QUARANTINE — 2026-06-16 POST-MORTEMS
=====================================

Files in this folder were produced on 2026-06-16 but are INVALID due to
missing game context. They must NOT be used for calibration or method updates.

---

gemini_postmortem.txt
  Root cause: 503 service-unavailable during the picks call.
  Result: 0-byte raw file → log_picks wrote gemini.json with counts.games=0 →
  no game context injected into the post-mortem prompt.
  Gemini fabricated an entire slate from scratch (invented NYY -1.5 as best
  bet, etc.). PURE FABRICATION — Gemini never actually analysed any games.

kimi_postmortem.txt  *** SUPERSEDED — SEE STATUS BELOW ***
  Original root cause (mis-diagnosed): parse failure in log_picks — GAME 1:/GAME 2:
  numbered format not recognised.
  Actual root cause (confirmed): kimi-k2.6 uses max_tokens as a SHARED budget for
  reasoning_content + content. Original 32k ceiling was exhausted by the reasoning
  trace before the content field could be written → content="" → kimi_raw.txt written
  from reasoning_content only → 0 structured picks. PARTIALLY GROUNDED but INCOMPLETE.

  STATUS: RECOVERED. After raising max_tokens to 64k and switching to streaming,
  Kimi produced a clean 15-game structured response (28,349 output tokens, 36k
  headroom remaining). Real post-mortem run 2026-06-17 with confirmed picks
  (1 bet: SEA ML -147 1u WIN). Real kimi_postmortem.txt now lives at
  picks/mlb/2026-06-16/kimi_postmortem.txt. Real KIMI block inserted into
  post_mortem_2026-06-16.txt between DEEPSEEK and QWEN.
  This quarantine file is HISTORICAL ONLY — do not use for calibration.

---

Fix applied: integrity gate added to query_model.py (inner), run_daily_2.py
(outer via --models filter passed to run_postmortem_all.py). Gate condition:
counts.games == 0 in {model}.json → skip post-mortem API call entirely.
counts.bets == 0 is NOT a gate trigger (all-pass slate is valid).

Kimi fix: max_tokens raised to 64k for both picks and post-mortems; streaming
enabled (stream=True, stream_options include_usage); loud-fail fallback on
empty content field (writes kimi_reasoning_raw.txt diagnostic, exits 1).
Parser widened to accept GAME N: numbered format (belt-and-braces for future
reasoning-trace edge cases). See LEARNINGS.md 2026-06-17 entry.

GEMINI remains permanently quarantined — pure fabrication, no retry needed
unless Gemini's picks call is re-run and confirmed non-zero.

To retry gemini (if picks are re-fetched):
  python scripts/query_model.py --model gemini --date 2026-06-16
  python scripts/log_picks.py --model gemini --date 2026-06-16 --input picks/mlb/2026-06-16/gemini_raw.txt
  python scripts/query_model.py --model gemini --date 2026-06-16 --postmortem

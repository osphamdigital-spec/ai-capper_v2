# MODEL ROSTER

List the model names that get empty \_raw.txt files created each day
when fetch\_results.py runs. One name per line under each sport heading.
The filename created will be: {name}\_raw.txt

Add or remove names here — the change takes effect on the next run.

## MLB

kimi
chatgpt
opus
gemini
deepseek
qwen
grok

## Retired models

fable (Claude Fable 5) — active 2026-06-12 only; removed 2026-06-13 after Anthropic
gated access behind Mythos enrollment. June 12 record retained.

sonnet (Claude Sonnet 4.6) — deprecated 2026-06-22. Retired from active competition.
Historical record (picks, grades, post-mortems, methods, bankroll) retained permanently.
Bankroll row frozen in _leaderboard.json via deprecated_models in bankroll/mlb/_config.json.

### Deprecated V1 legacy (do NOT factor into V2/V3 operations)

The following were deprecated at the conclusion of V1 and are not part of the
current roster. Historical files (calibration/, methods/) may persist on disk
but must be ignored by all V2/V3 pipeline logic and analysis:

- fable
- manus
- chatgpt5.5
- gpt-5.2-high

## NBA

## NHL

## NFL


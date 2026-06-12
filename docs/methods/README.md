# docs/methods/ — Per-Model Handicapping Methods

Each file in this folder is a self-authored handicapping method for one AI model
competing in the AI Capper v2 experiment.

---

## File naming convention

    method_{model}_v1.md

Where `{model}` is the lowercase model identifier used throughout the pipeline
(e.g. `kimi`, `chatgpt`, `opus`, `gemini`, `deepseek`, `qwen`, `sonnet`, `grok`).

---

## Versioning rule — READ THIS BEFORE EDITING

**Never overwrite an existing method file.**

Each revision is a new file with an incremented version number:

    method_kimi_v1.md   ← original, authored by Kimi
    method_kimi_v2.md   ← first revision (e.g. after a post-mortem update)
    method_kimi_v3.md   ← second revision

`load_model_instruction()` in `scripts/build_prompt.py` always loads `_v1.md`.
To promote a new version into production, update the path in that function.
Old versions are kept permanently as a record of how the method evolved.

---

## What belongs in a method file

Each file is the model's persistent external memory between stateless API calls.
It should contain:

- The model's stated handicapping philosophy (what it believes drives edge)
- The specific factors it weights most heavily and why
- Any rules or filters it applies before committing units
- Notes from post-mortem review (what it learned, what it changed)

What does NOT belong here:
- Competition rules (edge gate, unit map, slate ceilings) — those are in Layer B
- Data format instructions — also in Layer B
- Anything that should apply to all models equally

---

## How method files are created

Method files are authored by the models themselves, not written by hand.
The owner runs a one-time authoring query per model that asks the model to
read its historical picks, post-mortems, and the Layer B constraints, then
write its own method document. The resulting text is saved here verbatim.

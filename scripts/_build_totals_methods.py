#!/usr/bin/env python
"""
scripts/_build_totals_methods.py  (one-shot helper)

Copies each model's self-authored totals method from feedback/totals/{model}.txt
into docs/methods/method_{model}_totals_v1.md, trimming conversational
preamble/postamble so the saved method doc is clean.

These totals method docs are loaded by build_prompt.py (load_model_instruction)
ALONGSIDE the model's existing ML/RL method (method_{model}_v1.md). They are the
model's persistent, self-authored Over/Under strategy.

Run once:
    python scripts/_build_totals_methods.py
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR      = PROJECT_ROOT / "feedback" / "totals"
DEST_DIR     = PROJECT_ROOT / "docs" / "methods"

# Per-model trim rules. start_marker: keep from the first line that contains this
# substring. end_marker: drop everything from the first line containing this
# substring onward. None = no trim on that end.
TRIM = {
    "chatgpt":  {"start": None, "end": None},
    "deepseek": {"start": None, "end": None},
    "gemini":   {"start": None, "end": None},
    "grok":     {"start": None, "end": None},
    "kimi":     {"start": "TOTALS METHODOLOGY", "end": None},
    "opus":     {"start": "TOTALS METHODOLOGY", "end": "A couple of notes for the experiment"},
    "qwen":     {"start": None, "end": None},
    "sonnet":   {"start": None, "end": None},
}


def _trim(text: str, start: str | None, end: str | None) -> str:
    """Trim text to the method body using start/end line markers."""
    lines = text.splitlines()

    if start:
        for i, line in enumerate(lines):
            if start in line:
                lines = lines[i:]
                break

    if end:
        for i, line in enumerate(lines):
            if end in line:
                lines = lines[:i]
                break

    return "\n".join(lines).strip()


def main():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    for model, rule in TRIM.items():
        src = SRC_DIR / f"{model}.txt"
        if not src.exists():
            print(f"  SKIP {model}: {src} not found")
            continue

        body = _trim(src.read_text(encoding="utf-8"), rule["start"], rule["end"])

        # Prepend a small provenance header so the doc is self-describing.
        header = (
            f"# TOTALS METHODOLOGY — {model} (self-authored, v1)\n"
            f"# Persistent Over/Under strategy. Authored 2026-06-19 via the totals\n"
            f"# method-authoring round. Applied to every slate alongside the ML/RL method.\n\n"
        )
        dest = DEST_DIR / f"method_{model}_totals_v1.md"
        dest.write_text(header + body + "\n", encoding="utf-8")
        print(f"  OK   method_{model}_totals_v1.md  ({len(body):,} chars)")


if __name__ == "__main__":
    main()

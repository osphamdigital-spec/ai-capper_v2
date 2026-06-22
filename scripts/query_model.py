#!/usr/bin/env python
"""
scripts/query_model.py

Send a daily prompt to a model's API and save the raw response, OR
send a post-mortem review and append the model's analysis.

Supported models:
    grok      -- xAI Responses API (https://api.x.ai/v1), model grok-4.3
    chatgpt   -- OpenAI Responses API (default base URL), model gpt-5.4
    deepseek  -- DeepSeek Chat Completions API (https://api.deepseek.com), model deepseek-v4-pro
    kimi      -- Kimi Chat Completions API (https://api.moonshot.ai/v1), model kimi-k2.6
    qwen      -- Qwen Chat Completions API (dashscope-intl.aliyuncs.com), model qwen3.7-max
    gemini    -- Gemini OpenAI-compat API (generativelanguage.googleapis.com), model gemini-3.5-flash

Usage:
    # Picks query (default)
    python scripts/query_model.py --model grok --date 2026-06-09
    python scripts/query_model.py --model chatgpt --date 2026-06-09

    # Post-mortem query
    python scripts/query_model.py --model grok --date 2026-06-09 --postmortem

    # Dry run (read files, print what would be sent, no API call)
    python scripts/query_model.py --model grok --date 2026-06-09 --dry-run

    # Override reasoning effort
    python scripts/query_model.py --model grok --date 2026-06-09 --reasoning high

Arguments:
    --model       Model identifier used in filenames: grok, chatgpt
    --sport       Sport code (default: mlb)
    --date        Slate date (YYYY-MM-DD); defaults to today in US Eastern Time
    --postmortem  Switch to post-mortem mode instead of picks mode
    --dry-run     Print what would be sent without calling the API
    --reasoning   Reasoning effort: none, low, medium, high, xhigh (overrides mode default)

Environment variables (set in .env):
    XAI_API_KEY     Required when --model grok
    GROK_MODEL      Optional -- override model string (default: "grok-4.3")
    OPENAI_API_KEY   Required when --model chatgpt
    CHATGPT_MODEL    Optional -- override model string (default: "gpt-5.4")
    DEEPSEEK_API_KEY Required when --model deepseek
    DEEPSEEK_MODEL   Optional -- override model string (default: "deepseek-v4-pro")
    MOONSHOT_API_KEY   Required when --model kimi
    KIMI_MODEL         Optional -- override model string (default: "kimi-k2.6")
    DASHSCOPE_API_KEY  Required when --model qwen
    QWEN_MODEL         Optional -- override model string (default: "qwen3.7-max")
    GEMINI_API_KEY     Required when --model gemini
    GEMINI_MODEL       Optional -- override model string (default: "gemini-3.5-flash")

Reads (picks mode):
    daily/{sport}/{date}/prompt_{model}.md

Reads (post-mortem mode):
    picks/{sport}/{date}/post_mortem_{date}.txt
    picks/{sport}/{date}/{model}_raw.txt   (optional -- used for context)

Writes (picks mode):
    picks/{sport}/{date}/{model}_raw.txt

Appends (post-mortem mode):
    picks/{sport}/{date}/post_mortem_{date}.txt
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

SCRIPTS_DIR  = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent

# Python 3.12 system install -- the same one used by run_daily.py
PYTHON = r"C:\Users\marko\AppData\Local\Programs\Python\Python312\python.exe"

# xAI base URL -- grok-4.3 uses the Responses API at this endpoint.
# OpenAI uses the default base URL (no override needed).
XAI_BASE_URL      = "https://api.x.ai/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
KIMI_BASE_URL     = "https://api.moonshot.ai/v1"
QWEN_BASE_URL     = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
GEMINI_BASE_URL   = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Default model strings if the env vars are not set.
# "grok 4.3 Expert" is listed in docs/model_roster.md as the active Grok model.
DEFAULT_GROK_MODEL      = "grok-4.3"
DEFAULT_CHATGPT_MODEL   = "gpt-5.4"
DEFAULT_DEEPSEEK_MODEL  = "deepseek-v4-pro"
DEFAULT_KIMI_MODEL      = "kimi-k2.6"
DEFAULT_QWEN_MODEL      = "qwen3.7-max"
DEFAULT_GEMINI_MODEL    = "gemini-3.5-flash"
DEFAULT_OPUS_MODEL      = "claude-opus-4-8"
DEFAULT_SONNET_MODEL    = "claude-sonnet-4-6"
DEFAULT_FABLE_MODEL     = "claude-fable-5"

# Anthropic models share one key and use the native Anthropic SDK (not openai-compat)
# so prompt caching can be enabled via cache_control on the system block.
ANTHROPIC_MODELS = ("opus", "fable")

ANTHROPIC_MAX_TOKENS_PICKS      = 16000
ANTHROPIC_MAX_TOKENS_POSTMORTEM = 8000

# Sonnet picks with extended thinking: max_tokens covers thinking + output combined.
# Sonnet used ~10k output tokens on a 14-game slate; 10k thinking budget + 14k output
# headroom = 24k total. Opus uses the shared default (thinking OFF).
SONNET_MAX_TOKENS_PICKS      = 24000
SONNET_THINKING_BUDGET_PICKS = 10000

# Per-model output token budgets for picks mode.
# DeepSeek splits the budget between reasoning tokens and response tokens --
# with only 8000 total, reasoning consumes half and the response is truncated.
# 32000 is the deepseek-v4-pro output ceiling.
DEEPSEEK_MAX_TOKENS_PICKS      = 32000
DEEPSEEK_MAX_TOKENS_POSTMORTEM = 16000

# kimi-k2.6 uses max_tokens as a SHARED budget for reasoning_content + content.
# On a 15-game slate the reasoning trace alone consumes ~25k-30k tokens before
# the structured content field is written. 64k gives the thinking phase room to
# complete on full slates while leaving ~10k-30k for structured output.
# (Kimi's per-step limit is well above 64k; 32k was not a model ceiling —
# it conflated "API accepts up to X" with "model can think AND output within X".)
KIMI_MAX_TOKENS_PICKS      = 64000
KIMI_MAX_TOKENS_POSTMORTEM = 64000

# Gemini needs more output room than other models -- it truncates responses
# on large slates if max_tokens is set to 8000. 16000 is used for picks only;
# post-mortem uses 8000 (same as all other models).
GEMINI_MAX_TOKENS_PICKS     = 16000
GEMINI_MAX_TOKENS_POSTMORTEM = 8000

# gpt-5.4 with reasoning=medium: reasoning tokens consume the shared budget.
# 8000 is not enough -- reasoning exhausts it before the model writes output.
# 16000 gives enough headroom for reasoning + full picks response.
CHATGPT_MAX_TOKENS_PICKS      = 16000
CHATGPT_MAX_TOKENS_POSTMORTEM = 8000

# grok-4.3 uses the Responses API with reasoning (same architecture as ChatGPT).
# Reasoning tokens consume the shared budget -- 16000 matches ChatGPT headroom.
GROK_MAX_TOKENS_PICKS      = 16000
GROK_MAX_TOKENS_POSTMORTEM = 16000
GROK_REASONING_PICKS      = "high"    # raised from medium -- full slate warrants deep reasoning
GROK_REASONING_POSTMORTEM = "medium"  # raised from low

# Gemini 3.5 Flash: thinkingLevel maps via OpenAI compat reasoning_effort.
# Picks: medium (default for gemini-3.5-flash -- balanced).
# Post-mortem: medium (reviewing results warrants real thinking; "low" produced
# thin 503-prone responses with very little analytical depth).
GEMINI_REASONING_PICKS      = "medium"
GEMINI_REASONING_POSTMORTEM = "medium"

# qwen3.7-max: 16000 gives headroom for thinking + response on large slates.
QWEN_MAX_TOKENS_PICKS = 16000

# Output token budget.
# Responses API uses max_output_tokens; Chat Completions uses max_tokens.
MAX_OUTPUT_TOKENS = 8000

# Diagnostic side-channel: _call_kimi stores the reasoning_content here when
# content is empty, so run_picks can write it to {model}_reasoning_raw.txt
# for debugging. Never written to {model}_raw.txt (which is picks output only).
# Dict wrapper avoids the need for a `global` declaration inside _call_kimi.
_kimi_diagnostic_reasoning: dict = {"content": ""}

# Default reasoning effort per mode.
# Grok and ChatGPT use "medium" for picks; DeepSeek uses "high" (maps to
# high effort and keeps thinking enabled -- cheap on DeepSeek, worth having).
# Post-mortem is lighter review work; "low" is sufficient for Grok/ChatGPT.
# DeepSeek keeps "high" for post-mortem too -- thinking is cheap there.
REASONING_PICKS      = "medium"
REASONING_POSTMORTEM = "low"

# DeepSeek only supports "high" and "max" reasoning effort on their API.
# The --reasoning flag values are mapped before the API call -- see
# _deepseek_reasoning_params() for the full mapping.
# xhigh is an OpenAI-only tier (gpt-5.4); it maps to "max" for DeepSeek.
VALID_REASONING_EFFORTS = ("none", "low", "medium", "high", "xhigh")

# ─────────────────────────────────────────────────────────────────────────────
# RETRY CONFIGURATION
# Per-call exponential backoff inside query_model.py.
# Total attempts = 1 initial + len(_RETRY_DELAYS) retries.
# The outer wrappers (run_postmortem_all.py 90s retry, run_daily_2_retry.ps1
# exponential backoff) kick in if ALL of these attempts fail.
# ─────────────────────────────────────────────────────────────────────────────

class _TransientAPIError(Exception):
    """
    Raised by _handle_api_errors (and _call_anthropic) for errors that are
    safe to retry: 5xx server errors, 429 rate limits, timeouts, and
    connection drops. _call_api_with_retry() catches this and sleeps before
    the next attempt.

    Permanent errors (401 auth, 400 bad request, 403, 404) are NOT wrapped
    here — those sys.exit(1) immediately since retrying cannot help.
    """
    def __init__(self, original: Exception):
        super().__init__(str(original))
        self.original = original

# 3 total attempts: initial + 2 retries at 10s and 30s.
# Short enough not to frustrate standalone use; the outer wrappers handle
# longer waits (90s / 180s / 360s...) if all inner attempts still fail.
_RETRY_ATTEMPTS = 3
_RETRY_DELAYS   = [10, 30]   # seconds to wait before attempt 2 and 3


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCY CHECK
# Fail fast and clearly if packages are not installed, rather than with a
# confusing ImportError traceback.
# ─────────────────────────────────────────────────────────────────────────────

def _check_dependencies():
    """
    Verify that openai, httpx, and python-dotenv are installed.
    If any are missing, print the pip install commands and exit.
    httpx is required only for Grok (timeout override) but we check it
    upfront for all models to keep the error surface predictable.
    """
    missing = []
    try:
        import anthropic  # noqa: F401
    except ImportError:
        missing.append("anthropic")
    try:
        import openai  # noqa: F401
    except ImportError:
        missing.append("openai>=1.0")
    try:
        import httpx  # noqa: F401
    except ImportError:
        missing.append("httpx")
    try:
        import dotenv  # noqa: F401
    except ImportError:
        missing.append("python-dotenv")

    if missing:
        print("ERROR: Required packages are not installed under Python 3.12.")
        print()
        print("Run the following commands to install them:")
        for pkg in missing:
            print(f'  "{PYTHON}" -m pip install {pkg}')
        print()
        print("Then re-run this script.")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# ENV LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _load_dotenv():
    """Load .env from the project root into the process environment."""
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"WARNING: .env not found at {env_path}")
        print("         XAI_API_KEY must already be set in the environment.")


# ─────────────────────────────────────────────────────────────────────────────
# DATE HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _today_et() -> str:
    """Return today's date in US Eastern Time as YYYY-MM-DD."""
    try:
        from tz_util import ET
        return datetime.now(ET).strftime("%Y-%m-%d")
    except ImportError:
        # Fallback if tz_util is not on the path -- caller should add scripts/ to sys.path
        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")
        return datetime.now(et).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# API CALLS
# Both Grok and ChatGPT use the openai package with the Responses API
# (/v1/responses). Grok requires a base_url override and a long timeout;
# OpenAI uses default settings. Neither accepts temperature, top_p, or
# other Chat Completions parameters -- reasoning models only accept
# reasoning={} and max_output_tokens.
#
# Web search is enabled for picks mode only (web_search=True).
# Post-mortem mode never uses web search (results are already provided).
# ─────────────────────────────────────────────────────────────────────────────

def _handle_api_errors(e, key_env_var: str):
    """
    Classify an API exception as transient or permanent and act accordingly.

    Transient (raise _TransientAPIError — _call_api_with_retry will retry):
      429 RateLimitError, 5xx server errors, APITimeoutError, APIConnectionError

    Permanent (sys.exit(1) — retrying cannot fix these):
      401 AuthenticationError, 400/403/404 and other 4xx client errors

    Called from all per-model _call_* functions so error handling is defined
    in one place instead of duplicated across 6 callers.
    """
    from openai import (AuthenticationError, RateLimitError, APITimeoutError,
                        APIConnectionError, APIStatusError, APIError)

    if isinstance(e, AuthenticationError):
        print(f"ERROR: API authentication failed -- check {key_env_var} in .env")
        print(f"       Detail: {e}")
        sys.exit(1)
    elif isinstance(e, RateLimitError):
        print(f"ERROR: Rate limit (429) -- will retry with backoff")
        print(f"       Detail: {e}")
        raise _TransientAPIError(e)
    elif isinstance(e, APITimeoutError):
        print(f"ERROR: Request timed out -- will retry with backoff")
        print(f"       Detail: {e}")
        raise _TransientAPIError(e)
    elif isinstance(e, APIConnectionError):
        print(f"ERROR: Connection error -- will retry with backoff")
        print(f"       Detail: {e}")
        raise _TransientAPIError(e)
    elif isinstance(e, APIStatusError):
        if e.status_code >= 500:
            print(f"ERROR: Server error ({e.status_code}) -- will retry with backoff")
            print(f"       Detail: {e}")
            raise _TransientAPIError(e)
        else:
            # 400 bad request, 403 forbidden, 404 not found, etc. — permanent
            print(f"ERROR: API error ({e.status_code}) -- {e}")
            sys.exit(1)
    elif isinstance(e, APIError):
        print(f"ERROR: API error -- {e}")
        sys.exit(1)
    else:
        print(f"ERROR: Unexpected error -- {e}")
        sys.exit(1)


def _extract_text_from_output(output_items) -> str:
    """
    Walk the response.output list and concatenate all output_text blocks.

    When tools (e.g. web search) are enabled the response contains multiple
    output items: tool call blocks, tool result blocks, and the message block.
    response.output_text may be empty in that case, so we always walk the list
    manually instead of relying on the convenience shortcut.
    """
    text = ""
    for item in output_items:
        if item.type == "message":
            for part in item.content:
                if part.type == "output_text":
                    text += part.text
    return text


def _extract_reasoning_tokens(usage) -> int | None:
    """
    Pull reasoning_tokens out of a usage object safely.
    OpenAI nests it under output_tokens_details; xAI may expose it directly.
    Returns None if not present or zero (zero means no reasoning was billed).
    """
    # OpenAI path: usage.output_tokens_details.reasoning_tokens
    details = getattr(usage, "output_tokens_details", None)
    if details is not None:
        val = getattr(details, "reasoning_tokens", None)
        if val:
            return val
    # xAI path: usage.reasoning_tokens (direct attribute)
    val = getattr(usage, "reasoning_tokens", None)
    if val:
        return val
    return None


def _call_grok(
    input_messages: list[dict],
    api_key: str,
    model_id: str,
    reasoning_effort: str,
    web_search: bool,
) -> tuple[str, int, int, int | None]:
    """
    Send messages to the xAI Responses API and return:
        (response_text, input_tokens, output_tokens, reasoning_tokens_or_None)

    Uses a 3600s timeout because medium/high-reasoning calls can take several
    minutes. Web search is included only when web_search=True (picks mode).
    """
    import httpx
    from openai import OpenAI

    client = OpenAI(
        api_key  = api_key,
        base_url = XAI_BASE_URL,
        timeout  = httpx.Timeout(3600.0),
    )

    kwargs = dict(
        model             = model_id,
        reasoning         = {"effort": reasoning_effort},
        max_output_tokens = MAX_OUTPUT_TOKENS,
        input             = input_messages,
    )
    if web_search:
        kwargs["tools"] = [{"type": "web_search"}]

    response = None
    try:
        response = client.responses.create(**kwargs)
    except Exception as e:
        _handle_api_errors(e, "XAI_API_KEY")

    response_id = getattr(response, "id", None) if response else None  # noqa: F841
    text = _extract_text_from_output(response.output)
    if not text:
        print("ERROR: Unexpected response structure -- no output_text found.")
        print(f"       Raw response output: {response.output}")
        sys.exit(1)

    return (
        text,
        response.usage.input_tokens,
        response.usage.output_tokens,
        _extract_reasoning_tokens(response.usage),
    )


def _call_chatgpt(
    input_messages: list[dict],
    api_key: str,
    model_id: str,
    reasoning_effort: str,
    web_search: bool,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> tuple[str, int, int, int | None]:
    """
    Send messages to the OpenAI Responses API and return:
        (response_text, input_tokens, output_tokens, reasoning_tokens_or_None)

    Web search and text verbosity are added only when web_search=True (picks
    mode). We always extract text by walking response.output rather than using
    response.output_text directly, because when tools are active the shortcut
    may be empty.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    kwargs = dict(
        model             = model_id,
        reasoning         = {"effort": reasoning_effort},
        max_output_tokens = max_output_tokens,
        input             = input_messages,
    )
    # web_search flag is kept in the signature for interface consistency but
    # web_search_preview is never enabled -- it consumed the full token budget
    # on search calls before the model could produce picks (token exhaustion).

    try:
        response = client.responses.create(**kwargs)
    except Exception as e:
        _handle_api_errors(e, "OPENAI_API_KEY")

    text = _extract_text_from_output(response.output)
    if not text:
        print("ERROR: Unexpected response structure -- no output_text found.")
        print(f"       Raw response output: {response.output}")
        sys.exit(1)

    return (
        text,
        response.usage.input_tokens,
        response.usage.output_tokens,
        _extract_reasoning_tokens(response.usage),
    )


def _deepseek_reasoning_params(effort: str) -> tuple[dict, str]:
    """
    Map the --reasoning flag to DeepSeek API parameters and a display label.

    DeepSeek Chat Completions accepts reasoning_effort="high" or "max".
    "low" and "medium" are silently coerced to "high" by the API anyway, so
    we map them explicitly here to keep the printed label honest.

    Returns (extra_body, display_label) where:
      extra_body  -- passed as extra_body= to chat.completions.create()
      display_label -- printed in the token usage summary

    Mapping:
      "none"   -> thinking disabled, no reasoning_effort param
      "low"    -> thinking enabled, reasoning_effort="high"
      "medium" -> thinking enabled, reasoning_effort="high"
      "high"   -> thinking enabled, reasoning_effort="high"
      "xhigh"  -> thinking enabled, reasoning_effort="max"
    """
    if effort == "none":
        return {"thinking": {"type": "disabled"}}, "none (thinking disabled)"
    elif effort == "xhigh":
        return {"thinking": {"type": "enabled"}}, "max"
    else:
        # low / medium / high all resolve to "high" on DeepSeek
        suffix = " (deepseek maps low/medium -> high)" if effort in ("low", "medium") else ""
        return {"thinking": {"type": "enabled"}}, f"high{suffix}"


def _call_deepseek(
    input_messages: list[dict],
    api_key: str,
    model_id: str,
    reasoning_effort: str,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> tuple[str, int, int, int | None]:
    """
    Send messages to the DeepSeek Chat Completions API and return:
        (response_text, input_tokens, output_tokens, reasoning_tokens_or_None)

    DeepSeek uses Chat Completions (not Responses API), so parameters differ
    from Grok and ChatGPT:
      - max_tokens instead of max_output_tokens
      - extra_body={"thinking": ...} to control chain-of-thought
      - reasoning_effort as a top-level param (omitted when thinking disabled)
      - No web search tool (not available on DeepSeek API)

    reasoning_content on the response is the raw thinking trace -- we log
    its token count but do not include it in the saved output text.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    extra_body, _ = _deepseek_reasoning_params(reasoning_effort)

    kwargs = dict(
        model      = model_id,
        messages   = input_messages,
        max_tokens = max_tokens,
        extra_body = extra_body,
    )
    # reasoning_effort is a top-level param only when thinking is enabled
    if extra_body.get("thinking", {}).get("type") == "enabled":
        kwargs["reasoning_effort"] = (
            "max" if reasoning_effort == "xhigh" else "high"
        )

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        _handle_api_errors(e, "DEEPSEEK_API_KEY")

    text = response.choices[0].message.content or ""

    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    # reasoning_tokens lives under completion_tokens_details on DeepSeek
    details = getattr(response.usage, "completion_tokens_details", None)
    reasoning_tokens = getattr(details, "reasoning_tokens", None) if details else None
    if reasoning_tokens == 0:
        reasoning_tokens = None

    return text, input_tokens, output_tokens, reasoning_tokens


def _kimi_thinking_params(effort: str) -> tuple[dict, str]:
    """
    Map the --reasoning flag to Kimi extra_body and a display label.

    Kimi supports thinking on/off only -- there are no effort levels.
    Any effort value other than "none" enables thinking.

    Returns (extra_body, display_label).
    """
    if effort == "none":
        return {"thinking": {"type": "disabled"}}, "thinking disabled"
    return {"thinking": {"type": "enabled"}}, "thinking enabled"


def _call_kimi(
    input_messages: list[dict],
    api_key: str,
    model_id: str,
    reasoning_effort: str,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> tuple[str, int, int, int | None]:
    """
    Send messages to the Kimi Chat Completions API and return:
        (response_text, input_tokens, output_tokens, reasoning_tokens_or_None)

    kimi-k2.6 does NOT accept temperature, top_p, presence_penalty, or
    frequency_penalty -- only model, messages, extra_body, max_tokens, and
    stream/stream_options are passed. No web search tool, no reasoning_effort param.

    stream=True is required for thinking models: non-streaming calls can time out
    at the HTTP layer before the long reasoning phase completes. stream_options
    include_usage=True ensures token counts (including reasoning_tokens) arrive
    in the final chunk — without it the usage block is null on all chunks.

    reasoning_content is NOT a typed attribute on the OpenAI SDK StreamingChoice
    delta — direct attribute access raises AttributeError. Always use hasattr guard.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=KIMI_BASE_URL)

    extra_body, _ = _kimi_thinking_params(reasoning_effort)

    # Accumulate content and reasoning_content separately from the stream.
    content_chunks   = []
    reasoning_chunks = []
    finish_reason    = None
    _usage           = None
    _usage_details   = None

    try:
        stream = client.chat.completions.create(
            model          = model_id,
            messages       = input_messages,
            max_tokens     = max_tokens,
            extra_body     = extra_body,
            stream         = True,
            stream_options = {"include_usage": True},
        )
        # Stream loop is inside the same try block so mid-stream network
        # drops are caught and classified as transient just like connection
        # errors on the initial request.
        for chunk in stream:
            if not chunk.choices:
                # Usage-only final chunk (sent after the finish_reason chunk)
                if hasattr(chunk, "usage") and chunk.usage:
                    _usage         = chunk.usage
                    _usage_details = getattr(chunk.usage, "completion_tokens_details", None)
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                content_chunks.append(delta.content)
            # reasoning_content is not a typed SDK attribute — hasattr guard required
            if hasattr(delta, "reasoning_content"):
                rc = getattr(delta, "reasoning_content")
                if rc:
                    reasoning_chunks.append(rc)
            fr = chunk.choices[0].finish_reason
            if fr:
                finish_reason = fr
            if hasattr(chunk, "usage") and chunk.usage:
                _usage         = chunk.usage
                _usage_details = getattr(chunk.usage, "completion_tokens_details", None)
    except _TransientAPIError:
        raise  # already printed; let _call_api_with_retry handle backoff
    except Exception as e:
        _handle_api_errors(e, "MOONSHOT_API_KEY")

    text              = "".join(content_chunks).strip()
    reasoning_content = "".join(reasoning_chunks)

    # Capture token usage from the accumulated stream usage block.
    input_tokens     = _usage.prompt_tokens     if _usage else 0
    output_tokens    = _usage.completion_tokens if _usage else 0
    details          = _usage_details
    reasoning_tokens = getattr(details, "reasoning_tokens", None) if details else None
    if reasoning_tokens == 0:
        reasoning_tokens = None

    # Empty content means the reasoning trace consumed the full token budget
    # before the model could write any structured output to the content field.
    # This is a FAILED call — do NOT fall back to reasoning_content as picks output.
    # The reasoning trace has no PICK:/UNITS:/EDGE: fields and cannot be parsed.
    # Store it via the module-level side-channel so run_picks can write a diagnostic
    # file without confusing it with a real picks raw file.
    if not text:
        _kimi_diagnostic_reasoning["content"] = reasoning_content
        finish = getattr(response.choices[0], "finish_reason", "unknown")
        rt_note = (f"  reasoning_tokens : {reasoning_tokens:,}\n"
                   if reasoning_tokens else "")
        print(f"\n  ERROR: Kimi content field is empty (finish_reason={finish}).")
        print(f"  reasoning_content: {len(reasoning_content):,} chars")
        print(rt_note, end="")
        print(f"  The reasoning trace consumed the max_tokens={max_tokens:,} shared budget")
        print(f"  before the structured content field could be written.")
        print(f"  Returning empty — run_picks will write diagnostic file and fail.")
        return "", input_tokens, output_tokens, reasoning_tokens

    # Strip any preamble before the first GAME block (edge case where content
    # begins with a brief prose header before the structured game blocks).
    import re as _re
    lines = text.splitlines()
    first_game = next(
        (i for i, ln in enumerate(lines)
         if _re.match(r"^## GAME:|^GAME ", ln.strip())),
        None,
    )
    if first_game and first_game > 0:
        stripped_chars = sum(len(l) + 1 for l in lines[:first_game])
        print(f"  INFO: Stripped {stripped_chars} chars before first GAME block")
        text = "\n".join(lines[first_game:])

    return text, input_tokens, output_tokens, reasoning_tokens


def _qwen_thinking_params(effort: str) -> tuple[dict, str]:
    """
    Map the --reasoning flag to Qwen extra_body and a display label.

    qwen3.7-max uses enable_thinking: True/False. No effort levels.
    Any value other than "none" enables thinking.

    Returns (extra_body, display_label).
    """
    if effort == "none":
        return {"enable_thinking": False}, "thinking disabled"
    return {"enable_thinking": True}, "thinking enabled"


def _call_qwen(
    input_messages: list[dict],
    api_key: str,
    model_id: str,
    reasoning_effort: str,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> tuple[str, int, int, int | None]:
    """
    Send messages to the Qwen Chat Completions API (Singapore endpoint) and return:
        (response_text, input_tokens, output_tokens, reasoning_tokens_or_None)

    Uses the international DashScope endpoint, correct for Australia.
    Only model, messages, extra_body, and max_tokens are passed --
    temperature and other sampling params are not accepted by qwen3.7-max.
    No web search, no reasoning_effort param.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=QWEN_BASE_URL)

    extra_body, _ = _qwen_thinking_params(reasoning_effort)

    try:
        response = client.chat.completions.create(
            model      = model_id,
            messages   = input_messages,
            max_tokens = max_tokens,
            extra_body = extra_body,
        )
    except Exception as e:
        _handle_api_errors(e, "DASHSCOPE_API_KEY")

    text = response.choices[0].message.content or ""

    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    details = getattr(response.usage, "completion_tokens_details", None)
    reasoning_tokens = getattr(details, "reasoning_tokens", None) if details else None
    if reasoning_tokens == 0:
        reasoning_tokens = None

    return text, input_tokens, output_tokens, reasoning_tokens


def _gemini_reasoning_params(effort: str) -> tuple[str | None, str]:
    """
    Map the --reasoning flag to a Gemini reasoning_effort value and display label.

    Gemini 3 cannot disable thinking, so "none" omits the param entirely
    rather than passing an unsupported value. "xhigh" is capped at "high".

    Returns (api_effort_or_None, display_label).
    """
    if effort == "none":
        return None, "default (thinking level not set)"
    if effort == "xhigh":
        return "high", "high"
    return effort, effort


def _call_gemini(
    input_messages: list[dict],
    api_key: str,
    model_id: str,
    reasoning_effort: str,
    max_tokens: int,
) -> tuple[str, int, int, int | None]:
    """
    Send messages to Gemini via the OpenAI-compatible Chat Completions endpoint
    and return: (response_text, input_tokens, output_tokens, reasoning_tokens_or_None)

    reasoning_effort is passed as a top-level param when set; omitted for "none"
    (Gemini 3 cannot disable thinking, so we just leave it at its default).
    max_tokens is caller-supplied: 16000 for picks, 8000 for post-mortem.
    No temperature or other sampling params -- Gemini compat layer rejects them.
    No web search via the OpenAI compat layer.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)

    api_effort, _ = _gemini_reasoning_params(reasoning_effort)

    kwargs = dict(
        model      = model_id,
        messages   = input_messages,
        max_tokens = max_tokens,
    )
    if api_effort is not None:
        kwargs["reasoning_effort"] = api_effort

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        _handle_api_errors(e, "GEMINI_API_KEY")

    text = response.choices[0].message.content or ""

    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    details = getattr(response.usage, "completion_tokens_details", None)
    reasoning_tokens = getattr(details, "reasoning_tokens", None) if details else None
    if reasoning_tokens == 0:
        reasoning_tokens = None

    return text, input_tokens, output_tokens, reasoning_tokens


def _call_anthropic(
    system_text: str,
    prompt_text: str,
    api_key: str,
    model_id: str,
    max_tokens: int = ANTHROPIC_MAX_TOKENS_PICKS,
    thinking_budget: int | None = None,
) -> tuple[str, int, int, int | None]:
    """
    Send messages to the Anthropic API using the native SDK with prompt caching.
    The system prompt is marked ephemeral so the API caches it across calls --
    reducing cost and latency for repeat queries on the same slate.

    thinking_budget: when set, enables extended thinking with that token budget.
    max_tokens must exceed thinking_budget (it covers thinking + output combined).
    Only passed for Sonnet picks -- Opus and post-mortems use thinking=disabled (default).

    Returns (response_text, input_tokens, output_tokens, None).
    Reasoning tokens are not exposed separately by the Anthropic API.
    """
    import anthropic as ant

    client = ant.Anthropic(api_key=api_key)

    create_kwargs = dict(
        model      = model_id,
        max_tokens = max_tokens,
        system     = [
            {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages   = [{"role": "user", "content": prompt_text}],
    )
    if thinking_budget is not None:
        create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

    # Use streaming — required by Anthropic for requests that may exceed 10 minutes.
    # client.messages.stream() accumulates the full response and exposes usage
    # stats via stream.get_final_message() at the end of the context manager.
    try:
        with client.messages.stream(**create_kwargs) as stream:
            response = stream.get_final_message()
    except ant.AuthenticationError as e:
        print(f"ERROR: Anthropic API authentication failed -- check CLAUDE_API_KEY in .env")
        print(f"       Detail: {e}")
        sys.exit(1)
    except ant.RateLimitError as e:
        print(f"ERROR: Anthropic rate limit (429) -- will retry with backoff")
        print(f"       Detail: {e}")
        raise _TransientAPIError(e)
    except ant.InternalServerError as e:
        print(f"ERROR: Anthropic server error (5xx) -- will retry with backoff")
        print(f"       Detail: {e}")
        raise _TransientAPIError(e)
    except Exception as e:
        # Catch any other APIStatusError subclass with a 5xx status code
        status = getattr(e, "status_code", None)
        if status is not None and status >= 500:
            print(f"ERROR: Anthropic server error ({status}) -- will retry with backoff")
            print(f"       Detail: {e}")
            raise _TransientAPIError(e)
        print(f"ERROR: Anthropic API error -- {e}")
        sys.exit(1)

    # Fable 5 (and extended-thinking models) may return a ThinkingBlock before
    # the TextBlock. Find the first block that has a .text attribute.
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text = block.text
            break
    if not text:
        print("ERROR: Anthropic returned empty content.")
        sys.exit(1)

    input_tokens  = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    return text, input_tokens, output_tokens, None


def _resolve_model_config(model: str) -> tuple[str, str, str]:
    """
    Return (api_key, model_id, display_label) for the given model name.
    Exits with a clear error if the required API key is not set.
    """
    if model == "grok":
        api_key  = os.environ.get("XAI_API_KEY", "")
        model_id = os.environ.get("GROK_MODEL", DEFAULT_GROK_MODEL)
        label    = f"Grok ({model_id})"
        if not api_key:
            print("ERROR: XAI_API_KEY is not set.")
            print("       Add it to .env: XAI_API_KEY=your_key_here")
            sys.exit(1)
    elif model == "chatgpt":
        api_key  = os.environ.get("OPENAI_API_KEY", "")
        model_id = os.environ.get("CHATGPT_MODEL", DEFAULT_CHATGPT_MODEL)
        label    = f"ChatGPT ({model_id})"
        if not api_key:
            print("ERROR: OPENAI_API_KEY is not set.")
            print("       Add it to .env: OPENAI_API_KEY=your_key_here")
            sys.exit(1)
    elif model == "deepseek":
        api_key  = os.environ.get("DEEPSEEK_API_KEY", "")
        model_id = os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)
        label    = f"DeepSeek ({model_id})"
        if not api_key:
            print("ERROR: DEEPSEEK_API_KEY is not set.")
            print("       Add it to .env: DEEPSEEK_API_KEY=your_key_here")
            sys.exit(1)
    elif model == "kimi":
        api_key  = os.environ.get("MOONSHOT_API_KEY", "")
        model_id = os.environ.get("KIMI_MODEL", DEFAULT_KIMI_MODEL)
        label    = f"Kimi ({model_id})"
        if not api_key:
            print("ERROR: MOONSHOT_API_KEY is not set.")
            print("       Add it to .env: MOONSHOT_API_KEY=your_key_here")
            sys.exit(1)
    elif model == "qwen":
        api_key  = os.environ.get("DASHSCOPE_API_KEY", "")
        model_id = os.environ.get("QWEN_MODEL", DEFAULT_QWEN_MODEL)
        label    = f"Qwen ({model_id})"
        if not api_key:
            print("ERROR: DASHSCOPE_API_KEY is not set.")
            print("       Add it to .env: DASHSCOPE_API_KEY=your_key_here")
            sys.exit(1)
    elif model == "gemini":
        api_key  = os.environ.get("GEMINI_API_KEY", "")
        model_id = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        label    = f"Gemini ({model_id})"
        if not api_key:
            print("ERROR: GEMINI_API_KEY is not set.")
            print("       Add it to .env: GEMINI_API_KEY=your_key_here")
            sys.exit(1)
    elif model in ANTHROPIC_MODELS:
        api_key = os.environ.get("CLAUDE_API_KEY", "")
        if model == "opus":
            model_id = os.environ.get("OPUS_MODEL", DEFAULT_OPUS_MODEL)
            label    = f"Claude Opus ({model_id})"
        else:  # fable
            model_id = os.environ.get("FABLE_MODEL", DEFAULT_FABLE_MODEL)
            label    = f"Claude Fable ({model_id})"
        if not api_key:
            print("ERROR: CLAUDE_API_KEY is not set.")
            print("       Add it to .env: CLAUDE_API_KEY=your_key_here")
            sys.exit(1)
    else:
        print(f"ERROR: Unknown model '{model}'. Supported: grok, chatgpt, deepseek, kimi, qwen, gemini, opus, fable")
        sys.exit(1)

    return api_key, model_id, label


def _call_api(
    model: str,
    input_messages: list[dict],
    api_key: str,
    model_id: str,
    reasoning_effort: str,
    web_search: bool,
    max_tokens: int = MAX_OUTPUT_TOKENS,
    system_text: str = "",
    prompt_text: str = "",
    thinking_budget: int | None = None,
) -> tuple[str, int, int, int | None]:
    """Dispatch to the correct API caller for the given model name."""
    if model in ANTHROPIC_MODELS:
        # Native Anthropic SDK with prompt caching; ignores input_messages format
        return _call_anthropic(system_text, prompt_text, api_key, model_id, max_tokens,
                               thinking_budget=thinking_budget)
    elif model == "grok":
        return _call_grok(input_messages, api_key, model_id, reasoning_effort, web_search)
    elif model == "chatgpt":
        return _call_chatgpt(input_messages, api_key, model_id, reasoning_effort, web_search, max_tokens)
    elif model == "deepseek":
        # DeepSeek has no web search tool -- web_search flag is ignored
        return _call_deepseek(input_messages, api_key, model_id, reasoning_effort, max_tokens)
    elif model == "kimi":
        # Kimi has no web search tool via API -- web_search flag is ignored
        return _call_kimi(input_messages, api_key, model_id, reasoning_effort, max_tokens)
    elif model == "qwen":
        # Qwen has no web search tool via API -- web_search flag is ignored
        return _call_qwen(input_messages, api_key, model_id, reasoning_effort)
    elif model == "gemini":
        # Gemini has no web search via OpenAI compat layer; max_tokens is caller-set
        return _call_gemini(input_messages, api_key, model_id, reasoning_effort, max_tokens)
    else:
        print(f"ERROR: No API caller for model '{model}'.")
        sys.exit(1)


def _call_api_with_retry(
    model: str,
    input_messages: list[dict],
    api_key: str,
    model_id: str,
    reasoning_effort: str,
    web_search: bool,
    max_tokens: int = MAX_OUTPUT_TOKENS,
    system_text: str = "",
    prompt_text: str = "",
    thinking_budget: int | None = None,
) -> tuple[str, int, int, int | None]:
    """
    Wrapper around _call_api() with exponential backoff for transient errors.

    Retry schedule (_RETRY_ATTEMPTS=3, _RETRY_DELAYS=[10, 30]):
      Attempt 1 — immediate
      Attempt 2 — wait 10s after attempt 1 fails
      Attempt 3 — wait 30s after attempt 2 fails
      All failed — sys.exit(1) so the outer wrappers can retry the pipeline:
        run_postmortem_all.py : one fixed 90s retry per model
        run_daily_2_retry.ps1 : exponential backoff (90 / 180 / 360s ...)

    Permanent errors (auth failure, bad request) bypass this and sys.exit(1)
    immediately from _handle_api_errors — no retry is attempted for those.
    """
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            return _call_api(
                model, input_messages, api_key, model_id, reasoning_effort,
                web_search, max_tokens, system_text, prompt_text, thinking_budget,
            )
        except _TransientAPIError:
            if attempt < _RETRY_ATTEMPTS - 1:
                wait = _RETRY_DELAYS[attempt]
                print(f"\n  Transient error on attempt {attempt + 1}/{_RETRY_ATTEMPTS} — "
                      f"retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"\n  All {_RETRY_ATTEMPTS} internal attempts failed.")
                print(f"  The outer retry wrappers will handle further retries.")
                sys.exit(1)

    sys.exit(1)  # unreachable — satisfies type checker


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN USAGE PRINTER
# ─────────────────────────────────────────────────────────────────────────────

def _print_usage(
    model_label: str,
    model_id: str,
    reasoning_effort: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int | None,
    output_path: Path,
):
    """Print a consistent token usage summary after every API call."""
    r_tokens = str(reasoning_tokens) if reasoning_tokens is not None else "N/A"
    print(f"  Model            : {model_label}  ({model_id})")
    print(f"  Reasoning effort : {reasoning_effort}")
    print(f"  Input tokens     : {input_tokens:,}")
    print(f"  Output tokens    : {output_tokens:,}")
    print(f"  Reasoning tokens : {r_tokens}")
    print(f"  Output file      : {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# PICKS MODE
# ─────────────────────────────────────────────────────────────────────────────

def run_picks(model: str, sport: str, date: str, dry_run: bool, reasoning_effort: str):
    """
    Read per-model system + prompt files, send to the API, save the raw response.

    System file:   daily/{sport}/{date}/system_{model}.md  (permanent instructions)
    Prompt file:   daily/{sport}/{date}/prompt_{model}.md  (daily slate data)
    Output file:   picks/{sport}/{date}/{model}_raw.txt
    """
    # --- Read prompt file (daily slate data) --------------------------------
    prompt_path = PROJECT_ROOT / "daily" / sport / date / f"prompt_{model}.md"

    if not prompt_path.exists():
        print(f"ERROR: Prompt file not found: {prompt_path}")
        print(f"       Run build_prompt.py first to generate it.")
        sys.exit(1)

    prompt_text = prompt_path.read_text(encoding="utf-8")

    # --- Phase 5b: inject per-model calibration stats ----------------------
    # Reads picks/calibration/{model}_calibration.md if it exists.
    # calc_calibration.py generates this file after each graded day.
    # Appended at the END of the prompt so it never interferes with data blocks.
    calib_path = PROJECT_ROOT / "picks" / "calibration" / f"{model}_calibration.md"
    if calib_path.exists():
        try:
            calib_text = calib_path.read_text(encoding="utf-8").strip()
            if calib_text:
                prompt_text = (
                    prompt_text.rstrip()
                    + "\n\n"
                    + "---\n"
                    + "## YOUR CALIBRATION RECORD (as of last graded slate)\n"
                    + "Use this to self-assess — not to chase losses or press winners.\n"
                    + "If ROI is negative, review whether your gap calculations are honest.\n"
                    + "If win rate is below 50%, check whether you are overconfident on prices.\n\n"
                    + calib_text
                    + "\n"
                )
                print(f"Calibration      : injected ({calib_path.name})")
        except Exception as e:
            print(f"Calibration      : skipped (read error: {e})")
    else:
        print(f"Calibration      : not available (run calc_calibration.py first)")

    # --- Load system prompt (permanent instructions) -----------------------
    # Falls back gracefully when the system file is missing so pre-refactor
    # prompt files (which contain instructions inline) still work.
    system_path = PROJECT_ROOT / "daily" / sport / date / f"system_{model}.md"
    if system_path.exists():
        system_text = system_path.read_text(encoding="utf-8")
        system_label = f"{system_path}  ({len(system_text):,} chars)"
    else:
        system_text = (
            "You are a professional sports bettor. "
            "Follow all instructions in the user message exactly."
        )
        system_label = "fallback (system file not found -- instructions in user message)"

    # Show a model-appropriate effort label rather than the raw flag value.
    if model == "deepseek":
        _, effort_label = _deepseek_reasoning_params(reasoning_effort)
    elif model == "kimi":
        _, effort_label = _kimi_thinking_params(reasoning_effort)
    elif model == "qwen":
        _, effort_label = _qwen_thinking_params(reasoning_effort)
    elif model == "gemini":
        _, effort_label = _gemini_reasoning_params(reasoning_effort)
    else:
        effort_label = reasoning_effort

    print(f"System file      : {system_label}")
    print(f"Prompt file      : {prompt_path}  ({len(prompt_text):,} chars)")
    print(f"Reasoning effort : {effort_label}")
    if model == "grok":
        web_label = "enabled"
    elif model == "chatgpt":
        web_label = "disabled (removed -- token exhaustion)"
    else:
        web_label = "disabled"
    print(f"Web search       : {web_label}")

    # --- Build input list: system message + user message -------------------
    input_messages = [
        {"role": "system", "content": system_text},
        {"role": "user",   "content": prompt_text},
    ]

    # --- Dry run exit point -----------------------------------------------
    if dry_run:
        print()
        print("--- DRY RUN: system message (first 200 chars) ---")
        sys_safe    = system_text[:200].encode("ascii", errors="replace").decode("ascii")
        sys_preview = sys_safe.replace("\n", "\n  ")
        print(f"  {sys_preview}")
        print()
        print("--- DRY RUN: user message (first 500 chars) ---")
        safe    = prompt_text[:500].encode("ascii", errors="replace").decode("ascii")
        preview = safe.replace("\n", "\n  ")
        print(f"  {preview}")
        if len(prompt_text) > 500:
            print(f"  ... [{len(prompt_text) - 500} more chars]")
        print()
        print("No API call made.")
        return

    # --- Resolve API credentials ------------------------------------------
    api_key, model_id, display_label = _resolve_model_config(model)

    if model in ANTHROPIC_MODELS:
        endpoint = "https://api.anthropic.com"
    elif model == "grok":
        endpoint = XAI_BASE_URL
    elif model == "deepseek":
        endpoint = DEEPSEEK_BASE_URL
    elif model == "kimi":
        endpoint = KIMI_BASE_URL
    elif model == "qwen":
        endpoint = QWEN_BASE_URL
    elif model == "gemini":
        endpoint = GEMINI_BASE_URL
    else:
        endpoint = "https://api.openai.com/v1"
    print(f"Model ID         : {model_id}")
    print(f"Sending to       : {endpoint}  ...")

    # Per-model output token budgets for picks mode.
    # Opus picks: thinking OFF -- uses shared Anthropic default.
    if model in ANTHROPIC_MODELS:
        picks_max_tokens   = ANTHROPIC_MAX_TOKENS_PICKS
        picks_thinking_budget = None
    elif model == "deepseek":
        picks_max_tokens, picks_thinking_budget = DEEPSEEK_MAX_TOKENS_PICKS, None
    elif model == "kimi":
        picks_max_tokens, picks_thinking_budget = KIMI_MAX_TOKENS_PICKS, None
    elif model == "gemini":
        picks_max_tokens, picks_thinking_budget = GEMINI_MAX_TOKENS_PICKS, None
    elif model == "chatgpt":
        picks_max_tokens, picks_thinking_budget = CHATGPT_MAX_TOKENS_PICKS, None
    elif model == "grok":
        picks_max_tokens, picks_thinking_budget = GROK_MAX_TOKENS_PICKS, None
    elif model == "qwen":
        picks_max_tokens, picks_thinking_budget = QWEN_MAX_TOKENS_PICKS, None
    else:
        picks_max_tokens, picks_thinking_budget = MAX_OUTPUT_TOKENS, None
    response_text, input_tokens, output_tokens, reasoning_tokens = _call_api_with_retry(
        model, input_messages, api_key, model_id, reasoning_effort,
        web_search=True, max_tokens=picks_max_tokens,
        system_text=system_text, prompt_text=prompt_text,
        thinking_budget=picks_thinking_budget,
    )

    # --- Token cap warning -----------------------------------------------
    if output_tokens >= picks_max_tokens - 500:
        print(f"WARNING: {model} output tokens ({output_tokens:,}) near max_tokens cap "
              f"({picks_max_tokens:,}).")
        print(f"         Response may be truncated. Consider increasing max_tokens.")

    # --- Kimi empty-content guard ----------------------------------------
    # _call_kimi returns "" when content was empty (reasoning trace consumed
    # the full shared token budget before structured output was written).
    # Write the reasoning trace to a diagnostic file — NEVER to {model}_raw.txt,
    # which is reserved for structured picks output only. Fail loudly.
    if model == "kimi" and not response_text:
        out_dir = PROJECT_ROOT / "picks" / sport / date
        out_dir.mkdir(parents=True, exist_ok=True)
        rc = _kimi_diagnostic_reasoning.get("content", "")
        if rc:
            diag_path = out_dir / f"{model}_reasoning_raw.txt"
            diag_path.write_text(rc, encoding="utf-8")
            print(f"\n  Diagnostic : reasoning trace saved -> {diag_path.name}")
            print(f"               ({len(rc):,} chars — thinking trace only, NOT parseable as picks)")
        print(f"\nERROR: Kimi picks call FAILED — content field was empty.")
        print(f"  {model}_raw.txt has NOT been written.")
        print(f"  The reasoning trace consumed the full max_tokens={picks_max_tokens:,} budget.")
        print(f"  Retry: python scripts/query_model.py --model {model} --date {date}")
        sys.exit(1)

    # --- Save output ------------------------------------------------------
    out_dir  = PROJECT_ROOT / "picks" / sport / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{model}_raw.txt"
    out_path.write_text(response_text, encoding="utf-8")

    # --- Verify the file was written with content -------------------------
    written_bytes = out_path.stat().st_size
    if written_bytes == 0:
        print(f"ERROR: output file is empty after write -- {out_path}")
        sys.exit(1)
    print(f"  File verified: {written_bytes:,} bytes")

    # --- Summary ----------------------------------------------------------
    print()
    print("Done.")
    _print_usage(display_label, model_id, reasoning_effort,
                 input_tokens, output_tokens, reasoning_tokens, out_path)


# ─────────────────────────────────────────────────────────────────────────────
# POST-MORTEM MODE
# ─────────────────────────────────────────────────────────────────────────────

def _load_rotowire_index(sport: str, date: str) -> dict:
    """
    Load rotowire_lineups.json and return a lookup keyed by frozenset of team abbrs.
    Returns {} if the file is absent (pre-game capture was not run or failed).
    """
    path = PROJECT_ROOT / "data" / sport / date / "rotowire_lineups.json"
    if not path.exists():
        return {}
    try:
        games = json.loads(path.read_text(encoding="utf-8"))
        return {
            frozenset({g["away_abbr"], g["home_abbr"]}): g
            for g in games
            if "away_abbr" in g and "home_abbr" in g
        }
    except Exception:
        return {}


def _fmt_rotowire_side(order: list[dict], abbr: str, vs_hand: str, status: str) -> list[str]:
    """
    Format one side's Rotowire expected batting order into prompt lines.
    vs_hand is the opposing SP hand ('L' or 'R') — for label context only.
    """
    hand_label = "LHP" if vs_hand == "L" else "RHP"
    lines = [f"{abbr} EXPECTED ORDER (vs {hand_label}, status: {status}):"]
    for p in order:
        bat_order = p.get("bat_order", "?")
        name      = p.get("name", "?")
        pos       = p.get("pos", "")
        bats      = p.get("bats", "")
        pos_bats  = f"{pos}/{bats}" if pos and bats else (pos or bats)
        lines.append(f"  {bat_order}. {name}" + (f" ({pos_bats})" if pos_bats else ""))
    return lines


def _build_confirmed_section(model: str, sport: str, date: str) -> str | None:
    """
    Build the CONFIRMED DATA EVALUATION block for the post-mortem prompt.

    Only includes games where this model BET or LEANED (not passes).
    Reads:
      - picks/{sport}/{date}/{model}.json              (to find bet/lean games)
      - data/{sport}/{date}/confirmed_data.json        (actual lineup + umpire)
      - data/{sport}/{date}/rotowire_lineups.json      (pre-game expected lineup,
                                                        optional — added if present)

    Returns a formatted block string, or None if confirmed_data.json is absent
    (i.e. fetch_confirmed_data.py hasn't been run yet for this slate).
    """
    picks_path    = PROJECT_ROOT / "picks" / sport / date / f"{model}.json"
    confirmed_path = PROJECT_ROOT / "data" / sport / date / "confirmed_data.json"

    if not confirmed_path.exists():
        return None
    if not picks_path.exists():
        return None

    try:
        picks_raw      = json.loads(picks_path.read_text(encoding="utf-8"))
        confirmed_data = json.loads(confirmed_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    # Load Rotowire pre-game expected lineups (optional — absent if run_daily.py
    # was not executed that morning or Rotowire was unreachable).
    rotowire_idx = _load_rotowire_index(sport, date)

    # picks JSON is {"picks": [...], ...} — extract the list
    picks_data = picks_raw.get("picks", picks_raw) if isinstance(picks_raw, dict) else picks_raw

    games_confirmed = confirmed_data.get("games", {})

    # Find games where model BET or LEANED
    engaged_games = []
    for pick in picks_data:
        action = (pick.get("action") or "").lower()
        if action not in ("bet", "lean"):
            continue
        matchup = pick.get("matchup", "")
        if matchup not in games_confirmed:
            continue
        engaged_games.append((pick, games_confirmed[matchup]))

    if not engaged_games:
        return None

    has_rotowire = bool(rotowire_idx)
    ANTI_HINDSIGHT = (
        "## CONFIRMED DATA EVALUATION (lineup + umpire)\n"
        + (
            "PRE-GAME EXPECTED (Rotowire) is shown first — this WAS knowable before "
            "first pitch. ACTUAL CONFIRMED (MLB API) follows — this was NOT available "
            "pre-game. "
            if has_rotowire else
            "The confirmed lineup was NOT available pre-game. "
        )
        + "Using ONLY the pre-game STATS of these players/umpire — NOT the game result — "
        "would this confirmed data have changed your pick? You MUST cite a specific "
        "pre-game-knowable reason (platoon mismatch, key hitter resting, umpire zone "
        "tendency). If the confirmed lineup matches your team-level assumption, say "
        "'no change'. Do NOT reason from what happened in the game. A would-change "
        "call with no specific pre-game reason is invalid."
    )

    blocks = [ANTI_HINDSIGHT]

    for pick, cd in engaged_games:
        matchup      = pick.get("matchup", "")
        action       = pick.get("action", "").upper()
        pick_side    = pick.get("pick_side", "")
        price        = pick.get("price", "")
        units        = pick.get("units", "")
        bet_type     = pick.get("bet_type", "ML")
        away_abbr, _, home_abbr = matchup.partition(" @ ")

        # Resolve pick label
        if action == "BET":
            price_str = f" {price}" if price and price != "N/A" else ""
            units_str = f" ({units}u)" if units and units not in ("PASS", "LEAN") else ""
            call_label = f"BET {pick_side} {bet_type}{price_str}{units_str}"
        else:
            call_label = f"LEAN {pick_side}"

        # Away team bats vs home SP; home team bats vs away SP
        away_hand = cd.get("away_sp_hand", "R")
        home_hand = cd.get("home_sp_hand", "R")

        block_lines = [
            f"\n---\n",
            f"### GAME: {matchup} — YOUR CALL: {call_label}\n",
        ]

        # ── PRE-GAME EXPECTED (Rotowire) ──────────────────────────────────────
        # Show what was knowable before first pitch, if we captured it.
        rw_game = rotowire_idx.get(frozenset({away_abbr, home_abbr}))
        if rw_game:
            block_lines.append("#### PRE-GAME EXPECTED LINEUPS (Rotowire — knowable before first pitch)")
            rw_away_hand = cd.get("away_sp_hand", "R")  # away SP throws → home batters face it
            rw_home_hand = cd.get("home_sp_hand", "R")  # home SP throws → away batters face it
            away_rw_lines = _fmt_rotowire_side(
                rw_game.get("away_order", []),
                away_abbr,
                vs_hand=rw_home_hand,   # away bats vs home SP
                status=rw_game.get("away_status", "unknown"),
            )
            home_rw_lines = _fmt_rotowire_side(
                rw_game.get("home_order", []),
                home_abbr,
                vs_hand=rw_away_hand,   # home bats vs away SP
                status=rw_game.get("home_status", "unknown"),
            )
            block_lines.extend(away_rw_lines)
            block_lines.append("")
            block_lines.extend(home_rw_lines)
            block_lines.append("")
            block_lines.append("#### ACTUAL CONFIRMED LINEUPS (MLB API — post-game)")

        # Away batting order (bats vs home SP hand)
        away_lu  = cd.get("away_lineup", [])
        away_avg = cd.get("away_avg_wrc")
        block_lines.append(
            f"{away_abbr} BATTING ORDER (vs {home_hand}HP):"
        )
        for i, batter in enumerate(away_lu, 1):
            wrc = batter.get("wrc_plus")
            wrc_str = f"wRC+ vs {'LHP' if home_hand == 'L' else 'RHP'}: {int(wrc)}" if wrc is not None else "wRC+: N/A"
            block_lines.append(f"  {i}. {batter['name']} — {wrc_str}")
        if away_avg is not None:
            block_lines.append(f"  [lineup avg wRC+: {away_avg}]")

        block_lines.append("")

        # Home batting order (bats vs away SP hand)
        home_lu  = cd.get("home_lineup", [])
        home_avg = cd.get("home_avg_wrc")
        block_lines.append(
            f"{home_abbr} BATTING ORDER (vs {away_hand}HP):"
        )
        for i, batter in enumerate(home_lu, 1):
            wrc = batter.get("wrc_plus")
            wrc_str = f"wRC+ vs {'LHP' if away_hand == 'L' else 'RHP'}: {int(wrc)}" if wrc is not None else "wRC+: N/A"
            block_lines.append(f"  {i}. {batter['name']} — {wrc_str}")
        if home_avg is not None:
            block_lines.append(f"  [lineup avg wRC+: {home_avg}]")

        block_lines.append("")
        umpire = cd.get("umpire") or "unknown"
        block_lines.append(f"HOME PLATE UMPIRE: {umpire}")
        block_lines.append("")

        # Response fields
        response_fields = []
        if rw_game:
            # Model can compare expected vs actual — did the lineup change materially?
            response_fields.append(
                "EXPECTED vs ACTUAL: [lineup matched / key change — who was added/dropped]"
            )
        response_fields.extend([
            "CONFIRMED LINEUP vs YOUR ASSUMPTION: [materially different / roughly as expected]",
            "WOULD CHANGE? [no change / lean→bet / bet→pass / bet→other side / bet→higher stake / bet→lower stake]",
            "PRE-GAME REASON (required if WOULD CHANGE ≠ no change):",
            "UMPIRE WOULD CHANGE? [yes/no] — pre-game reason:",
        ])
        block_lines.extend(response_fields)

        blocks.append("\n".join(block_lines))

    return "\n".join(blocks)


def _build_outcome_summaries(model: str, sport: str, date: str) -> str | None:
    """
    Build one OUTCOME line per game the model engaged with, using:
      - picks/{sport}/{date}/{model}.json  (model's picks + graded results)
      - results/{sport}/{date}/results.json  (final scores)

    Returns a formatted block string, or None if either file is missing.
    Only includes games present in the model's picks JSON (all games they saw).
    Bets and leans listed first, passes after, sorted by action within groups.

    NOTE: Starter IP/ER and "bullpen decisive" are not in the current data files.
    The format uses scores + model's call + graded result, which is fully factual.
    """
    picks_path   = PROJECT_ROOT / "picks" / sport / date / f"{model}.json"
    results_path = PROJECT_ROOT / "results" / sport / date / "results.json"

    if not picks_path.exists() or not results_path.exists():
        return None

    try:
        picks_data   = json.loads(picks_path.read_text(encoding="utf-8"))
        results_data = json.loads(results_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Build a lookup: game_id -> result record
    result_by_id = {g["game_id"]: g for g in results_data.get("games", [])}

    # Also build lookup by matchup string as fallback (away_abbr @ home_abbr)
    result_by_matchup = {}
    for g in results_data.get("games", []):
        key = f"{g.get('away_abbr','')} @ {g.get('home_abbr','')}"
        result_by_matchup[key] = g

    picks = picks_data.get("picks", [])

    # Sort: bets first, then leans, then passes (within each group keep original order)
    ACTION_RANK = {"bet": 0, "lean": 1, "pass": 2}
    picks_sorted = sorted(picks, key=lambda p: ACTION_RANK.get(p.get("action", "pass"), 2))

    lines = []
    for p in picks_sorted:
        matchup   = p.get("matchup", "")
        game_id   = p.get("game_id", "")
        action    = p.get("action", "pass")
        pick_side = p.get("pick_side")
        price     = p.get("price")
        result    = p.get("result")  # WIN / LOSS / PUSH / None (ungraded)

        # Look up the final score
        res = result_by_id.get(game_id) or result_by_matchup.get(matchup)
        if res:
            away  = res.get("away_abbr", "?")
            home  = res.get("home_abbr", "?")
            ascore = res.get("away_score")
            hscore = res.get("home_score")
            score_str = f"{away} {ascore} @ {home} {hscore}" if ascore is not None else matchup
            winner_abbr = away if res.get("winner") == "away" else home
        else:
            score_str   = matchup
            winner_abbr = "?"

        # Resolve pick_side ("away"/"home") to team abbreviation using result data
        def _side_to_abbr(side, result_record):
            if not side or not result_record:
                return side or "?"
            if side == "away":
                return result_record.get("away_abbr", side)
            if side == "home":
                return result_record.get("home_abbr", side)
            return side  # already an abbr or unknown

        # Build the "your call" portion
        if action == "bet" and pick_side:
            team_abbr  = _side_to_abbr(pick_side, res)
            price_str  = f" {int(price):+d}" if isinstance(price, (int, float)) else (f" {price}" if price else "")
            result_str = f" -> {result.upper()}" if result else " -> (ungraded)"
            call = f"Bet: {team_abbr}{price_str}{result_str}"
        elif action == "lean" and pick_side:
            team_abbr = _side_to_abbr(pick_side, res)
            call = f"Lean: {team_abbr} (no stake)"
        else:
            call = "Pass"

        lines.append(f"OUTCOME: {score_str} | Winner: {winner_abbr} | {call}")

    if not lines:
        return None

    anti_hindsight = (
        "GAME OUTCOMES below are factual results. Use them ONLY to identify whether a "
        "signal that was AVAILABLE IN THE PRE-GAME DATA predicted the outcome. "
        "Do NOT reason from the result itself ('I should have known X would lose'). "
        "A bet with sound pre-game process and a bad result is still a good bet. "
        "If no pre-game signal pointed to the outcome, the result was variance — say so."
    )

    block = "GAME OUTCOMES (factual — for post-mortem reference only)\n"
    block += anti_hindsight + "\n\n"
    block += "\n".join(lines)
    return block


def run_postmortem(model: str, sport: str, date: str, dry_run: bool, reasoning_effort: str):
    """
    Read the post-mortem prompt and the model's original picks, send a review
    request to the API, and write the response to two destinations.
    Web search is disabled for post-mortem calls -- results are provided.

    Per-model file   : picks/{sport}/{date}/{model}_postmortem.txt   (written, primary output)
    Aggregate file   : picks/{sport}/{date}/post_mortem_{date}.txt   (appended, human-readable)
    Original picks   : picks/{sport}/{date}/{model}_raw.txt          (context only)
    """
    # --- Read post-mortem file --------------------------------------------
    pm_path = PROJECT_ROOT / "picks" / sport / date / f"post_mortem_{date}.txt"

    if not pm_path.exists():
        print(f"ERROR: Post-mortem file not found: {pm_path}")
        print(f"       Grade picks first to generate results, then fill in the post-mortem file.")
        sys.exit(1)

    pm_text_full = pm_path.read_text(encoding="utf-8")

    # Strip any previously appended model responses so they are not sent to
    # subsequent models. Responses are separated by "\n\n---\n## MODEL RESPONSE".
    _sep = "\n\n---\n## "
    _cut = pm_text_full.find(_sep)
    pm_text = pm_text_full[:_cut] if _cut != -1 else pm_text_full
    if _cut != -1:
        stripped_models = len(pm_text_full[_cut:].split(_sep)) - 1
        print(f"Post-mortem file : {pm_path}  (stripped {stripped_models} prior response(s))")
    else:
        print(f"Post-mortem file : {pm_path}")

    # --- Read original picks (optional context) ---------------------------
    raw_path = PROJECT_ROOT / "picks" / sport / date / f"{model}_raw.txt"
    raw_text = None

    if raw_path.exists():
        raw_text = raw_path.read_text(encoding="utf-8")
        print(f"Original picks   : {raw_path}  ({len(raw_text):,} chars)")
    else:
        print(f"WARNING: Original picks not found at {raw_path}")
        print(f"         Continuing without picks context.")

    print(f"Reasoning effort : {reasoning_effort}")
    print(f"Web search       : disabled")

    # --- Integrity gate: skip if picks JSON has zero parsed game blocks -------
    # counts.games == 0 means the picks call either failed (empty raw file) or
    # the parser could not extract game blocks from the response. Either way the
    # model has no structured game context to review — firing the API call would
    # produce fabricated analysis with no grounding.
    # NOTE: counts.bets == 0 is NOT a gate trigger — all-pass slates are valid.
    picks_json_path = PROJECT_ROOT / "picks" / sport / date / f"{model}.json"
    if picks_json_path.exists():
        try:
            picks_doc    = json.loads(picks_json_path.read_text(encoding="utf-8"))
            games_parsed = picks_doc.get("counts", {}).get("games", None)
            if games_parsed == 0:
                raw_size = raw_path.stat().st_size if raw_path.exists() else 0
                if raw_size == 0:
                    cause = "empty raw file (picks fetch failed or 0-byte response)"
                else:
                    cause = f"parse failure ({raw_size:,}-byte raw file — log_picks extracted 0 game blocks)"
                print(f"\nINTEGRITY GATE: {model}.json has counts.games=0 — {cause}")
                print(f"Post-mortem skipped: no structured game context available to review.")
                print(f"Fix picks first, then retry post-mortem:")
                print(f"  python scripts/query_model.py --model {model} --date {date}")
                print(f"  python scripts/query_model.py --model {model} --date {date} --postmortem")
                sys.exit(1)
        except (json.JSONDecodeError, OSError):
            pass  # malformed JSON — proceed and let _build_outcome_summaries handle it

    # --- Resolve API credentials early (needed for placeholder substitution) -
    api_key, model_id, display_label = _resolve_model_config(model)

    # --- Substitute model name placeholder in the post-mortem text --------
    # The post-mortem template contains "[write your model name here...]" as a
    # placeholder. Replace it with the actual model label so the model sees its
    # own name in the questions (e.g. "What did Grok get right?").
    pm_text_filled = pm_text.replace(
        "[write your model name here...]", display_label
    )
    if pm_text_filled != pm_text:
        print(f"Placeholder      : substituted '{display_label}' for name placeholder")

    # --- Build per-game outcome summaries (factual scores + model's call) ---
    outcome_block = _build_outcome_summaries(model, sport, date)
    if outcome_block:
        print(f"Outcome summaries: built ({outcome_block.count('OUTCOME:')} games)")
    else:
        print(f"Outcome summaries: not available (missing picks JSON or results JSON)")

    # --- Build confirmed data evaluation section (lineup + umpire) ----------
    # Only injected if fetch_confirmed_data.py has been run for this date.
    # Covers bet/lean games only — not passes.
    confirmed_block = _build_confirmed_section(model, sport, date)
    if confirmed_block:
        print(f"Confirmed data:    built (bet/lean games only)")
    else:
        print(f"Confirmed data:    not available (run fetch_confirmed_data.py first)")

    # --- Build input list -------------------------------------------------
    # System message sets the review framing; original picks give context.
    system_msg = (
        "You are reviewing your own MLB betting picks from earlier today. "
        "You will be given your original picks and the actual game results. "
        "Provide honest analysis of what worked, what failed, and what you would change."
    )

    input_messages = [{"role": "system", "content": system_msg}]

    if raw_text:
        input_messages.append({
            "role": "user",
            "content": f"Here were your original picks:\n\n{raw_text}"
        })

    # Assemble post-mortem content: outcome summaries → post-mortem questions
    # → confirmed data evaluation (appended last so it doesn't contaminate the
    # standard post-mortem analysis with pre-game data the model didn't have).
    pm_content = pm_text_filled
    if outcome_block:
        pm_content = outcome_block + "\n\n---\n\n" + pm_text_filled
    if confirmed_block:
        pm_content = pm_content + "\n\n" + confirmed_block

    input_messages.append({
        "role": "user",
        "content": f"Here are the results and post-mortem questions:\n\n{pm_content}"
    })

    # --- Dry run exit point -----------------------------------------------
    if dry_run:
        print()
        print("--- DRY RUN: would send these messages to the API ---")
        for i, msg in enumerate(input_messages, 1):
            role    = msg["role"]
            content = msg["content"]
            # Encode to ASCII with replacement so non-ASCII characters in
            # the post-mortem file do not crash the Windows console (cp1252).
            safe    = content.encode("ascii", errors="replace").decode("ascii")
            preview = safe[:300].replace("\n", "\n    ")
            print(f"  Message {i} ({role}):")
            print(f"    {preview}")
            if len(content) > 300:
                print(f"    ... [{len(content) - 300} more chars]")
        print()
        print("No API call made.")
        return

    # --- API call ---------------------------------------------------------
    if model in ANTHROPIC_MODELS:
        endpoint = "https://api.anthropic.com"
    elif model == "grok":
        endpoint = XAI_BASE_URL
    elif model == "deepseek":
        endpoint = DEEPSEEK_BASE_URL
    elif model == "kimi":
        endpoint = KIMI_BASE_URL
    elif model == "qwen":
        endpoint = QWEN_BASE_URL
    elif model == "gemini":
        endpoint = GEMINI_BASE_URL
    else:
        endpoint = "https://api.openai.com/v1"
    print(f"Model ID         : {model_id}")
    print(f"Sending to       : {endpoint}  ...")

    if model in ANTHROPIC_MODELS:
        pm_max_tokens = ANTHROPIC_MAX_TOKENS_POSTMORTEM
    elif model == "gemini":
        pm_max_tokens = GEMINI_MAX_TOKENS_POSTMORTEM
    elif model == "deepseek":
        pm_max_tokens = DEEPSEEK_MAX_TOKENS_POSTMORTEM
    elif model == "kimi":
        pm_max_tokens = KIMI_MAX_TOKENS_POSTMORTEM
    elif model == "grok":
        pm_max_tokens = GROK_MAX_TOKENS_POSTMORTEM
    else:
        pm_max_tokens = MAX_OUTPUT_TOKENS
    # For Anthropic models the system/prompt split is reconstructed from input_messages
    pm_system = input_messages[0]["content"] if input_messages else ""
    pm_user   = "\n\n".join(m["content"] for m in input_messages[1:])
    response_text, input_tokens, output_tokens, reasoning_tokens = _call_api_with_retry(
        model, input_messages, api_key, model_id, reasoning_effort,
        web_search=False, max_tokens=pm_max_tokens,
        system_text=pm_system, prompt_text=pm_user,
    )

    # --- Token cap warning -----------------------------------------------
    if output_tokens >= pm_max_tokens - 500:
        print(f"WARNING: {model} output tokens ({output_tokens:,}) near max_tokens cap "
              f"({pm_max_tokens:,}).")
        print(f"         Response may be truncated. Consider increasing max_tokens.")

    # --- Write per-model file (primary output) ----------------------------
    # This is the canonical output for v2. Each model gets its own file so
    # responses can be reviewed and acted on independently.
    per_model_path = PROJECT_ROOT / "picks" / sport / date / f"{model}_postmortem.txt"
    per_model_path.write_text(response_text, encoding="utf-8")
    print(f"Per-model file  : {per_model_path.relative_to(PROJECT_ROOT)}  ({len(response_text):,} chars)")

    # --- Append to shared aggregate file (human-readable summary) ---------
    # Separator format is kept so the file remains grep-friendly and human-readable.
    # Nothing reads this file programmatically -- it is for review only.
    separator = f"\n\n---\n## {model.upper()} RESPONSE\n\n"
    with open(pm_path, "a", encoding="utf-8") as f:
        f.write(separator)
        f.write(response_text)
    print(f"Aggregate file  : {pm_path.relative_to(PROJECT_ROOT)}  ({len(separator) + len(response_text):,} chars added)")

    # --- Summary ----------------------------------------------------------
    print()
    print("Done.")
    _print_usage(display_label, model_id, reasoning_effort,
                 input_tokens, output_tokens, reasoning_tokens, pm_path)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIRM-CHECK MODE
# ─────────────────────────────────────────────────────────────────────────────

# Per-model output token budgets for confirm-check calls.
# Responses are short (4 fields per pick, bounded game set) —
# half the picks budget is generous headroom for every model.
_CONFIRM_MAX_TOKENS: dict = {
    "grok":     8000,
    "chatgpt":  8000,
    "deepseek": 8000,
    "kimi":    16000,
    "qwen":     8000,
    "gemini":   8000,
    "opus":     4000,
    "fable":    4000,
}

# Valid structured-response field values (normalised to upper/lower after parse)
_CONFIRM_FIELDS   = ("OUTCOME", "DRIVER", "CITED_FACT", "NEW_UNITS")
_VALID_OUTCOMES   = {"HOLD", "CANCEL", "DOWNGRADE", "UPGRADE"}
_VALID_DRIVERS    = {"lineup", "umpire", "price", "none"}


def _slate_ceiling(n_games: int) -> int:
    """Slate bet ceiling by game count — mirrors the staking rules in CLAUDE.md."""
    if n_games <= 7:
        return 1
    elif n_games <= 14:
        return 2
    return 3


def _parse_confirm_response(
    response_text: str,
    cluster_picks: list,
) -> tuple:
    """
    Parse the model's confirm-check response into one result dict per pick.

    The model is instructed to produce one block per pick:

        PICK: MIL ML  [market:ML]
        OUTCOME: HOLD
        DRIVER: none
        CITED_FACT: confirmed order matches assumed lineup; Misiorowski still starting
        NEW_UNITS: 1

    Matching strategy:
      1. Split on "PICK:" lines to get one chunk per pick.
      2. Within each chunk, extract OUTCOME/DRIVER/CITED_FACT/NEW_UNITS.
      3. Match back to a pick in cluster_picks via [gid:...] tag (primary)
         or fuzzy pick_raw + market (fallback).

    Returns (results, warnings) where results is a list of result dicts
    and warnings is a list of human-readable problem strings.
    """
    import re as _re

    results:  list = []
    warnings: list = []

    # Build a fast lookup: (game_id, pick_market) -> pick
    pick_by_key: dict = {}
    for pick in cluster_picks:
        key = (pick.get("game_id", ""), (pick.get("pick_market") or "").lower())
        pick_by_key[key] = pick

    # Split on PICK: lines (allow leading ##, bold markers, whitespace)
    pick_header_re = _re.compile(
        r'^\s*(?:#+\s*|[*_]{1,2})?PICK\s*:',
        _re.IGNORECASE | _re.MULTILINE,
    )
    chunks = pick_header_re.split(response_text)
    if chunks:
        chunks = chunks[1:]   # discard pre-amble before first PICK:

    if not chunks:
        warnings.append("No PICK: blocks found in response — entire response unparsed")
        return results, warnings

    field_re = _re.compile(
        r'^\s*(?:#+\s*|[*_]{1,2})?(OUTCOME|DRIVER|CITED_FACT|NEW_UNITS)\s*:\s*(.+)',
        _re.IGNORECASE | _re.MULTILINE,
    )

    matched_pairs: set = set()   # (game_id, market) pairs already claimed by a gid-matched block
    for chunk in chunks:
        header_line = chunk.split("\n")[0].strip()

        # Primary: extract game_id from [gid:...] tag written by build_prompt.py
        gid_match   = _re.search(r'\[gid:([^\]]+)\]', header_line, _re.IGNORECASE)
        block_gid   = gid_match.group(1).strip() if gid_match else None

        # Market from [market:XX] tag
        mkt_match    = _re.search(r'\[market:([^\]]+)\]', header_line, _re.IGNORECASE)
        block_market = mkt_match.group(1).strip().lower() if mkt_match else None

        # pick_raw: everything before the first [...] tag
        block_raw = _re.sub(r'\[.*', '', header_line).strip()

        # Extract the four fields from the rest of the chunk
        field_map: dict = {}
        for m in field_re.finditer(chunk):
            key = m.group(1).upper()
            val = _re.sub(r'[*_]+$', '', m.group(2).strip()).strip()
            field_map[key] = val

        missing = [f for f in _CONFIRM_FIELDS if f not in field_map]
        block_warning = (
            f"Block for '{block_raw}' missing fields {missing} — "
            f"parsed what was found; review manually"
        ) if missing else None

        # Normalise OUTCOME
        outcome_raw = field_map.get("OUTCOME", "")
        outcome     = outcome_raw.upper().split()[0] if outcome_raw else ""
        if outcome not in _VALID_OUTCOMES:
            warnings.append(
                f"Block for '{block_raw}': unrecognised OUTCOME '{outcome_raw}' — "
                f"treated as parse failure, pick will auto-HOLD"
            )
            outcome = None

        # Normalise DRIVER
        driver_raw = field_map.get("DRIVER", "")
        driver     = driver_raw.lower().split()[0] if driver_raw else "none"
        if driver not in _VALID_DRIVERS:
            driver = "none"

        # Parse NEW_UNITS — first numeric token
        nu_raw   = field_map.get("NEW_UNITS", "")
        nu_match = _re.search(r'(\d+(?:\.\d+)?)', nu_raw)
        try:
            new_units = float(nu_match.group(1)) if nu_match else None
            if new_units is not None:
                new_units = int(new_units) if new_units == int(new_units) else new_units
        except (ValueError, AttributeError):
            new_units = None

        cited_fact = field_map.get("CITED_FACT", "")

        # Match back to a pick: primary path via game_id + market
        matched_pick = None
        if block_gid and block_market:
            matched_pick = pick_by_key.get((block_gid, block_market))

        # Fallback: only when gid absent. Match iff exactly one unclaimed pick of
        # this market exists in the cluster — unambiguous. Two or more = don't guess.
        if matched_pick is None and not block_gid and block_market:
            unclaimed = [
                p for p in cluster_picks
                if (p.get("pick_market") or "").lower() == block_market
                and (p.get("game_id"), (p.get("pick_market") or "").lower()) not in matched_pairs
            ]
            if len(unclaimed) == 1:
                matched_pick = unclaimed[0]
            elif len(unclaimed) > 1:
                warnings.append(
                    f"Block for '{block_raw}' [market:{block_market}]: gid absent and "
                    f"{len(unclaimed)} unclaimed picks of market '{block_market}' in cluster "
                    f"— ambiguous, block skipped (pick will auto-HOLD)"
                )
                continue

        if matched_pick is None:
            warnings.append(
                f"Block for '{block_raw}' [gid:{block_gid} market:{block_market}] "
                f"could not be matched to any pick — block skipped (pick will auto-HOLD)"
            )
            continue

        # Mark claimed so a later block in this call can't bind to the same pick
        matched_pairs.add((matched_pick.get("game_id"), (matched_pick.get("pick_market") or "").lower()))

        results.append({
            "game_id":         matched_pick.get("game_id"),
            "matchup":         matched_pick.get("matchup"),
            "pick_raw":        matched_pick.get("pick_raw"),
            "pick_market":     matched_pick.get("pick_market"),
            "pick_side":       matched_pick.get("pick_side"),
            "original_units":  matched_pick.get("units"),
            "original_price":  matched_pick.get("price"),
            "original_action": matched_pick.get("action"),
            "outcome":         outcome,
            "driver":          driver,
            "cited_fact":      cited_fact,
            "new_units_raw":   new_units,   # model's stated value before guards
            "new_units":       new_units,   # may be overridden by guards below
            "guard_override":  None,
            "parse_warning":   block_warning,
        })

    return results, warnings


def _total_wagered_units(model: str, sport: str, date: str, root: Path) -> float:
    """
    Sum units already wagered across all bet picks in {model}.json for this date.
    Used by the UPGRADE guard to enforce the Run-1 slate ceiling slate-wide.
    """
    picks_path = root / "picks" / sport / date / f"{model}.json"
    if not picks_path.exists():
        return 0.0
    try:
        doc = json.loads(picks_path.read_text(encoding="utf-8"))
        return sum(
            float(p.get("units") or 0)
            for p in doc.get("picks", [])
            if (p.get("action") or "").lower() == "bet"
        )
    except Exception:
        return 0.0


def _n_slate_games(sport: str, date: str, root: Path) -> int:
    """Return total game count for the slate (used by ceiling calculation)."""
    games_path = root / "data" / sport / date / "games.json"
    if not games_path.exists():
        return 0
    try:
        return len(json.loads(games_path.read_text(encoding="utf-8")))
    except Exception:
        return 0


def _apply_confirm_guards(
    result: dict,
    model:  str,
    sport:  str,
    date:   str,
    root:   Path,
) -> dict:
    """
    Enforce hard guards on a parsed confirm-check result. Mutates and returns
    result, setting guard_override to a description when any rule fires.

    Guards (in priority order):
      1. Parse failure (outcome is None) — force HOLD at original units.
      2. Price absent/suspect at Run 1 — block UPGRADE, force HOLD.
      3. Absolute unit ceiling: new_units > 3 is impossible; clamp to 3.
      4. UPGRADE sanity: new_units must be strictly > original_units.
      5. Slate ceiling (slate-wide): total already wagered + delta must not
         exceed the ceiling for this slate's game count.
    """
    outcome        = result.get("outcome")
    new_units      = result.get("new_units")
    original_units = result.get("original_units") or 0
    original_price = result.get("original_price")

    overrides = []

    # Guard 1: parse failure
    if outcome is None:
        result["outcome"]   = "HOLD"
        result["new_units"] = original_units
        overrides.append("parse_failure→HOLD at original units")
        outcome   = "HOLD"
        new_units = original_units

    # Guard 2: price absent at Run 1 — can't UPGRADE into a real bet
    price_absent = (
        original_price is None
        or str(original_price).strip() in ("", "—", "N/A", "absent")
    )
    if price_absent and outcome == "UPGRADE":
        result["outcome"]   = "HOLD"
        result["new_units"] = original_units
        overrides.append("price_absent→UPGRADE blocked, forced HOLD")
        outcome   = "HOLD"
        new_units = original_units

    # Guard 3: absolute unit cap (3u is the hard ceiling per staking rules)
    if new_units is not None and new_units > 3:
        overrides.append(f"unit_cap→new_units clamped {new_units}→3")
        result["new_units"] = 3
        new_units = 3

    # Guard 4: UPGRADE must strictly increase units
    if outcome == "UPGRADE":
        if new_units is None or new_units <= original_units:
            result["outcome"]   = "HOLD"
            result["new_units"] = original_units
            overrides.append(
                f"upgrade_no_increase→HOLD "
                f"(new_units={new_units} not > original={original_units})"
            )
            outcome   = "HOLD"
            new_units = original_units

    # Guard 5: slate ceiling (slate-wide, not cluster-wide).
    # Only applies on UPGRADE — HOLD adds no new exposure so the ceiling
    # is irrelevant even if Run-1 bets already fill it.
    if outcome == "UPGRADE" and not price_absent:
        n_games     = _n_slate_games(sport, date, root)
        ceiling     = _slate_ceiling(n_games)
        already_bet = _total_wagered_units(model, sport, date, root)
        # 0 is a valid value (CANCEL / downgrade-to-zero), not a missing field
        final_units = result.get("new_units") if result.get("new_units") is not None else original_units
        delta       = max(0.0, float(final_units) - float(original_units))
        if already_bet + delta > ceiling:
            headroom = max(0.0, ceiling - already_bet)
            if headroom <= 0:
                result["outcome"]   = "HOLD"
                result["new_units"] = original_units
                overrides.append(
                    f"slate_ceiling→UPGRADE blocked "
                    f"(already {already_bet}u wagered, ceiling {ceiling}u for {n_games} games)"
                )
            else:
                capped = original_units + headroom
                overrides.append(
                    f"slate_ceiling→new_units capped {final_units}→{capped} "
                    f"(ceiling {ceiling}u, already {already_bet}u)"
                )
                result["new_units"] = capped

    if overrides:
        result["guard_override"] = "; ".join(overrides)

    return result


def run_confirm_check(
    model:            str,
    sport:            str,
    date:             str,
    game_ids:         list,
    dry_run:          bool,
    reasoning_effort: str,
):
    """
    Send one confirm-check API call for this model covering the given game_ids,
    parse the structured response, apply guards, and write
    daily/{sport}/{date}/{model}_confirm.json.

    game_ids is the list assembled by run_lineup_watcher.py for this cluster.
    Only picks for games in this list are included in the prompt and output.

    The prompt file confirm_prompt_{model}.md was written by
    build_prompt.py --confirm-check and contains one ## GAME: block per
    confirmed game, each header tagged with [gid:{game_id}] for reliable
    matching without any matchup-string join.

    Reads:
      daily/{sport}/{date}/confirm_system_{model}.md
      daily/{sport}/{date}/confirm_prompt_{model}.md
      picks/{sport}/{date}/{model}.json

    Writes (merge-appends across clusters):
      daily/{sport}/{date}/{model}_confirm.json
    """
    import re as _re
    import datetime as _dt

    daily_dir   = PROJECT_ROOT / "daily" / sport / date
    picks_path  = PROJECT_ROOT / "picks" / sport / date / f"{model}.json"
    sys_path    = daily_dir / f"confirm_system_{model}.md"
    prompt_path = daily_dir / f"confirm_prompt_{model}.md"
    out_path    = daily_dir / f"{model}_confirm.json"

    for p, label in [
        (sys_path,    "confirm_system"),
        (prompt_path, "confirm_prompt"),
        (picks_path,  "picks JSON"),
    ]:
        if not p.exists():
            print(f"ERROR: {label} file not found: {p}")
            sys.exit(1)

    system_text = sys_path.read_text(encoding="utf-8")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    picks_doc   = json.loads(picks_path.read_text(encoding="utf-8"))
    all_picks   = picks_doc.get("picks", [])

    requested_gids = set(game_ids)

    # ── Filter prompt to only the game blocks for this cluster ────────────────
    # The ## GAME: header embeds [gid:...] — extract game_id directly from
    # the header, no matchup-string join needed, doubleheader-safe.
    game_block_re = _re.compile(
        r'^(## GAME:.*?)(?=^## GAME:|\Z)',
        _re.MULTILINE | _re.DOTALL,
    )
    gid_tag_re = _re.compile(r'\[gid:([^\]]+)\]', _re.IGNORECASE)

    gid_to_block: dict = {}
    for m in game_block_re.finditer(prompt_text):
        block = m.group(1)
        hdr   = block.split("\n")[0]
        gid_m = gid_tag_re.search(hdr)
        if gid_m:
            gid_to_block[gid_m.group(1).strip()] = block

    filtered_blocks = [
        gid_to_block[gid]
        for gid in game_ids          # preserve watcher order
        if gid in gid_to_block
    ]

    missing_in_prompt = requested_gids - set(gid_to_block.keys())
    if missing_in_prompt:
        print(f"  WARNING: {len(missing_in_prompt)} game_id(s) not in confirm_prompt "
              f"(may still be unconfirmed): {missing_in_prompt}")

    if not filtered_blocks:
        print(f"  No matching game blocks for requested game_ids — nothing to send.")
        return

    filtered_prompt = "\n".join(filtered_blocks)

    # ── Collect bet/lean picks for this cluster ───────────────────────────────
    cluster_picks = [
        p for p in all_picks
        if p.get("game_id") in requested_gids
        and (p.get("action") or "").lower() in ("bet", "lean")
    ]

    print(f"  System file      : {sys_path.name}  ({len(system_text):,} chars)")
    print(f"  Games in cluster : {len(filtered_blocks)}")
    print(f"  Picks in cluster : {len(cluster_picks)}")

    # ── Dry run ───────────────────────────────────────────────────────────────
    if dry_run:
        print()
        print("--- DRY RUN: system (first 300 chars) ---")
        print(system_text[:300].encode("ascii", errors="replace").decode("ascii"))
        print()
        print("--- DRY RUN: prompt (first 500 chars) ---")
        print(filtered_prompt[:500].encode("ascii", errors="replace").decode("ascii"))
        print()
        print("No API call made.")
        return

    # ── Dispatch to the correct API ───────────────────────────────────────────
    api_key, model_id, display_label = _resolve_model_config(model)
    max_tokens = _CONFIRM_MAX_TOKENS.get(model, 4000)

    print(f"  Model            : {display_label}  ({model_id})")
    print(f"  Reasoning effort : {reasoning_effort}")
    print(f"  Max tokens       : {max_tokens}")
    print(f"  Sending to API   ...")

    input_messages = [
        {"role": "system", "content": system_text},
        {"role": "user",   "content": filtered_prompt},
    ]

    response_text, input_tokens, output_tokens, reasoning_tokens = _call_api_with_retry(
        model, input_messages, api_key, model_id, reasoning_effort,
        web_search=False,
        max_tokens=max_tokens,
        system_text=system_text,
        prompt_text=filtered_prompt,
        thinking_budget=None,
    )

    _print_usage(display_label, model_id, reasoning_effort,
                 input_tokens, output_tokens, reasoning_tokens, out_path)

    # ── Parse response ────────────────────────────────────────────────────────
    results, parse_warnings = _parse_confirm_response(response_text, cluster_picks)

    if parse_warnings:
        print(f"\n  Parse warnings ({len(parse_warnings)}):")
        for w in parse_warnings:
            print(f"    - {w}")

    # ── Apply guards ──────────────────────────────────────────────────────────
    for result in results:
        _apply_confirm_guards(result, model, sport, date, PROJECT_ROOT)

    # ── Build output entries: one per cluster pick ────────────────────────────
    # Picks with no matching parsed block get auto-HOLD with parse_warning.
    parsed_keys = {(r["game_id"], r["pick_market"]) for r in results}

    output_entries = []
    for pick in cluster_picks:
        gid    = pick.get("game_id")
        market = pick.get("pick_market")

        matched = next(
            (r for r in results
             if r.get("game_id") == gid and r.get("pick_market") == market),
            None,
        )

        if matched:
            entry = {
                # Original Run-1 pick fields — never overwritten
                "game_id":          gid,
                "matchup":          pick.get("matchup"),
                "pick_raw":         pick.get("pick_raw"),
                "pick_market":      market,
                "pick_side":        pick.get("pick_side"),
                "original_action":  pick.get("action"),
                "original_units":   pick.get("units"),
                "original_price":   pick.get("price"),
                "original_edge":    pick.get("edge"),
                "original_reason":  pick.get("reason"),
                # Confirm-check result
                "cc_outcome":        matched["outcome"],
                "cc_driver":         matched["driver"],
                "cc_cited_fact":     matched["cited_fact"],
                "cc_new_units":      matched["new_units"],
                "cc_new_units_raw":  matched["new_units_raw"],
                "cc_guard_override": matched.get("guard_override"),
                "cc_parse_warning":  matched.get("parse_warning"),
            }
        else:
            entry = {
                "game_id":          gid,
                "matchup":          pick.get("matchup"),
                "pick_raw":         pick.get("pick_raw"),
                "pick_market":      market,
                "pick_side":        pick.get("pick_side"),
                "original_action":  pick.get("action"),
                "original_units":   pick.get("units"),
                "original_price":   pick.get("price"),
                "original_edge":    pick.get("edge"),
                "original_reason":  pick.get("reason"),
                "cc_outcome":        "HOLD",
                "cc_driver":         "none",
                "cc_cited_fact":     "",
                "cc_new_units":      pick.get("units"),
                "cc_new_units_raw":  None,
                "cc_guard_override": None,
                "cc_parse_warning":  "no matching block in response — auto-HOLD",
            }

        output_entries.append(entry)

    # ── Merge with any prior-cluster entries in the same output file ──────────
    existing_entries: list = []
    if out_path.exists():
        try:
            existing_doc     = json.loads(out_path.read_text(encoding="utf-8"))
            existing_entries = existing_doc.get("picks", [])
            # Drop any stale entries for game_ids we're about to (re)write
            existing_entries = [
                e for e in existing_entries
                if e.get("game_id") not in requested_gids
            ]
        except Exception:
            existing_entries = []

    all_entries = existing_entries + output_entries

    checked_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = {
        "model":        model,
        "date":         date,
        "sport":        sport,
        "checked_at":   checked_at,
        "picks":        all_entries,
        "raw_response": response_text,
    }

    daily_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  Written -> {out_path.relative_to(PROJECT_ROOT)}")
    print(f"  Entries : {len(all_entries)} total "
          f"({len(output_entries)} this cluster, {len(existing_entries)} prior)")

    # Compact decision table
    print()
    for e in output_entries:
        guard_flag = "  [GUARD]" if e.get("cc_guard_override") else ""
        print(
            f"  {e['matchup']:<18}  {e['pick_raw']:<12}  "
            f"{e['cc_outcome']:<10}  {e['cc_driver']:<8}  "
            f"{e['original_units']}u->{e['cc_new_units']}u{guard_flag}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# AUTHORING MODE
# ─────────────────────────────────────────────────────────────────────────────

# All models are now API-connected. Tuple kept for reference; guard removed.
MANUAL_PASTE_MODELS = ()

def run_authoring(model: str, dry_run: bool, reasoning_effort: str):
    """
    Send the one-time method-authoring query to a model and save its reply as
    docs/methods/method_{model}_v1.md.

    Input file  : docs/methods/authoring_query_{model}.md
    Output file : docs/methods/method_{model}_v1.md

    Rules:
      - If method_{model}_v1.md already exists, refuses to overwrite -- prints
        a clear message and exits.
      - The authoring file is self-contained (instruction + Layer B + sample
        slate) so no daily system prompt is prepended. System message is minimal.
      - Web search disabled -- authoring is a reflection task, not a research task.
    """

    # --- Locate authoring query file ----------------------------------------
    query_path = PROJECT_ROOT / "docs" / "methods" / f"authoring_query_{model}.md"
    if not query_path.exists():
        print(f"ERROR: Authoring query file not found: {query_path}")
        print(f"       Expected: docs/methods/authoring_query_{{model}}.md")
        sys.exit(1)

    # --- Guard: refuse to overwrite an existing method doc ------------------
    output_path = PROJECT_ROOT / "docs" / "methods" / f"method_{model}_v1.md"
    if output_path.exists():
        print(f"ERROR: Method file already exists: {output_path}")
        print(f"       Remove or rename it first if you want to regenerate.")
        print(f"       Never silently overwrite a method doc.")
        sys.exit(1)

    query_text = query_path.read_text(encoding="utf-8")

    # Authoring system prompt -- must override the output-format block inside
    # the authoring query, which contains a ## GAME: template that models may
    # follow literally if the system instruction is too weak.
    system_text = (
        "You are an independent professional sports bettor writing a personal "
        "method document. Your task is to write the method document described "
        "in the user message. Do NOT produce picks, game blocks, or any "
        "## GAME: output. Output ONLY the method document text, nothing else."
    )

    print(f"Mode             : authoring")
    print(f"Query file       : {query_path}  ({len(query_text):,} chars)")
    print(f"Output file      : {output_path}")
    print(f"Reasoning effort : {reasoning_effort}")
    print(f"Web search       : disabled")

    input_messages = [
        {"role": "system", "content": system_text},
        {"role": "user",   "content": query_text},
    ]

    # --- Dry run exit point -------------------------------------------------
    if dry_run:
        print()
        print("--- DRY RUN: system message ---")
        print(f"  {system_text}")
        print()
        print("--- DRY RUN: user message (first 500 chars) ---")
        safe    = query_text[:500].encode("ascii", errors="replace").decode("ascii")
        preview = safe.replace("\n", "\n  ")
        print(f"  {preview}")
        if len(query_text) > 500:
            print(f"  ... [{len(query_text) - 500} more chars]")
        print()
        print("No API call made. Output would be written to:")
        print(f"  {output_path}")
        return

    # --- Resolve API credentials -------------------------------------------
    api_key, model_id, display_label = _resolve_model_config(model)

    if model in ANTHROPIC_MODELS:
        endpoint = "https://api.anthropic.com"
    elif model == "grok":
        endpoint = XAI_BASE_URL
    elif model == "deepseek":
        endpoint = DEEPSEEK_BASE_URL
    elif model == "kimi":
        endpoint = KIMI_BASE_URL
    elif model == "qwen":
        endpoint = QWEN_BASE_URL
    elif model == "gemini":
        endpoint = GEMINI_BASE_URL
    else:
        endpoint = "https://api.openai.com/v1"
    print(f"Model ID         : {model_id}")
    print(f"Sending to       : {endpoint}  ...")

    response_text, input_tokens, output_tokens, reasoning_tokens = _call_api_with_retry(
        model, input_messages, api_key, model_id, reasoning_effort,
        web_search=False, max_tokens=MAX_OUTPUT_TOKENS,
        system_text=system_text, prompt_text=query_text,
    )

    # --- Save output (never append -- always a fresh write) -----------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(response_text, encoding="utf-8")

    written_bytes = output_path.stat().st_size
    if written_bytes == 0:
        print(f"ERROR: output file is empty after write -- {output_path}")
        sys.exit(1)
    print(f"  File verified: {written_bytes:,} bytes")

    print()
    print("Done.")
    _print_usage(display_label, model_id, reasoning_effort,
                 input_tokens, output_tokens, reasoning_tokens, output_path)


def _highest_method_version(model: str, totals: bool = False) -> tuple[int, Path | None]:
    """
    Return (highest_version, path) for the model's method doc.
      totals=False -> method_{model}_v{N}.md (ML/RL only, excludes totals)
      totals=True  -> method_{model}_totals_v{N}.md
    Returns (0, None) if none exist.
    """
    methods_dir = PROJECT_ROOT / "docs" / "methods"
    best_v, best_path = 0, None
    pattern = f"method_{model}_totals_v*.md" if totals else f"method_{model}_v*.md"
    for f in methods_dir.glob(pattern):
        # When matching the ML/RL pattern, the totals files also match the glob
        # (method_{model}_v*.md does NOT match totals, but be explicit anyway).
        if not totals and "_totals_v" in f.stem:
            continue
        try:
            v = int(f.stem.rsplit("_v", 1)[1])
        except (IndexError, ValueError):
            continue
        if v > best_v:
            best_v, best_path = v, f
    return best_v, best_path


def run_reauthoring(model: str, dry_run: bool, reasoning_effort: str, kind: str = "sides"):
    """
    v3 RE-AUTHORING. Send the v3 re-authoring query to a model and save its reply
    as a NEW version of its method doc (never overwrites).

      kind="sides"  : template authoring_query_v3.md
                      revises method_{model}_v{N}.md      -> method_{model}_v{N+1}.md
      kind="totals" : template authoring_query_v3_totals.md
                      revises method_{model}_totals_v{N}.md -> method_{model}_totals_v{N+1}.md

    The model reads the v3 rules-of-the-game (it now owns its edge gate, slate
    ceiling, and 1u/3u threshold) plus the account-history block format it will
    receive each slate, then revises its own method. Web search disabled.
    """
    is_totals     = (kind == "totals")
    template_name = "authoring_query_v3_totals.md" if is_totals else "authoring_query_v3.md"
    template_path = PROJECT_ROOT / "docs" / "methods" / template_name
    if not template_path.exists():
        print(f"ERROR: v3 re-authoring template not found: {template_path}")
        sys.exit(1)

    cur_v, cur_path = _highest_method_version(model, totals=is_totals)
    if cur_path is None:
        which = "totals method" if is_totals else "method"
        print(f"ERROR: no existing {which} doc found for '{model}'.")
        print(f"       Re-authoring revises an existing method; use --authoring for a first method.")
        sys.exit(1)

    if is_totals:
        output_path = PROJECT_ROOT / "docs" / "methods" / f"method_{model}_totals_v{cur_v + 1}.md"
    else:
        output_path = PROJECT_ROOT / "docs" / "methods" / f"method_{model}_v{cur_v + 1}.md"
    target_v = cur_v + 1
    if output_path.exists():
        print(f"ERROR: target method file already exists: {output_path}")
        print(f"       Remove or rename it first. Never silently overwrite a method doc.")
        sys.exit(1)

    current_method = cur_path.read_text(encoding="utf-8").strip()
    template       = template_path.read_text(encoding="utf-8")
    query_text     = template.replace("{CURRENT_METHOD}", current_method).replace("{MODEL}", model)

    # Totals re-authoring sees the model's finalized SIDES method so its slate-ceiling
    # statement stays consistent with the sides ceiling (prevents cross-market conflict).
    if is_totals and "{SIDES_METHOD}" in query_text:
        _, sides_path = _highest_method_version(model, totals=False)
        sides_text = sides_path.read_text(encoding="utf-8").strip() if sides_path else "(no sides method on file)"
        query_text = query_text.replace("{SIDES_METHOD}", sides_text)

    doc_label = "totals (Over/Under) method document" if is_totals else "method document"
    system_text = (
        f"You are an independent professional sports bettor revising your personal "
        f"{doc_label}. Your task is to write the revised {doc_label} described "
        f"in the user message. Do NOT produce picks, game blocks, or any "
        f"## GAME: output. Output ONLY the method document text, nothing else."
    )

    print(f"Mode             : re-authoring (v3, {kind})")
    print(f"Template         : {template_path}  ({len(template):,} chars)")
    print(f"Current method   : {cur_path.name}  (v{cur_v})")
    print(f"Output file      : {output_path.name}  (v{target_v})")
    print(f"Full query size  : {len(query_text):,} chars")
    print(f"Reasoning effort : {reasoning_effort}")
    print(f"Web search       : disabled")

    input_messages = [
        {"role": "system", "content": system_text},
        {"role": "user",   "content": query_text},
    ]

    if dry_run:
        print()
        print("--- DRY RUN: system message ---")
        print(f"  {system_text}")
        print()
        print("--- DRY RUN: user message (first 1200 chars) ---")
        safe    = query_text[:1200].encode("ascii", errors="replace").decode("ascii")
        print("  " + safe.replace("\n", "\n  "))
        print(f"  ... [{len(query_text) - 1200} more chars, ending with the current method doc]")
        print()
        print(f"No API call made. Output would be written to: {output_path}")
        return

    api_key, model_id, display_label = _resolve_model_config(model)
    print(f"Model ID         : {model_id}")
    print(f"Sending ...")

    response_text, input_tokens, output_tokens, reasoning_tokens = _call_api_with_retry(
        model, input_messages, api_key, model_id, reasoning_effort,
        web_search=False, max_tokens=MAX_OUTPUT_TOKENS,
        system_text=system_text, prompt_text=query_text,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(response_text, encoding="utf-8")
    written_bytes = output_path.stat().st_size
    if written_bytes == 0:
        print(f"ERROR: output file is empty after write -- {output_path}")
        sys.exit(1)
    print(f"  File verified: {written_bytes:,} bytes -> {output_path.name}")
    print()
    print("Done.")
    _print_usage(display_label, model_id, reasoning_effort,
                 input_tokens, output_tokens, reasoning_tokens, output_path)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Add scripts/ to path so tz_util imports work when called directly
    sys.path.insert(0, str(SCRIPTS_DIR))

    _check_dependencies()
    _load_dotenv()

    parser = argparse.ArgumentParser(
        description=(
            "Send a daily prompt to a model's API and save the raw response. "
            "Use --postmortem to send a post-mortem review instead."
        )
    )
    parser.add_argument("--model",      required=True,
                        help="Model identifier used in filenames: grok, chatgpt")
    parser.add_argument("--sport",      default="mlb",
                        help="Sport code (default: mlb)")
    parser.add_argument("--date",       default=None,
                        help="Slate date YYYY-MM-DD (default: today in US Eastern Time)")
    parser.add_argument("--postmortem", action="store_true",
                        help="Run post-mortem review instead of picks query")
    parser.add_argument("--authoring",  action="store_true",
                        help="Send one-time method-authoring query; saves reply to docs/methods/method_{model}_v1.md")
    parser.add_argument("--reauthor",   action="store_true",
                        help="v3 re-authoring (sides): model revises its method to add its own staking rules; saves to method_{model}_v{N+1}.md")
    parser.add_argument("--reauthor-totals", action="store_true", dest="reauthor_totals",
                        help="v3 re-authoring (totals): model revises its totals method to own its run-gap gate/units; saves to method_{model}_totals_v{N+1}.md")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Print what would be sent without calling the API")
    parser.add_argument("--reasoning",  default=None,
                        choices=VALID_REASONING_EFFORTS,
                        help=(
                            "Reasoning effort: none, low, medium, high, xhigh. "
                            "xhigh is OpenAI-only (gpt-5.4). "
                            "Default: medium for picks, low for postmortem."
                        ))
    parser.add_argument("--confirm-check", action="store_true", dest="confirm_check",
                        help=(
                            "Run confirm-check mode: re-evaluate picks after lineups confirm. "
                            "Requires --game-ids."
                        ))
    parser.add_argument("--game-ids",  default=None, dest="game_ids",
                        help=(
                            "Comma-separated game_ids for this confirm-check cluster. "
                            "Required with --confirm-check."
                        ))

    args = parser.parse_args()

    date = args.date or _today_et()

    # Resolve reasoning effort: explicit flag wins, otherwise use mode default.
    # DeepSeek/Kimi/Qwen: thinking enabled = always "high".
    # Grok: picks=high, postmortem=medium (per GROK_REASONING_* constants).
    # All others: global REASONING_PICKS / REASONING_POSTMORTEM defaults.
    if args.reasoning:
        reasoning_effort = args.reasoning
    elif args.postmortem:
        if args.model in ("deepseek", "kimi", "qwen"):
            reasoning_effort = "high"
        elif args.model == "grok":
            reasoning_effort = GROK_REASONING_POSTMORTEM
        elif args.model == "gemini":
            reasoning_effort = GEMINI_REASONING_POSTMORTEM
        else:
            reasoning_effort = REASONING_POSTMORTEM
    else:
        if args.model in ("deepseek", "kimi", "qwen"):
            reasoning_effort = "high"
        elif args.model == "grok":
            reasoning_effort = GROK_REASONING_PICKS
        elif args.model == "gemini":
            reasoning_effort = GEMINI_REASONING_PICKS
        else:
            reasoning_effort = REASONING_PICKS

    if args.confirm_check:
        mode_label = "confirm-check"
    elif args.reauthor_totals:
        mode_label = "reauthor-totals"
    elif args.reauthor:
        mode_label = "reauthor"
    elif args.authoring:
        mode_label = "authoring"
    elif args.postmortem:
        mode_label = "postmortem"
    else:
        mode_label = "picks"
    dry_label  = "  [DRY RUN]" if args.dry_run else ""
    print(f"query_model.py  model={args.model}  sport={args.sport}  date={date}  "
          f"mode={mode_label}  reasoning={reasoning_effort}{dry_label}")
    print()

    if args.confirm_check:
        if not args.game_ids:
            print("ERROR: --confirm-check requires --game-ids")
            sys.exit(1)
        game_id_list = [g.strip() for g in args.game_ids.split(",") if g.strip()]
        run_confirm_check(
            model            = args.model,
            sport            = args.sport,
            date             = date,
            game_ids         = game_id_list,
            dry_run          = args.dry_run,
            reasoning_effort = reasoning_effort,
        )
    elif args.reauthor or args.reauthor_totals:
        run_reauthoring(
            model            = args.model,
            dry_run          = args.dry_run,
            reasoning_effort = reasoning_effort,
            kind             = "totals" if args.reauthor_totals else "sides",
        )
    elif args.authoring:
        run_authoring(
            model            = args.model,
            dry_run          = args.dry_run,
            reasoning_effort = reasoning_effort,
        )
    elif args.postmortem:
        run_postmortem(
            model            = args.model,
            sport            = args.sport,
            date             = date,
            dry_run          = args.dry_run,
            reasoning_effort = reasoning_effort,
        )
    else:
        run_picks(
            model            = args.model,
            sport            = args.sport,
            date             = date,
            dry_run          = args.dry_run,
            reasoning_effort = reasoning_effort,
        )

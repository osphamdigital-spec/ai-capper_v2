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
ANTHROPIC_MODELS = ("opus", "sonnet", "fable")

ANTHROPIC_MAX_TOKENS_PICKS      = 16000
ANTHROPIC_MAX_TOKENS_POSTMORTEM = 8000

# Per-model output token budgets for picks mode.
# DeepSeek splits the budget between reasoning tokens and response tokens --
# with only 8000 total, reasoning consumes half and the response is truncated.
# 32000 is the deepseek-v4-pro output ceiling.
DEEPSEEK_MAX_TOKENS_PICKS      = 32000
DEEPSEEK_MAX_TOKENS_POSTMORTEM = 16000

# kimi-k2.6 max output is 32k. Use the ceiling for picks so large slates
# are not truncated mid-response.
KIMI_MAX_TOKENS_PICKS      = 32000
KIMI_MAX_TOKENS_POSTMORTEM = 16000

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
GROK_MAX_TOKENS_PICKS = 16000

# qwen3.7-max: 16000 gives headroom for thinking + response on large slates.
QWEN_MAX_TOKENS_PICKS = 16000

# Output token budget.
# Responses API uses max_output_tokens; Chat Completions uses max_tokens.
MAX_OUTPUT_TOKENS = 8000

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
    Print a clear error message for common API failure modes and exit.
    Called from both _call_grok and _call_chatgpt to avoid duplication.
    """
    from openai import AuthenticationError, RateLimitError, APITimeoutError, APIError
    if isinstance(e, AuthenticationError):
        print(f"ERROR: API authentication failed -- check {key_env_var} in .env")
        print(f"       Detail: {e}")
    elif isinstance(e, RateLimitError):
        print(f"ERROR: Rate limit hit -- wait and retry")
        print(f"       Detail: {e}")
    elif isinstance(e, APITimeoutError):
        print(f"ERROR: Request timed out -- check your connection and retry")
        print(f"       Detail: {e}")
    elif isinstance(e, APIError):
        print(f"ERROR: API error -- {e}")
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
    frequency_penalty -- only model, messages, extra_body, and max_tokens
    are passed. No web search tool, no reasoning_effort level param.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=KIMI_BASE_URL)

    extra_body, _ = _kimi_thinking_params(reasoning_effort)

    try:
        response = client.chat.completions.create(
            model      = model_id,
            messages   = input_messages,
            max_tokens = max_tokens,
            extra_body = extra_body,
        )
    except Exception as e:
        _handle_api_errors(e, "MOONSHOT_API_KEY")

    msg    = response.choices[0].message
    text   = msg.content or ""

    # kimi-k2.6 separates thinking from response: reasoning_content = thinking
    # trace, content = final answer. Always prefer content. Only fall back to
    # reasoning_content if content is genuinely absent (API edge case).
    reasoning_content = getattr(msg, "reasoning_content", "") or ""
    if not text and reasoning_content:
        # content is empty -- this is an API anomaly. Log and use reasoning_content
        # as a last resort so we get something rather than nothing.
        print("  WARNING: Kimi content field empty -- falling back to reasoning_content")
        print("           This is an API anomaly; response may be thinking trace only.")
        text = reasoning_content
    elif reasoning_content and not text.strip():
        text = reasoning_content

    # Strip thinking trace from picks output: picks always start with a GAME block.
    # Post-mortem output starts with section headers (## S1:) -- no stripping needed.
    import re as _re
    lines = text.splitlines()
    first_game = next(
        (i for i, ln in enumerate(lines)
         if _re.match(r"^## GAME:|^GAME ", ln.strip())),
        None,
    )
    if first_game and first_game > 0:
        stripped_chars = sum(len(l) + 1 for l in lines[:first_game])
        print(f"  INFO: Stripped {stripped_chars} chars of thinking trace before first GAME block")
        text = "\n".join(lines[first_game:])

    if not text:
        finish = getattr(response.choices[0], "finish_reason", "unknown")
        print(f"  WARNING: Kimi returned empty content (finish_reason={finish})")
        print(f"  Response message fields: {[f for f in dir(msg) if not f.startswith('_')]}")

    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    details = getattr(response.usage, "completion_tokens_details", None)
    reasoning_tokens = getattr(details, "reasoning_tokens", None) if details else None
    if reasoning_tokens == 0:
        reasoning_tokens = None

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
) -> tuple[str, int, int, int | None]:
    """
    Send messages to the Anthropic API using the native SDK with prompt caching.
    The system prompt is marked ephemeral so the API caches it across calls --
    reducing cost and latency for repeat queries on the same slate.

    Returns (response_text, input_tokens, output_tokens, None).
    Reasoning tokens are not exposed separately by the Anthropic API.
    """
    import anthropic as ant

    client = ant.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
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
    except ant.AuthenticationError as e:
        print(f"ERROR: Anthropic API authentication failed -- check CLAUDE_API_KEY in .env")
        print(f"       Detail: {e}")
        sys.exit(1)
    except ant.RateLimitError as e:
        print(f"ERROR: Rate limit hit -- wait and retry")
        print(f"       Detail: {e}")
        sys.exit(1)
    except Exception as e:
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
        elif model == "sonnet":
            model_id = os.environ.get("SONNET_MODEL", DEFAULT_SONNET_MODEL)
            label    = f"Claude Sonnet ({model_id})"
        else:  # fable
            model_id = os.environ.get("FABLE_MODEL", DEFAULT_FABLE_MODEL)
            label    = f"Claude Fable ({model_id})"
        if not api_key:
            print("ERROR: CLAUDE_API_KEY is not set.")
            print("       Add it to .env: CLAUDE_API_KEY=your_key_here")
            sys.exit(1)
    else:
        print(f"ERROR: Unknown model '{model}'. Supported: grok, chatgpt, deepseek, kimi, qwen, gemini, opus, sonnet, fable")
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
) -> tuple[str, int, int, int | None]:
    """Dispatch to the correct API caller for the given model name."""
    if model in ANTHROPIC_MODELS:
        # Native Anthropic SDK with prompt caching; ignores input_messages format
        return _call_anthropic(system_text, prompt_text, api_key, model_id, max_tokens)
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
    if model in ANTHROPIC_MODELS:
        picks_max_tokens = ANTHROPIC_MAX_TOKENS_PICKS
    elif model == "deepseek":
        picks_max_tokens = DEEPSEEK_MAX_TOKENS_PICKS
    elif model == "kimi":
        picks_max_tokens = KIMI_MAX_TOKENS_PICKS
    elif model == "gemini":
        picks_max_tokens = GEMINI_MAX_TOKENS_PICKS
    elif model == "chatgpt":
        picks_max_tokens = CHATGPT_MAX_TOKENS_PICKS
    elif model == "grok":
        picks_max_tokens = GROK_MAX_TOKENS_PICKS
    elif model == "qwen":
        picks_max_tokens = QWEN_MAX_TOKENS_PICKS
    else:
        picks_max_tokens = MAX_OUTPUT_TOKENS
    response_text, input_tokens, output_tokens, reasoning_tokens = _call_api(
        model, input_messages, api_key, model_id, reasoning_effort,
        web_search=True, max_tokens=picks_max_tokens,
        system_text=system_text, prompt_text=prompt_text,
    )

    # --- Token cap warning -----------------------------------------------
    if output_tokens >= picks_max_tokens - 500:
        print(f"WARNING: {model} output tokens ({output_tokens:,}) near max_tokens cap "
              f"({picks_max_tokens:,}).")
        print(f"         Response may be truncated. Consider increasing max_tokens.")

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

def _build_confirmed_section(model: str, sport: str, date: str) -> str | None:
    """
    Build the CONFIRMED DATA EVALUATION block for the post-mortem prompt.

    Only includes games where this model BET or LEANED (not passes).
    Reads:
      - picks/{sport}/{date}/{model}.json          (to find bet/lean games)
      - data/{sport}/{date}/confirmed_data.json    (lineup + umpire data)

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

    ANTI_HINDSIGHT = (
        "## CONFIRMED DATA EVALUATION (lineup + umpire) — was NOT available pre-game\n"
        "Using ONLY the pre-game STATS of these players/umpire — NOT the game result — "
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
        block_lines.extend([
            "CONFIRMED LINEUP vs YOUR ASSUMPTION: [materially different / roughly as expected]",
            "WOULD CHANGE? [no change / lean→bet / bet→pass / bet→other side / bet→higher stake / bet→lower stake]",
            "PRE-GAME REASON (required if WOULD CHANGE ≠ no change):",
            "UMPIRE WOULD CHANGE? [yes/no] — pre-game reason:",
        ])

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
            result_str = f" → {result.upper()}" if result else " → (ungraded)"
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
    else:
        pm_max_tokens = MAX_OUTPUT_TOKENS
    # For Anthropic models the system/prompt split is reconstructed from input_messages
    pm_system = input_messages[0]["content"] if input_messages else ""
    pm_user   = "\n\n".join(m["content"] for m in input_messages[1:])
    response_text, input_tokens, output_tokens, reasoning_tokens = _call_api(
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

    response_text, input_tokens, output_tokens, reasoning_tokens = _call_api(
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
    parser.add_argument("--dry-run",    action="store_true",
                        help="Print what would be sent without calling the API")
    parser.add_argument("--reasoning",  default=None,
                        choices=VALID_REASONING_EFFORTS,
                        help=(
                            "Reasoning effort: none, low, medium, high, xhigh. "
                            "xhigh is OpenAI-only (gpt-5.4). "
                            "Default: medium for picks, low for postmortem."
                        ))

    args = parser.parse_args()

    date = args.date or _today_et()

    # Resolve reasoning effort: explicit flag wins, otherwise use mode default.
    # DeepSeek keeps thinking enabled for post-mortem too (cheap, worth having),
    # so its postmortem default is "high" rather than the global "low".
    if args.reasoning:
        reasoning_effort = args.reasoning
    elif args.postmortem:
        reasoning_effort = "high" if args.model in ("deepseek", "kimi", "qwen") else REASONING_POSTMORTEM
    else:
        reasoning_effort = "high" if args.model in ("deepseek", "kimi", "qwen") else REASONING_PICKS

    if args.authoring:
        mode_label = "authoring"
    elif args.postmortem:
        mode_label = "postmortem"
    else:
        mode_label = "picks"
    dry_label  = "  [DRY RUN]" if args.dry_run else ""
    print(f"query_model.py  model={args.model}  sport={args.sport}  date={date}  "
          f"mode={mode_label}  reasoning={reasoning_effort}{dry_label}")
    print()

    if args.authoring:
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

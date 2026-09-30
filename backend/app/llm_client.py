"""
Thin, provider-abstracted client for the chat assistant's LLM calls.
Every provider detail (which one, which model, the key, sampling
params) comes from chat.* settings — see settings_registry.py — so
switching providers or models is an admin edit, not a deploy.

Deliberately not using any vendor's SDK: all three APIs are a single
JSON POST, and a plain httpx call keeps this file's only dependency on
the wire format, not on SDK version churn.

Tool use: callers may pass `tools` (a provider-agnostic list of
{name, description, parameters} dicts — see chat_tools.py) and a
`tool_executor` callback. Each provider function runs its own
request/tool-call/tool-result loop, translating the provider-agnostic
tool schema and any tool_use/tool_call blocks into that provider's
wire format, until the model returns a plain text reply or
MAX_TOOL_ITERATIONS is hit (treated as a failure — a model that won't
stop calling tools shouldn't hang a visitor's chat indefinitely).
"""
from __future__ import annotations

import json
from typing import Any, Callable

import httpx

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

REQUEST_TIMEOUT_SECONDS = 20.0

# A normal reply resolves in one round trip; a booking flow might take
# a couple (list_services -> check_availability -> book_appointment).
# Past this, something's wrong (the model is stuck looping) and we'd
# rather fail into the fallback message than hang the request.
MAX_TOOL_ITERATIONS = 6

ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


class LLMError(Exception):
    """Raised for any failure talking to the provider — network,
    auth, rate limit, malformed response, or a tool-use loop that
    never converges. Callers (chat_service.py) catch this uniformly
    and fall back to chat.unavailable_message rather than ever
    surfacing a raw provider error to a visitor."""


def _history_to_messages(history: list[dict]) -> list[dict]:
    """Frontend history entries are {from: 'user'|'ai', text} (tests
    also pass 'assistant'). Anything not literally 'user' is the
    assistant's own prior turn — treating 'ai' as unrecognized used to
    silently relabel every past assistant reply as a 'user' message,
    corrupting multi-turn context sent to the LLM."""
    return [{"role": ("user" if h.get("from") == "user" else "assistant"), "content": h.get("text", "")}
            for h in history]


def _run_tool(tool_executor: ToolExecutor, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Never lets a tool's own exception escape into the provider loop
    — an unexpected error becomes a normal (failed) tool result the
    model can react to, same as any other {"ok": False, ...}."""
    try:
        return tool_executor(name, args)
    except Exception as e:  # noqa: BLE001 - deliberately broad: any tool failure must stay in-loop
        return {"ok": False, "error": f"tool_failed: {e}"}


def _call_anthropic(*, api_key: str, model: str, system_prompt: str, history: list[dict], message: str,
                     max_tokens: int, temperature: float, tools: list[dict] | None = None,
                     tool_executor: ToolExecutor | None = None) -> str:
    messages = _history_to_messages(history) + [{"role": "user", "content": message}]
    anthropic_tools = [
        {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
        for t in (tools or [])
    ]

    for _ in range(MAX_TOOL_ITERATIONS):
        payload: dict[str, Any] = {
            "model": model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if anthropic_tools:
            payload["tools"] = anthropic_tools
        try:
            resp = httpx.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Anthropic API returned {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise LLMError(f"Anthropic API request failed: {e}") from e

        content = data.get("content", [])
        tool_uses = [b for b in content if b.get("type") == "tool_use"]

        if not tool_uses or tool_executor is None:
            text = "".join(b["text"] for b in content if b.get("type") == "text").strip()
            if not text:
                raise LLMError("Anthropic response contained no text content")
            return text

        messages.append({"role": "assistant", "content": content})
        tool_results = []
        for tu in tool_uses:
            result = _run_tool(tool_executor, tu.get("name", ""), tu.get("input") or {})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.get("id", ""),
                "content": json.dumps(result),
            })
        messages.append({"role": "user", "content": tool_results})

    raise LLMError("Anthropic tool-use loop did not converge")


def _call_openai_compatible(url: str, provider_label: str, *, api_key: str, model: str, system_prompt: str,
                             history: list[dict], message: str, max_tokens: int, temperature: float,
                             tools: list[dict] | None = None, tool_executor: ToolExecutor | None = None) -> str:
    """Shared implementation for OpenAI and DeepSeek: both speak the
    same chat-completions request/response shape (including the same
    `tools`/`tool_calls` function-calling format), differing only in
    base URL. Kept as one function with a label for error messages,
    rather than duplicated per provider, since this loop is the part
    most worth not drifting between the two."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt}, *_history_to_messages(history),
        {"role": "user", "content": message},
    ]
    openai_tools = [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in (tools or [])
    ]

    for _ in range(MAX_TOOL_ITERATIONS):
        payload: dict[str, Any] = {
            "model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
        }
        if openai_tools:
            payload["tools"] = openai_tools
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected {provider_label} response shape: {e}") from e
        except httpx.HTTPStatusError as e:
            raise LLMError(f"{provider_label} API returned {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise LLMError(f"{provider_label} API request failed: {e}") from e

        tool_calls = msg.get("tool_calls")
        if not tool_calls or tool_executor is None:
            text = (msg.get("content") or "").strip()
            if not text:
                raise LLMError(f"{provider_label} response contained no text content")
            return text

        messages.append(msg)
        for tc in tool_calls:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = _run_tool(tool_executor, fn.get("name", ""), args)
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": json.dumps(result)})

    raise LLMError(f"{provider_label} tool-use loop did not converge")


def _call_openai(*, api_key: str, model: str, system_prompt: str, history: list[dict], message: str,
                  max_tokens: int, temperature: float, tools: list[dict] | None = None,
                  tool_executor: ToolExecutor | None = None) -> str:
    return _call_openai_compatible(
        OPENAI_URL, "OpenAI", api_key=api_key, model=model, system_prompt=system_prompt, history=history,
        message=message, max_tokens=max_tokens, temperature=temperature, tools=tools, tool_executor=tool_executor,
    )


def _call_deepseek(*, api_key: str, model: str, system_prompt: str, history: list[dict], message: str,
                    max_tokens: int, temperature: float, tools: list[dict] | None = None,
                    tool_executor: ToolExecutor | None = None) -> str:
    # DeepSeek's API is OpenAI-compatible — same chat-completions and
    # function-calling wire format, just its own base URL and key.
    return _call_openai_compatible(
        DEEPSEEK_URL, "DeepSeek", api_key=api_key, model=model, system_prompt=system_prompt, history=history,
        message=message, max_tokens=max_tokens, temperature=temperature, tools=tools, tool_executor=tool_executor,
    )


_PROVIDERS = {"anthropic": _call_anthropic, "openai": _call_openai, "deepseek": _call_deepseek}


def generate_reply(*, provider: str, api_key: str, model: str, system_prompt: str, history: list[dict],
                    message: str, max_tokens: int, temperature: float, tools: list[dict] | None = None,
                    tool_executor: ToolExecutor | None = None) -> str:
    if provider not in _PROVIDERS:
        raise LLMError(f"Unsupported or unconfigured provider: {provider!r}")
    if not api_key:
        raise LLMError("No API key configured")
    return _PROVIDERS[provider](
        api_key=api_key, model=model, system_prompt=system_prompt, history=history,
        message=message, max_tokens=max_tokens, temperature=temperature,
        tools=tools, tool_executor=tool_executor,
    )

import os
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class LLMConfigurationError(RuntimeError):
    pass


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value if value and value.strip() else None


def get_configured_llm_provider() -> Tuple[str, str]:
    """Return (provider, api_key).

    If LLM_PROVIDER is set, it must be one of: openrouter, openai, anthropic.
    Otherwise, uses priority: openrouter -> openai -> anthropic.
    """
    forced = (_env("LLM_PROVIDER") or "").strip().lower() or None
    if forced:
        if forced == "openrouter":
            key = _env("OPENROUTER_API_KEY")
            if not key:
                raise LLMConfigurationError("LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is missing")
            return "openrouter", key
        if forced == "openai":
            key = _env("OPENAI_API_KEY")
            if not key:
                raise LLMConfigurationError("LLM_PROVIDER=openai but OPENAI_API_KEY is missing")
            return "openai", key
        if forced == "anthropic":
            key = _env("ANTHROPIC_API_KEY")
            if not key:
                raise LLMConfigurationError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is missing")
            return "anthropic", key
        raise LLMConfigurationError("LLM_PROVIDER must be one of: openrouter, openai, anthropic")

    openrouter_key = _env("OPENROUTER_API_KEY")
    if openrouter_key:
        return "openrouter", openrouter_key

    openai_key = _env("OPENAI_API_KEY")
    if openai_key:
        return "openai", openai_key

    anthropic_key = _env("ANTHROPIC_API_KEY")
    if anthropic_key:
        return "anthropic", anthropic_key

    raise LLMConfigurationError(
        "No LLM provider configured. Set OPENROUTER_API_KEY (recommended) or OPENAI_API_KEY or ANTHROPIC_API_KEY."
    )


async def chat_completion(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 700,
    timeout_s: float = 30.0,
) -> str:
    provider, api_key = get_configured_llm_provider()

    # Optional override: LLM_MODEL (OpenRouter expects vendor/model, OpenAI expects model, Anthropic expects model)
    model = model or _env("LLM_MODEL")

    if provider in ("openrouter", "openai"):
        url = (
            "https://openrouter.ai/api/v1/chat/completions"
            if provider == "openrouter"
            else "https://api.openai.com/v1/chat/completions"
        )
        chosen_model = model or (
            "openai/gpt-4o-mini" if provider == "openrouter" else "gpt-4o-mini"
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            # Helpful but optional; safe defaults
            headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "https://maestra.8825.systems")
            headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "Maestra")

        payload: Dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"LLM request failed ({provider}): {resp.status_code} {resp.text}")
            data = resp.json()

        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Unexpected LLM response format ({provider}): {e}")

    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        chosen_model = model or "claude-3-5-sonnet-20241022"

        headers = {
            "x-api-key": api_key,
            "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
            "content-type": "application/json",
        }

        # Anthropic uses a top-level system + user/assistant messages.
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        system = "\n\n".join(system_parts) if system_parts else None
        anthropic_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]

        payload = {
            "model": chosen_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(f"LLM request failed (anthropic): {resp.status_code} {resp.text}")
            data = resp.json()

        try:
            # content is a list of blocks
            blocks = data.get("content", [])
            text_blocks = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            return "\n".join([t for t in text_blocks if t]).strip()
        except Exception as e:
            raise RuntimeError(f"Unexpected LLM response format (anthropic): {e}")

    raise RuntimeError(f"Unsupported provider: {provider}")

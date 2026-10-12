"""LLM provider, isolated so the backing model/API can be swapped.

Uses Google AI Studio's Generative Language API (the `google-genai` SDK)
pointed at a Gemma model (e.g. `gemma-4-26b-a4b-it`), per the project's
configured provider. The API key is optional application-wide: if it is
missing or the call fails, callers must preserve authorization/audit results
and surface a clear error rather than failing closed on security logic or
fabricating an answer.

Supports Gemma 4's `thinking_level` control ("minimal" vs "high") so callers
can trade latency for deeper multi-step reasoning on harder questions.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from config import Settings

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.5

ThinkingLevel = Literal["minimal", "high"]


class LLMProviderError(RuntimeError):
    pass


class LLMNotConfiguredError(LLMProviderError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    thinking_level: ThinkingLevel


def generate(
    settings: Settings,
    system_instruction: str,
    user_prompt: str,
    thinking_level: ThinkingLevel = "minimal",
) -> LLMResponse:
    if not settings.llm_configured:
        raise LLMNotConfiguredError(
            "No GOOGLE_API_KEY configured. Set it in .env to enable live answer "
            "generation via the Gemma API."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise LLMProviderError(
            "google-genai package is not installed. Run `pip install google-genai`."
        ) from exc

    client = genai.Client(api_key=settings.google_api_key)
    last_error: Exception | None = None

    # The Gemma-on-Gemini-API endpoint occasionally returns a transient 5xx.
    # Retry a couple of times with a short backoff before surfacing an error
    # to the caller, which must then fall back without bypassing ACL checks.
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=settings.gemma_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
                ),
            )
            text = (response.text or "").strip()
            if not text:
                raise LLMProviderError("The Gemma API returned an empty response.")
            return LLMResponse(text=text, model=settings.gemma_model, thinking_level=thinking_level)
        except LLMProviderError as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc
            is_retryable = "INTERNAL" in str(exc) or "503" in str(exc) or "UNAVAILABLE" in str(exc)
            if not is_retryable or attempt == _MAX_ATTEMPTS:
                break
            time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
            continue
        break

    raise LLMProviderError(f"Gemma API call failed: {last_error}") from last_error

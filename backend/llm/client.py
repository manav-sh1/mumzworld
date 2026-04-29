"""OpenRouter LLM client — API calls with retry, timeout, and observability."""
from __future__ import annotations

import json
import time

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import settings
from backend.core.exceptions import LLMError, SchemaValidationError
from backend.core.logging import get_logger
from backend.gift_finder.schemas import GiftResponse
from backend.llm.prompts import SYSTEM_PROMPT, build_user_prompt

log = get_logger(__name__)

_client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
    timeout=60.0,
)


def get_recommendations(
    catalog_json: str,
    raw_query: str,
    age_months: int | None,
    budget_aed: float | None,
    occasion: str | None,
    language: str,
    interests: str | None,
) -> GiftResponse:
    """Call OpenRouter and return a validated GiftResponse."""
    user_msg = build_user_prompt(
        catalog_json=catalog_json,
        raw_query=raw_query,
        age_months=age_months,
        budget_aed=budget_aed,
        occasion=occasion,
        language=language,
        interests=interests,
    )
    raw = _call_llm(user_msg)
    return _parse_response(raw)


@retry(
    retry=retry_if_exception_type(openai.RateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _call_llm(user_message: str) -> str:
    """Send messages to OpenRouter with retry and observability.

    Only RateLimitError triggers retry — auth errors and other API
    failures fail fast to avoid wasting time on unrecoverable issues.
    """
    start = time.perf_counter()
    try:
        response = _client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=settings.temperature,
            max_tokens=2048,
        )
    except openai.AuthenticationError as exc:
        raise LLMError("Invalid OpenRouter API key.") from exc
    except openai.RateLimitError:
        log.warning("llm.rate_limited", model=settings.model_name)
        raise  # let tenacity retry this one
    except openai.APIConnectionError as exc:
        raise LLMError("Cannot reach OpenRouter API.") from exc
    except openai.APIError as exc:
        raise LLMError(f"OpenRouter API error: {exc}") from exc

    elapsed_ms = round((time.perf_counter() - start) * 1000)
    content = _extract_content(response)
    usage = response.usage
    log.info(
        "llm.response",
        model=settings.model_name,
        latency_ms=elapsed_ms,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        chars=len(content),
    )
    return content


def _extract_content(response: openai.types.ChatCompletion) -> str:
    """Safely extract text content from the LLM response."""
    if not response.choices:
        raise LLMError("LLM returned empty choices array.")
    message = response.choices[0].message
    if not message or not message.content:
        raise LLMError("LLM returned empty message content.")
    return message.content


def _parse_response(raw: str) -> GiftResponse:
    """Parse and validate the raw JSON string into a GiftResponse."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError("LLM output is not valid JSON.", raw) from exc

    try:
        return GiftResponse.model_validate(data)
    except (ValueError, TypeError) as exc:
        raise SchemaValidationError(str(exc), raw) from exc

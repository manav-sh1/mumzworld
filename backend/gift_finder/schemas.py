"""Pydantic models for API request / response and LLM structured output."""
from __future__ import annotations

from pydantic import BaseModel, Field


# ── LLM Output Schema ──────────────────────────────────────────────


class ProductRecommendation(BaseModel):
    """A single gift recommendation from the catalog."""

    name: str
    price_aed: float | None = None
    category: str
    reason_en: str
    reason_ar: str
    confidence: str = Field(pattern=r"^(high|medium|low)$")
    tags: list[str] = Field(default_factory=list)


class GiftResponse(BaseModel):
    """Full LLM response — validated before reaching the frontend."""

    recommendations: list[ProductRecommendation] = Field(
        default_factory=list, max_length=5,
    )
    query_understood: bool = True
    clarification_needed: str | None = None
    out_of_scope: bool = False
    refusal_reason: str | None = None


# ── API Request Schema ──────────────────────────────────────────────


class GiftRequest(BaseModel):
    """Incoming user query from the frontend."""

    query: str = Field(..., min_length=1, max_length=1000)


# ── Parsed Parameters ───────────────────────────────────────────────


class ParsedParams(BaseModel):
    """Extracted parameters from the raw user query."""

    age_months: int | None = None
    budget_aed: float | None = None
    occasion: str | None = None
    interests: str | None = None
    language: str = "en"

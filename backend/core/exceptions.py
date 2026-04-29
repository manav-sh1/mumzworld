"""Typed exception hierarchy for the gift finder."""
from __future__ import annotations


class GiftFinderError(Exception):
    """Root exception — catch at the API boundary."""


class LLMError(GiftFinderError):
    """Unrecoverable LLM API failure."""


class SchemaValidationError(GiftFinderError):
    """LLM output did not match the expected schema."""

    def __init__(self, detail: str, raw_output: str) -> None:
        super().__init__(f"Schema validation failed: {detail}")
        self.detail = detail
        self.raw_output = raw_output


class CatalogError(GiftFinderError):
    """Problem loading or querying the product catalog."""

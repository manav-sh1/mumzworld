"""Load and query the mock product catalog."""
from __future__ import annotations

import json
from pathlib import Path

from backend.core.exceptions import CatalogError
from backend.core.logging import get_logger

log = get_logger(__name__)

_CATALOG_PATH = Path(__file__).parent / "catalog.json"


def load_catalog() -> list[dict]:
    """Read catalog.json once and return the product list.

    Raises CatalogError with a clear message if the file is missing or
    contains invalid JSON, instead of crashing with a bare traceback.
    """
    if not _CATALOG_PATH.exists():
        raise CatalogError(
            f"Catalog file not found at {_CATALOG_PATH}. "
            "Ensure catalog.json is in backend/gift_finder/."
        )
    try:
        with _CATALOG_PATH.open(encoding="utf-8") as fh:
            products: list[dict] = json.load(fh)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"catalog.json contains invalid JSON: {exc}") from exc

    if not products:
        raise CatalogError("catalog.json is empty — no products to recommend.")

    log.info("catalog.loaded", count=len(products))
    return products


def catalog_as_json_str(products: list[dict]) -> str:
    """Serialize catalog for injection into the LLM prompt."""
    return json.dumps(products, ensure_ascii=False, indent=2)

"""Gift finder service — orchestrates parsing, catalog, LLM calls, and grounding."""
from __future__ import annotations

from backend.core.logging import get_logger
from backend.gift_finder.catalog import catalog_as_json_str, load_catalog
from backend.gift_finder.parser import parse_query
from backend.gift_finder.schemas import GiftRequest, GiftResponse
from backend.llm.client import get_recommendations

log = get_logger(__name__)

# Load catalog once at import time
_CATALOG = load_catalog()
_CATALOG_JSON = catalog_as_json_str(_CATALOG)
_CATALOG_NAMES = {p["name"] for p in _CATALOG}


def find_gifts(request: GiftRequest) -> GiftResponse:
    """End-to-end pipeline: parse → prompt → LLM → validate → ground."""
    params = parse_query(request.query)
    log.info(
        "query.parsed",
        language=params.language,
        age=params.age_months,
        budget=params.budget_aed,
        occasion=params.occasion,
    )
    response = get_recommendations(
        catalog_json=_CATALOG_JSON,
        raw_query=request.query,
        age_months=params.age_months,
        budget_aed=params.budget_aed,
        occasion=params.occasion,
        language=params.language,
        interests=params.interests,
    )
    response = _validate_grounding(response)
    log.info(
        "recommendations.returned",
        count=len(response.recommendations),
        out_of_scope=response.out_of_scope,
    )
    return response


def _validate_grounding(response: GiftResponse) -> GiftResponse:
    """Remove any recommendations with names not found in the catalog."""
    valid = [r for r in response.recommendations if r.name in _CATALOG_NAMES]
    if len(valid) < len(response.recommendations):
        log.warning(
            "grounding.filtered",
            original=len(response.recommendations),
            valid=len(valid),
        )
    return response.model_copy(update={"recommendations": valid})

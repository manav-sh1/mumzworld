"""FastAPI routes for the gift finder API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.exceptions import GiftFinderError, SchemaValidationError
from backend.core.logging import get_logger
from backend.gift_finder.schemas import GiftRequest, GiftResponse
from backend.gift_finder.service import find_gifts

log = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["gifts"])


@router.post("/recommend", response_model=GiftResponse)
def recommend_gifts(request: GiftRequest) -> GiftResponse:
    """Accept a natural-language gift query, return structured recommendations."""
    try:
        return find_gifts(request)
    except SchemaValidationError as exc:
        log.error("schema.validation_failed", detail=exc.detail)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "LLM output failed schema validation",
                "detail": exc.detail,
                "raw_output": exc.raw_output[:500],
            },
        ) from exc
    except GiftFinderError as exc:
        log.error("gift_finder.error", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        log.error("unexpected.error", error=str(exc), exc_type=type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again.",
        ) from exc

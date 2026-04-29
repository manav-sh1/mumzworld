"""Structured logging via structlog — configure once at startup."""
from __future__ import annotations

import logging

import structlog

from backend.core.config import settings


def configure_logging() -> None:
    """Call once in main.py lifespan."""
    logging.basicConfig(level=getattr(logging, settings.log_level))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level),
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a module-scoped structured logger."""
    return structlog.get_logger(name)

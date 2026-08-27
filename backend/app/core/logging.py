"""Structured logging with pipeline stage events.

Sensitive values (full names, document numbers, addresses) must never be
logged at INFO. Log stage outcomes and identifiers only.
"""
import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_stage(logger: logging.Logger, event: str, **context) -> None:
    """Emit a structured pipeline stage event.

    Example: log_stage(log, "OCR_COMPLETED", case_id=case_id, doc_id=doc_id)
    """
    parts = [event]
    for key, value in context.items():
        parts.append(f"{key}={value}")
    logger.info(" | ".join(parts))

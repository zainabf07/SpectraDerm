"""Small, explicit logging setup for command-line and future service entry points."""

from __future__ import annotations

import logging

from spectraderm.config import get_settings


def configure_logging() -> None:
    """Configure the package logger once using the configured log level."""
    settings = get_settings()
    logger = logging.getLogger("spectraderm")
    if logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(settings.log_level)
    logger.propagate = False

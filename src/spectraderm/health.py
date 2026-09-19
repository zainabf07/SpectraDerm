"""Minimal package health checks."""

from __future__ import annotations

from spectraderm.config import get_settings


def package_health() -> dict[str, str]:
    """Return basic package metadata without initializing any pipeline component."""
    settings = get_settings()
    return {"status": "ok", "project_root": str(settings.project_root)}

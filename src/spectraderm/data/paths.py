"""Configurable resolution of manifest entries to local dataset roots."""

from __future__ import annotations

from pathlib import Path

from spectraderm.config import Settings, get_settings


def resolve_hyperskin_path(manifest_path: str, settings: Settings | None = None) -> Path:
    """Resolve an archive-relative Hyper-Skin manifest path without hard-coding a drive."""
    active_settings = settings or get_settings()
    path = Path(manifest_path)
    return path if path.is_absolute() else active_settings.hyperskin_root / path


def resolve_uminho_path(filename: str, settings: Settings | None = None) -> Path:
    """Resolve a UMINHO-HSFD filename relative to its configured raw-data directory."""
    active_settings = settings or get_settings()
    path = Path(filename)
    return path if path.is_absolute() else active_settings.uminho_hsfd_root / path

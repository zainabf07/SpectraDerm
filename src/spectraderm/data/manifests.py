"""Manifest loading and validation for Phase 1 datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

HYPERSKIN_COLUMNS = ("sample_id", "subject_id", "split", "rgb_path", "vis_path")
UMINHO_COLUMNS = ("face_id", "rgb_filename", "reflectance_filename", "split")
VALID_SPLITS = frozenset({"train", "valid", "test"})


def load_manifest(path: Path) -> pd.DataFrame:
    """Load a CSV manifest and reject empty or malformed files."""
    manifest = pd.read_csv(path)
    if manifest.empty:
        raise ValueError(f"Manifest is empty: {path}")
    return manifest


def _validate_columns(manifest: pd.DataFrame, expected: tuple[str, ...], name: str) -> None:
    missing = set(expected).difference(manifest.columns)
    if missing:
        raise ValueError(f"{name} manifest is missing columns: {sorted(missing)}")
    if manifest.loc[:, list(expected)].isna().any().any():
        raise ValueError(f"{name} manifest contains missing required values")


def validate_hyperskin_manifest(manifest: pd.DataFrame) -> None:
    """Validate pairing and subject-aware split fields in Hyper-Skin metadata."""
    _validate_columns(manifest, HYPERSKIN_COLUMNS, "Hyper-Skin")
    if manifest["sample_id"].duplicated().any():
        raise ValueError("Hyper-Skin manifest contains duplicate sample IDs")
    _validate_split_integrity(manifest, "subject_id")


def validate_uminho_manifest(manifest: pd.DataFrame) -> None:
    """Validate pairing and subject-aware split fields in UMINHO-HSFD metadata."""
    _validate_columns(manifest, UMINHO_COLUMNS, "UMINHO-HSFD")
    if manifest["face_id"].duplicated().any():
        raise ValueError("UMINHO-HSFD manifest contains duplicate face IDs")
    _validate_split_integrity(manifest, "face_id")


def _validate_split_integrity(manifest: pd.DataFrame, subject_column: str) -> None:
    splits = set(manifest["split"])
    if not splits.issubset(VALID_SPLITS):
        raise ValueError(f"Unexpected split values: {sorted(splits.difference(VALID_SPLITS))}")
    if manifest.groupby(subject_column)["split"].nunique().gt(1).any():
        raise ValueError("A subject appears in more than one split")

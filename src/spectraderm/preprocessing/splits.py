"""Subject-aware split helpers for small Phase 1 datasets."""

from __future__ import annotations

import numpy as np
import pandas as pd


def create_uminho_split(manifest: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Assign the validated 20/4/5 UMINHO split by face ID using NumPy's seeded generator."""
    if manifest["face_id"].duplicated().any():
        raise ValueError("UMINHO-HSFD face IDs must be unique before splitting")
    split_manifest = manifest.copy()
    face_ids = split_manifest["face_id"].to_numpy(copy=True)
    if len(face_ids) != 29:
        raise ValueError(f"Expected 29 UMINHO faces, got {len(face_ids)}")
    np.random.default_rng(seed).shuffle(face_ids)
    train_ids, valid_ids, test_ids = face_ids[:20], face_ids[20:24], face_ids[24:]
    split_manifest["split"] = np.select(
        [split_manifest["face_id"].isin(train_ids), split_manifest["face_id"].isin(valid_ids)],
        ["train", "valid"],
        default="test",
    )
    return split_manifest

"""Dataset-specific Phase 1 preprocessing entry points."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from spectraderm.data.loaders import load_hyperskin_vis, load_rgb, load_uminho_reflectance
from spectraderm.preprocessing.normalization import normalize_rgb, preserve_spectral_scale
from spectraderm.preprocessing.quality import validate_pair
from spectraderm.preprocessing.transforms import augment_hyperskin_pair, resize_pair_opencv, resize_pair_pillow


def preprocess_hyperskin_pair(
    rgb_path: Path, vis_path: Path, *, augment: bool = False, rng: np.random.Generator | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Produce a 256 x 256 RGB/VIS pair while preserving VIS scale and 31 band order."""
    rgb = normalize_rgb(load_rgb(rgb_path))
    vis = preserve_spectral_scale(load_hyperskin_vis(vis_path))
    rgb, vis = resize_pair_opencv(rgb, vis)
    validate_pair(rgb, vis, expected_bands=31)
    if augment:
        if rng is None:
            raise ValueError("A NumPy random generator is required when augmentation is enabled")
        rgb, vis = augment_hyperskin_pair(rgb, vis, rng)
    return rgb, vis


def preprocess_uminho_pair(rgb_path: Path, reflectance_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Produce a 256 x 256 UMINHO pair without clipping reflectance or background zeros."""
    rgb = normalize_rgb(load_rgb(rgb_path))
    reflectance = preserve_spectral_scale(load_uminho_reflectance(reflectance_path))
    rgb, reflectance = resize_pair_pillow(rgb, reflectance)
    validate_pair(rgb, reflectance, expected_bands=33)
    return rgb, reflectance

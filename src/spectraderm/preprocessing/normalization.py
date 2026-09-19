"""Explicit normalization functions for RGB and measured spectral arrays."""

from __future__ import annotations

import numpy as np


def normalize_rgb(rgb: np.ndarray) -> np.ndarray:
    """Convert uint8 RGB values to float32 in the inclusive [0, 1] range."""
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError(f"Expected H x W x 3 RGB input, got {rgb.shape}")
    return rgb.astype(np.float32) / 255.0


def preserve_spectral_scale(spectral: np.ndarray) -> np.ndarray:
    """Convert measured spectral values to float32 without clipping or rescaling."""
    return spectral.astype(np.float32, copy=False)

"""Non-destructive numerical and spatial contract validation."""

from __future__ import annotations

import numpy as np


def validate_pair(
    rgb: np.ndarray,
    spectral: np.ndarray,
    *,
    expected_bands: int,
    require_normalized_rgb: bool = True,
) -> None:
    """Validate a paired RGB/spectral sample without changing spectral values."""
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError(f"Expected H x W x 3 RGB data, got {rgb.shape}")
    if spectral.ndim != 3 or spectral.shape[-1] != expected_bands:
        raise ValueError(f"Expected H x W x {expected_bands} spectral data, got {spectral.shape}")
    if rgb.shape[:2] != spectral.shape[:2]:
        raise ValueError(f"RGB/spectral spatial mismatch: {rgb.shape[:2]} vs {spectral.shape[:2]}")
    if rgb.dtype != np.float32 or spectral.dtype != np.float32:
        raise ValueError("RGB and spectral arrays must be float32 after preprocessing")
    if not np.isfinite(rgb).all() or not np.isfinite(spectral).all():
        raise ValueError("RGB and spectral arrays must not contain NaN or Inf")
    if require_normalized_rgb and (rgb.min() < 0.0 or rgb.max() > 1.0):
        raise ValueError("Normalized RGB values must remain in [0, 1]")

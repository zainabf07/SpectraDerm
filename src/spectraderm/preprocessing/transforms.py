"""Paired spatial transforms that preserve RGB/spectral correspondence."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def resize_pair_opencv(rgb: np.ndarray, spectral: np.ndarray, size: int = 256) -> tuple[np.ndarray, np.ndarray]:
    """Resize a pair with the same bilinear OpenCV interpolation used for Hyper-Skin."""
    resized_rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    resized_spectral = np.stack(
        [cv2.resize(spectral[:, :, band], (size, size), interpolation=cv2.INTER_LINEAR) for band in range(spectral.shape[-1])],
        axis=-1,
    ).astype(np.float32)
    return resized_rgb, resized_spectral


def resize_pair_pillow(rgb: np.ndarray, spectral: np.ndarray, size: int = 256) -> tuple[np.ndarray, np.ndarray]:
    """Resize a pair with the bilinear Pillow behavior used for UMINHO-HSFD."""
    rgb_uint8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    resized_rgb = np.asarray(
        Image.fromarray(rgb_uint8).resize((size, size), Image.Resampling.BILINEAR), dtype=np.float32
    ) / 255.0
    resized_spectral = np.empty((size, size, spectral.shape[-1]), dtype=np.float32)
    for band in range(spectral.shape[-1]):
        resized_spectral[:, :, band] = np.asarray(
            Image.fromarray(spectral[:, :, band]).resize((size, size), Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
    return resized_rgb, resized_spectral


def horizontal_flip_pair(rgb: np.ndarray, spectral: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply an identical horizontal flip to a paired sample."""
    return np.flip(rgb, axis=1).copy(), np.flip(spectral, axis=1).copy()


def augment_hyperskin_pair(
    rgb: np.ndarray, spectral: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Apply Hyper-Skin's paired horizontal/vertical flip and right-angle rotation policy."""
    if rng.random() < 0.5:
        rgb, spectral = horizontal_flip_pair(rgb, spectral)
    if rng.random() < 0.5:
        rgb, spectral = np.flip(rgb, axis=0).copy(), np.flip(spectral, axis=0).copy()
    rotations = int(rng.integers(0, 4))
    if rotations:
        rgb = np.rot90(rgb, k=rotations, axes=(0, 1)).copy()
        spectral = np.rot90(spectral, k=rotations, axes=(0, 1)).copy()
    return rgb, spectral

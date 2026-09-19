"""
Module G — Skin Detection / Segmentation

Purpose:
    Identify the skin region in an RGB image so that downstream
    SpectraDerm analysis focuses on relevant skin pixels rather than
    background, hair, clothing, or other non-skin regions.

Requirements:
    - Accept an RGB NumPy image.
    - Validate image shape and numeric values.
    - Produce a binary skin mask with shape (H, W).
    - Preserve the original image dimensions.
    - Return useful segmentation metadata.
    - Never interpret the mask as a disease or lesion diagnosis.
    - Do not claim clinical segmentation accuracy.

Initial implementation:
    Build a lightweight, explainable baseline suitable for the current
    prototype. Keep the implementation modular so it can later be
    replaced or compared with a trained segmentation model.

Safety:
    Skin segmentation identifies candidate skin pixels only.
    It must NOT be described as disease detection, lesion detection,
    or medical diagnosis.
"""

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class SkinSegmentationResult:
    mask: np.ndarray
    skin_fraction: float
    method: str


def _validate_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a NumPy array")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must have shape (H, W, 3)")
    if image.shape[0] < 2 or image.shape[1] < 2:
        raise ValueError("image dimensions are too small")
    if not np.isfinite(image).all():
        raise ValueError("image contains NaN or infinite values")


def segment_skin(image: np.ndarray) -> SkinSegmentationResult:
    """
    Lightweight skin-region segmentation baseline.

    Identifies candidate skin pixels only. It is not lesion detection,
    disease detection, or diagnosis.
    """
    _validate_image(image)

    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255.0).clip(0, 255).astype(np.uint8)
        else:
            image = image.clip(0, 255).astype(np.uint8)

    ycrcb = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

    y, cr, cb = cv2.split(ycrcb)
    _, saturation, _ = cv2.split(hsv)

    # Primary chromaticity rule.
    primary = (
        (cr >= 125)
        & (cr <= 190)
        & (cb >= 75)
        & (cb <= 145)
        & (saturation >= 15)
        & (y >= 10)
    )

    # Normalized RGB helps under darker illumination.
    rgb = image.astype(np.float32) + 1.0
    total = rgb.sum(axis=2)
    r = rgb[:, :, 0] / total
    g = rgb[:, :, 1] / total

    chromatic = (
        (r >= 0.30)
        & (r <= 0.55)
        & (g >= 0.20)
        & (g <= 0.45)
        & (r > g)
    )

    mask = (primary | chromatic).astype(np.uint8) * 255

    # Suppress very dark background.
    mask[y < 8] = 0

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Retain sufficiently large connected regions.
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)

    cleaned = np.zeros_like(mask)
    image_area = image.shape[0] * image.shape[1]

    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area >= image_area * 0.002:
            cleaned[labels == label] = 255

    skin_fraction = float(np.count_nonzero(cleaned) / image_area)

    return SkinSegmentationResult(
        mask=cleaned,
        skin_fraction=skin_fraction,
        method="ycrcb_normalized_rgb_baseline",
    )

@dataclass(frozen=True)
class SkinSegmentationResult:
    mask: np.ndarray
    skin_fraction: float
    method: str


def _validate_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a NumPy array")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must have shape (H, W, 3)")
    if image.shape[0] < 2 or image.shape[1] < 2:
        raise ValueError("image dimensions are too small")
    if not np.isfinite(image).all():
        raise ValueError("image contains NaN or infinite values")


def segment_skin(image: np.ndarray) -> SkinSegmentationResult:
    """
    Lightweight baseline skin-region segmentation.

    This identifies candidate skin pixels only. It is not lesion
    detection, disease detection, or diagnosis.
    """
    _validate_image(image)

    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255.0).clip(0, 255).astype(np.uint8)
        else:
            image = image.clip(0, 255).astype(np.uint8)

    ycrcb = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

    y, cr, cb = cv2.split(ycrcb)
    _, saturation, _ = cv2.split(hsv)

    # Conservative baseline candidate rule.
    mask = (
        (cr >= 135)
        & (cr <= 180)
        & (cb >= 85)
        & (cb <= 135)
        & (saturation >= 20)
        & (y >= 20)
    ).astype(np.uint8) * 255

    # Remove isolated noise and fill small gaps.
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Keep reasonably sized connected regions.
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)

    cleaned = np.zeros_like(mask)
    image_area = image.shape[0] * image.shape[1]

    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area >= image_area * 0.005:
            cleaned[labels == label] = 255

    skin_fraction = float(np.count_nonzero(cleaned) / image_area)

    return SkinSegmentationResult(
        mask=cleaned,
        skin_fraction=skin_fraction,
        method="ycrcb_normalized_rgb_baseline",
    )
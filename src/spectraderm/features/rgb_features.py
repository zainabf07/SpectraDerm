"""Conventional, non-diagnostic RGB feature extraction for selected image ROIs.

Pigmentation-related outputs in this module are RGB appearance proxies. They
are not direct measurements of melanin or any other biological quantity.
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


_EPSILON = 1e-8

_COLOR_FEATURES = [
    "color_mean_r", "color_mean_g", "color_mean_b",
    "color_std_r", "color_std_g", "color_std_b",
    "color_median_r", "color_median_g", "color_median_b",
    "color_mean_h", "color_mean_s", "color_mean_v",
    "color_std_h", "color_std_s", "color_std_v",
]
_TEXTURE_FEATURES = [
    "grayscale_mean", "grayscale_std", "gradient_mean", "gradient_std",
    "local_variance_mean",
]
_SHAPE_FEATURES = [
    "shape_area_pixels", "shape_area_fraction", "shape_perimeter",
    "shape_bbox_width", "shape_bbox_height", "shape_aspect_ratio",
    "shape_extent", "shape_solidity", "shape_circularity",
]
_CONTRAST_FEATURES = [
    "local_contrast_gray", "local_contrast_r", "local_contrast_g",
    "local_contrast_b",
]
_PIGMENTATION_FEATURES = [
    "pigmentation_darkness_proxy", "pigmentation_red_green_ratio",
    "pigmentation_red_blue_ratio", "pigmentation_chroma_proxy",
]


@dataclass(frozen=True)
class RGBFeatureResult:
    """Numerical RGB features and extraction metadata for a selected ROI."""

    features: dict[str, float]
    feature_groups: dict[str, list[str]]
    roi_pixel_count: int
    mask_fraction: float
    image_shape: tuple[int, int, int]
    warnings: list[str]


def _validate_and_normalize_rgb(rgb: np.ndarray) -> np.ndarray:
    if not isinstance(rgb, np.ndarray):
        raise TypeError("rgb must be a NumPy array")
    if rgb.ndim != 3:
        raise ValueError("rgb must have shape (H, W, 3)")
    if rgb.shape[2] != 3:
        raise ValueError("rgb must have exactly three channels")
    if rgb.shape[0] == 0 or rgb.shape[1] == 0:
        raise ValueError("rgb image dimensions must be non-zero")
    if not np.issubdtype(rgb.dtype, np.number):
        raise TypeError("rgb must have a numeric dtype")
    if not np.isfinite(rgb).all():
        raise ValueError("rgb contains NaN or infinite values")

    if rgb.dtype == np.uint8:
        return rgb.astype(np.float64) / 255.0
    if np.issubdtype(rgb.dtype, np.floating):
        if np.any(rgb < 0.0) or np.any(rgb > 1.0):
            raise ValueError("floating-point rgb values must be within [0, 1]")
        return rgb.astype(np.float64, copy=False)
    raise TypeError("rgb dtype must be uint8 or a floating-point dtype")


def _validate_mask(mask: Optional[np.ndarray], image_shape: tuple[int, int, int]) -> tuple[np.ndarray, bool]:
    height, width, _ = image_shape
    if mask is None:
        return np.ones((height, width), dtype=bool), False
    if not isinstance(mask, np.ndarray):
        raise TypeError("mask must be a NumPy array")
    if mask.ndim != 2:
        raise ValueError("mask must have shape (H, W)")
    if mask.shape != (height, width):
        raise ValueError("mask dimensions must match rgb dimensions")
    if not (np.issubdtype(mask.dtype, np.number) or mask.dtype == np.bool_):
        raise TypeError("mask must have a numeric or boolean dtype")
    if np.issubdtype(mask.dtype, np.floating) and not np.isfinite(mask).all():
        raise ValueError("mask contains NaN or infinite values")
    roi = mask.astype(bool)
    if not roi.any():
        raise ValueError("mask must include at least one ROI pixel")
    return roi, True


def _nan_features(names: list[str]) -> dict[str, float]:
    return {name: float("nan") for name in names}


def _shape_features(roi: np.ndarray) -> dict[str, float]:
    area_pixels = int(np.count_nonzero(roi))
    contours, _ = cv2.findContours(
        roi.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    points = np.argwhere(roi)
    min_y, min_x = points.min(axis=0)
    max_y, max_x = points.max(axis=0)
    bbox_width = int(max_x - min_x + 1)
    bbox_height = int(max_y - min_y + 1)
    perimeter = float(sum(cv2.arcLength(contour, True) for contour in contours))
    contour_area = float(sum(cv2.contourArea(contour) for contour in contours))
    all_points = np.concatenate(contours, axis=0) if contours else np.empty((0, 1, 2), dtype=np.int32)
    hull_area = float(cv2.contourArea(cv2.convexHull(all_points))) if len(all_points) >= 3 else 0.0

    return {
        "shape_area_pixels": float(area_pixels),
        "shape_area_fraction": float(area_pixels / roi.size),
        "shape_perimeter": perimeter,
        "shape_bbox_width": float(bbox_width),
        "shape_bbox_height": float(bbox_height),
        "shape_aspect_ratio": float(bbox_width / bbox_height),
        "shape_extent": float(area_pixels / (bbox_width * bbox_height)),
        "shape_solidity": float(contour_area / hull_area) if hull_area > _EPSILON else float("nan"),
        "shape_circularity": float(4.0 * np.pi * area_pixels / (perimeter * perimeter))
        if perimeter > _EPSILON else float("nan"),
    }


def _local_contrast(rgb: np.ndarray, gray: np.ndarray, roi: np.ndarray) -> dict[str, float]:
    points = np.argwhere(roi)
    min_y, min_x = points.min(axis=0)
    max_y, max_x = points.max(axis=0)
    bbox_size = max(max_y - min_y + 1, max_x - min_x + 1)
    margin = max(1, int(np.ceil(bbox_size * 0.1)))
    y0, y1 = max(0, min_y - margin), min(roi.shape[0], max_y + margin + 1)
    x0, x1 = max(0, min_x - margin), min(roi.shape[1], max_x + margin + 1)
    surrounding = np.zeros_like(roi, dtype=bool)
    surrounding[y0:y1, x0:x1] = True
    surrounding &= ~roi
    if not surrounding.any():
        return _nan_features(_CONTRAST_FEATURES)
    roi_rgb_mean = rgb[roi].mean(axis=0)
    surrounding_rgb_mean = rgb[surrounding].mean(axis=0)
    return {
        "local_contrast_gray": float(abs(gray[roi].mean() - gray[surrounding].mean())),
        "local_contrast_r": float(abs(roi_rgb_mean[0] - surrounding_rgb_mean[0])),
        "local_contrast_g": float(abs(roi_rgb_mean[1] - surrounding_rgb_mean[1])),
        "local_contrast_b": float(abs(roi_rgb_mean[2] - surrounding_rgb_mean[2])),
    }


def extract_rgb_features(rgb: np.ndarray, mask: Optional[np.ndarray] = None) -> RGBFeatureResult:
    """Extract deterministic conventional RGB features over ``mask`` or all pixels.

    Float images must already be normalized to [0, 1]; uint8 images are
    normalized internally. Shape and local-contrast features are undefined
    without a supplied ROI mask and are returned as NaN with warnings.
    """
    image = _validate_and_normalize_rgb(rgb)
    roi, has_mask = _validate_mask(mask, image.shape)
    warnings: list[str] = []
    selected_rgb = image[roi]
    hsv = cv2.cvtColor(image.astype(np.float32), cv2.COLOR_RGB2HSV).astype(np.float64)
    hsv[..., 0] /= 360.0  # Store hue consistently in [0, 1].
    selected_hsv = hsv[roi]
    gray = cv2.cvtColor(image.astype(np.float32), cv2.COLOR_RGB2GRAY).astype(np.float64)

    features = {
        "color_mean_r": float(selected_rgb[:, 0].mean()),
        "color_mean_g": float(selected_rgb[:, 1].mean()),
        "color_mean_b": float(selected_rgb[:, 2].mean()),
        "color_std_r": float(selected_rgb[:, 0].std()),
        "color_std_g": float(selected_rgb[:, 1].std()),
        "color_std_b": float(selected_rgb[:, 2].std()),
        "color_median_r": float(np.median(selected_rgb[:, 0])),
        "color_median_g": float(np.median(selected_rgb[:, 1])),
        "color_median_b": float(np.median(selected_rgb[:, 2])),
        "color_mean_h": float(selected_hsv[:, 0].mean()),
        "color_mean_s": float(selected_hsv[:, 1].mean()),
        "color_mean_v": float(selected_hsv[:, 2].mean()),
        "color_std_h": float(selected_hsv[:, 0].std()),
        "color_std_s": float(selected_hsv[:, 1].std()),
        "color_std_v": float(selected_hsv[:, 2].std()),
    }

    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient = np.hypot(grad_x, grad_y)
    local_mean = cv2.blur(gray, (3, 3))
    local_variance = np.maximum(cv2.blur(gray * gray, (3, 3)) - local_mean * local_mean, 0.0)
    features.update({
        "grayscale_mean": float(gray[roi].mean()),
        "grayscale_std": float(gray[roi].std()),
        "gradient_mean": float(gradient[roi].mean()),
        "gradient_std": float(gradient[roi].std()),
        "local_variance_mean": float(local_variance[roi].mean()),
    })

    if has_mask:
        features.update(_shape_features(roi))
        contrast = _local_contrast(image, gray, roi)
        features.update(contrast)
        if any(np.isnan(value) for value in contrast.values()):
            warnings.append("Local ROI contrast is undefined because no surrounding pixels are available.")
    else:
        features.update(_nan_features(_SHAPE_FEATURES))
        features.update(_nan_features(_CONTRAST_FEATURES))
        warnings.append("Shape features are undefined because no ROI mask was supplied.")
        warnings.append("Local ROI contrast is undefined because no ROI mask was supplied.")

    neutral = selected_rgb.mean(axis=1, keepdims=True)
    features.update({
        "pigmentation_darkness_proxy": float(1.0 - gray[roi].mean()),
        "pigmentation_red_green_ratio": float(features["color_mean_r"] / (features["color_mean_g"] + _EPSILON)),
        "pigmentation_red_blue_ratio": float(features["color_mean_r"] / (features["color_mean_b"] + _EPSILON)),
        "pigmentation_chroma_proxy": float(np.linalg.norm(selected_rgb - neutral, axis=1).mean()),
    })

    return RGBFeatureResult(
        features=features,
        feature_groups={
            "color": list(_COLOR_FEATURES),
            "texture": list(_TEXTURE_FEATURES),
            "shape": list(_SHAPE_FEATURES),
            "local_contrast": list(_CONTRAST_FEATURES),
            "pigmentation_related_rgb_proxies": list(_PIGMENTATION_FEATURES),
        },
        roi_pixel_count=int(roi.sum()),
        mask_fraction=float(roi.mean()),
        image_shape=tuple(image.shape),
        warnings=warnings,
    )

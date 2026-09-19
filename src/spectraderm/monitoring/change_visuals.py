"""Display images for the monitoring result: highlighted region and difference map.

All images are 256px display renders of real pipeline inputs/outputs. The
difference map compares the current photo with the baseline photo pixel by
pixel (CIELAB colour difference inside detected skin); it assumes the two
photos were taken with similar framing, so it is labelled as approximate.
"""
from __future__ import annotations

import base64
from typing import Any

import cv2
import numpy as np

# Colour difference (CIELAB delta-E) shown as the top of the colour scale.
DELTA_E_FULL_SCALE = 25.0
REGION_THRESHOLD = 0.35
HIGHLIGHT_BGR = (58, 92, 184)  # clay, matches the frontend accent


def _jpeg_data_url(rgb_float: np.ndarray) -> str:
    pixels = np.clip(rgb_float * 255.0, 0, 255).round().astype(np.uint8)
    ok, buffer = cv2.imencode(".jpg", cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise RuntimeError("Display image encoding failed.")
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.tobytes()).decode('ascii')}"


def _largest_box(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if count <= 1:
        return None
    label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = (int(stats[label, index]) for index in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
    return x, y, w, h


def _changed_box(mask: np.ndarray, min_area: float) -> tuple[int, int, int, int] | None:
    """Bounding box around every sizeable changed component."""
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    keep = [label for label in range(1, count) if stats[label, cv2.CC_STAT_AREA] >= min_area]
    if not keep:
        return None
    x0 = min(int(stats[label, cv2.CC_STAT_LEFT]) for label in keep)
    y0 = min(int(stats[label, cv2.CC_STAT_TOP]) for label in keep)
    x1 = max(int(stats[label, cv2.CC_STAT_LEFT] + stats[label, cv2.CC_STAT_WIDTH]) for label in keep)
    y1 = max(int(stats[label, cv2.CC_STAT_TOP] + stats[label, cv2.CC_STAT_HEIGHT]) for label in keep)
    return x0, y0, x1 - x0, y1 - y0


def _draw_box(rgb_float: np.ndarray, box: tuple[int, int, int, int] | None) -> np.ndarray:
    image = cv2.cvtColor(np.clip(rgb_float * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    if box is not None:
        x, y, w, h = box
        cv2.rectangle(image, (x, y), (x + w - 1, y + h - 1), HIGHLIGHT_BGR, 2)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def _prepare(rgb_float: np.ndarray, size: int) -> np.ndarray:
    if rgb_float.shape[:2] != (size, size):
        rgb_float = cv2.resize(rgb_float, (size, size), interpolation=cv2.INTER_AREA)
    return np.clip(rgb_float.astype(np.float32), 0.0, 1.0)


def build_change_visuals(
    current_rgb: np.ndarray, current_mask: np.ndarray | None,
    baseline_rgb: np.ndarray | None = None, baseline_mask: np.ndarray | None = None,
    spectral_false_color: np.ndarray | None = None, size: int = 256,
) -> dict[str, Any]:
    """Return data-URL images plus the monitored-region box (in 0..1 units)."""
    current = _prepare(current_rgb, size)
    mask = np.ones((size, size), bool) if current_mask is None or not current_mask.any() else (
        cv2.resize(current_mask.astype(np.uint8), (size, size), interpolation=cv2.INTER_NEAREST).astype(bool)
    )
    visuals: dict[str, Any] = {}
    box = _largest_box(mask)
    region_basis = "skin_region"

    if baseline_rgb is not None:
        baseline = _prepare(baseline_rgb, size)
        base_mask = mask if baseline_mask is None else (
            cv2.resize(baseline_mask.astype(np.uint8), (size, size), interpolation=cv2.INTER_NEAREST).astype(bool)
        )
        # Union: a changed area can drop out of one photo's skin mask
        # precisely because its colour changed.
        region = mask | base_mask
        lab_current = cv2.cvtColor(current, cv2.COLOR_RGB2LAB)
        lab_baseline = cv2.cvtColor(baseline, cv2.COLOR_RGB2LAB)
        delta_e = np.linalg.norm(lab_current - lab_baseline, axis=2)
        delta_e = cv2.GaussianBlur(delta_e, (0, 0), 3)
        strength = np.clip(delta_e / DELTA_E_FULL_SCALE, 0.0, 1.0) * region
        heat = cv2.applyColorMap((strength * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
        heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        gray = np.repeat(cv2.cvtColor(current, cv2.COLOR_RGB2GRAY)[..., None], 3, axis=2)
        alpha = (0.25 + 0.65 * strength)[..., None]
        difference = gray * (1 - alpha) + heat * alpha
        changed = cv2.morphologyEx(
            (strength >= REGION_THRESHOLD).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8),
        )
        changed_box = _changed_box(changed, min_area=0.002 * size * size)
        if changed_box is not None:
            box, region_basis = changed_box, "largest_difference"
        visuals["baseline_image"] = _jpeg_data_url(baseline)
        visuals["difference_map"] = _jpeg_data_url(_draw_box(difference, box))
        visuals["mean_color_difference"] = round(float(delta_e[region].mean()), 2) if region.any() else None

    visuals["current_image"] = _jpeg_data_url(current)
    visuals["current_highlighted"] = _jpeg_data_url(_draw_box(current, box))
    if spectral_false_color is not None:
        visuals["spectral_highlighted"] = _jpeg_data_url(_draw_box(_prepare(spectral_false_color, size), box))
    visuals["region"] = None if box is None else {
        "x": box[0] / size, "y": box[1] / size, "width": box[2] / size, "height": box[3] / size,
        "basis": region_basis,
    }
    return visuals

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class RegionCandidate:
    bbox: tuple[int, int, int, int]
    area: int
    score: float


@dataclass(frozen=True)
class LocalizationResult:
    candidates: list[RegionCandidate]
    method: str


def localize_regions(
    skin_mask: np.ndarray,
    min_area_fraction: float = 0.005,
) -> LocalizationResult:
    """
    Locate candidate regions inside a supplied skin mask.

    This identifies candidate ROIs only. It does not identify lesions,
    diseases, or diagnoses.
    """
    if not isinstance(skin_mask, np.ndarray):
        raise TypeError("skin_mask must be a NumPy array")

    if skin_mask.ndim != 2:
        raise ValueError("skin_mask must have shape (H, W)")

    if not np.isfinite(skin_mask).all():
        raise ValueError("skin_mask contains NaN or infinite values")

    if min_area_fraction <= 0 or min_area_fraction > 1:
        raise ValueError("min_area_fraction must be in (0, 1]")

    binary = (skin_mask > 0).astype(np.uint8)

    height, width = binary.shape
    image_area = height * width
    min_area = image_area * min_area_fraction

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary,
        connectivity=8,
    )

    candidates = []

    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])

        if area < min_area:
            continue

        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])

        score = float(area / image_area)

        candidates.append(
            RegionCandidate(
                bbox=(x, y, w, h),
                area=area,
                score=score,
            )
        )

    candidates.sort(key=lambda candidate: candidate.area, reverse=True)

    return LocalizationResult(
        candidates=candidates,
        method="connected_components_skin_roi",
    )
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import cv2
import numpy as np


class QualityStatus(str, Enum):
    GOOD = "GOOD"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


@dataclass(frozen=True)
class QualityThresholds:
    """Initial engineering thresholds.

    These are NOT clinically validated thresholds.
    They should be calibrated using representative project data.
    """

    min_width: int = 256
    min_height: int = 256

# Provisional engineering thresholds calibrated against a small
# Hyper-Skin and UMINHO-HSFD sample with controlled Gaussian blur.
# These values are not clinically validated and must be recalibrated
# on a larger representative evaluation set before deployment.
    blur_reject: float = 5.0
    blur_review: float = 10.0

    # Mean grayscale intensity, normalized to [0, 1].
    exposure_dark_reject: float = 0.05
    exposure_dark_review: float = 0.15
    exposure_bright_review: float = 0.90
    exposure_bright_reject: float = 0.98

    # Fraction of pixels that are very dark/bright.
    clipping_reject_fraction: float = 0.20
    clipping_review_fraction: float = 0.10

    # Illumination uniformity.
    # Lower coefficient of variation generally means more uniform lighting.
    lighting_cv_review: float = 0.50
    lighting_cv_reject: float = 0.80

    # Framing: fraction of image that must contain non-background content.
    framing_min_content_fraction: float = 0.10


@dataclass
class QualityMetric:
    name: str
    value: float | int | bool | str
    status: QualityStatus
    message: str


@dataclass
class ImageQualityResult:
    status: QualityStatus
    passed: bool
    metrics: dict[str, QualityMetric] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    @property
    def is_good(self) -> bool:
        return self.status == QualityStatus.GOOD


def _validate_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a numpy.ndarray")

    if image.ndim not in (2, 3):
        raise ValueError("image must have shape HxW or HxWxC")

    if image.shape[0] < 1 or image.shape[1] < 1:
        raise ValueError("image must have non-zero dimensions")

    if not np.isfinite(image.astype(np.float32)).all():
        raise ValueError("image contains NaN or infinite values")


def _to_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        gray = image.astype(np.float32)
    elif image.shape[2] == 1:
        gray = image[:, :, 0].astype(np.float32)
    elif image.shape[2] == 3:
        gray = cv2.cvtColor(image.astype(np.float32), cv2.COLOR_RGB2GRAY)
    elif image.shape[2] == 4:
        gray = cv2.cvtColor(image.astype(np.float32), cv2.COLOR_RGBA2GRAY)
    else:
        raise ValueError("image must have 1, 3, or 4 channels")

    # Normalize integer images and common [0, 255] floating images.
    if np.issubdtype(image.dtype, np.integer):
        max_value = np.iinfo(image.dtype).max
        if max_value > 1:
            gray /= float(max_value)
    elif gray.max(initial=0.0) > 1.0:
        gray /= 255.0

    return np.clip(gray, 0.0, 1.0)


def _metric_status(
    value: float,
    review_threshold: float,
    reject_threshold: float,
    higher_is_better: bool = True,
) -> QualityStatus:
    if higher_is_better:
        if value < reject_threshold:
            return QualityStatus.REJECT
        if value < review_threshold:
            return QualityStatus.REVIEW
        return QualityStatus.GOOD

    if value > reject_threshold:
        return QualityStatus.REJECT
    if value > review_threshold:
        return QualityStatus.REVIEW
    return QualityStatus.GOOD


def assess_blur(
    image: np.ndarray,
    thresholds: QualityThresholds | None = None,
) -> QualityMetric:
    thresholds = thresholds or QualityThresholds()
    gray = _to_grayscale(image)

    gray_255 = (gray * 255.0).astype(np.float32)
    value = float(cv2.Laplacian(gray_255, cv2.CV_32F).var())
    status = _metric_status(
        value,
        thresholds.blur_review,
        thresholds.blur_reject,
        higher_is_better=True,
    )

    messages = {
        QualityStatus.GOOD: "Image sharpness is acceptable.",
        QualityStatus.REVIEW: "Image may be somewhat blurred.",
        QualityStatus.REJECT: "Image appears strongly blurred.",
    }

    return QualityMetric(
        name="blur",
        value=value,
        status=status,
        message=messages[status],
    )


def assess_exposure(
    image: np.ndarray,
    thresholds: QualityThresholds | None = None,
) -> list[QualityMetric]:
    thresholds = thresholds or QualityThresholds()
    gray = _to_grayscale(image)

    mean_intensity = float(np.mean(gray))

    dark_fraction = float(np.mean(gray <= 0.02))
    bright_fraction = float(np.mean(gray >= 0.98))

    if mean_intensity <= thresholds.exposure_dark_reject:
        exposure_status = QualityStatus.REJECT
        exposure_message = "Image is likely severely underexposed."
    elif mean_intensity <= thresholds.exposure_dark_review:
        exposure_status = QualityStatus.REVIEW
        exposure_message = "Image may be underexposed."
    elif mean_intensity >= thresholds.exposure_bright_reject:
        exposure_status = QualityStatus.REJECT
        exposure_message = "Image is likely severely overexposed."
    elif mean_intensity >= thresholds.exposure_bright_review:
        exposure_status = QualityStatus.REVIEW
        exposure_message = "Image may be overexposed."
    else:
        exposure_status = QualityStatus.GOOD
        exposure_message = "Mean exposure is within the configured range."

    clipping_fraction = max(dark_fraction, bright_fraction)

    if clipping_fraction >= thresholds.clipping_reject_fraction:
        clipping_status = QualityStatus.REJECT
    elif clipping_fraction >= thresholds.clipping_review_fraction:
        clipping_status = QualityStatus.REVIEW
    else:
        clipping_status = QualityStatus.GOOD

    clipping_message = {
        QualityStatus.GOOD: "Clipping is limited.",
        QualityStatus.REVIEW: "Some pixels may be clipped.",
        QualityStatus.REJECT: "A substantial fraction of pixels is clipped.",
    }[clipping_status]

    return [
        QualityMetric(
            name="exposure_mean",
            value=mean_intensity,
            status=exposure_status,
            message=exposure_message,
        ),
        QualityMetric(
            name="exposure_clipping",
            value=clipping_fraction,
            status=clipping_status,
            message=clipping_message,
        ),
    ]


def assess_lighting(
    image: np.ndarray,
    thresholds: QualityThresholds | None = None,
) -> QualityMetric:
    thresholds = thresholds or QualityThresholds()
    gray = _to_grayscale(image)

    mean = float(np.mean(gray))
    std = float(np.std(gray))

    if mean <= 1e-8:
        coefficient_of_variation = float("inf")
    else:
        coefficient_of_variation = std / mean

    status = _metric_status(
        coefficient_of_variation,
        thresholds.lighting_cv_review,
        thresholds.lighting_cv_reject,
        higher_is_better=False,
    )

    messages = {
        QualityStatus.GOOD: "Lighting appears reasonably uniform.",
        QualityStatus.REVIEW: "Lighting may be uneven.",
        QualityStatus.REJECT: "Lighting variation is high.",
    }

    return QualityMetric(
        name="lighting_uniformity",
        value=coefficient_of_variation,
        status=status,
        message=messages[status],
    )


def assess_resolution(
    image: np.ndarray,
    thresholds: QualityThresholds | None = None,
) -> QualityMetric:
    thresholds = thresholds or QualityThresholds()

    height, width = image.shape[:2]

    if width < thresholds.min_width or height < thresholds.min_height:
        status = QualityStatus.REJECT
        message = (
            f"Resolution {width}x{height} is below the minimum "
            f"{thresholds.min_width}x{thresholds.min_height}."
        )
    else:
        status = QualityStatus.GOOD
        message = f"Resolution {width}x{height} meets the minimum requirement."

    return QualityMetric(
        name="resolution",
        value=width * height,
        status=status,
        message=message,
    )


def assess_framing(
    image: np.ndarray,
    thresholds: QualityThresholds | None = None,
) -> QualityMetric:
    """Simple baseline framing check.

    This is intentionally conservative: it detects whether the image
    contains enough non-near-black content. It is NOT a face detector.
    """

    thresholds = thresholds or QualityThresholds()
    gray = _to_grayscale(image)

    content_fraction = float(np.mean(gray > 0.02))

    if content_fraction < thresholds.framing_min_content_fraction:
        status = QualityStatus.REJECT
        message = "Very little usable image content was detected."
    else:
        status = QualityStatus.GOOD
        message = "Image contains sufficient visible content."

    return QualityMetric(
        name="framing",
        value=content_fraction,
        status=status,
        message=message,
    )


def assess_image_quality(
    image: np.ndarray,
    thresholds: QualityThresholds | None = None,
) -> ImageQualityResult:
    """Run the complete image quality assessment pipeline."""

    thresholds = thresholds or QualityThresholds()
    _validate_image(image)

    metrics: dict[str, QualityMetric] = {}

    metrics["blur"] = assess_blur(image, thresholds)

    for metric in assess_exposure(image, thresholds):
        metrics[metric.name] = metric

    metrics["lighting"] = assess_lighting(image, thresholds)
    metrics["resolution"] = assess_resolution(image, thresholds)
    metrics["framing"] = assess_framing(image, thresholds)

    statuses = [metric.status for metric in metrics.values()]

    if QualityStatus.REJECT in statuses:
        overall_status = QualityStatus.REJECT
    elif QualityStatus.REVIEW in statuses:
        overall_status = QualityStatus.REVIEW
    else:
        overall_status = QualityStatus.GOOD

    reasons = [
        metric.message
        for metric in metrics.values()
        if metric.status != QualityStatus.GOOD
    ]

    return ImageQualityResult(
        status=overall_status,
        passed=overall_status == QualityStatus.GOOD,
        metrics=metrics,
        reasons=reasons,
    )
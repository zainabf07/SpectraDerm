import numpy as np
import pytest

from spectraderm.vision.quality import (
    QualityStatus,
    QualityThresholds,
    assess_image_quality,
)


def test_good_image_passes():
    rng = np.random.default_rng(42)

    image = rng.uniform(
        0.2,
        0.8,
        size=(512, 512, 3),
    ).astype(np.float32)

    result = assess_image_quality(image)

    assert result.status in {
        QualityStatus.GOOD,
        QualityStatus.REVIEW,
    }
    assert "blur" in result.metrics
    assert "resolution" in result.metrics
    assert "framing" in result.metrics


def test_low_resolution_is_rejected():
    image = np.ones((100, 100, 3), dtype=np.float32) * 0.5

    result = assess_image_quality(image)

    assert result.status == QualityStatus.REJECT
    assert result.metrics["resolution"].status == QualityStatus.REJECT


def test_dark_image_is_rejected():
    image = np.zeros((512, 512, 3), dtype=np.float32)

    result = assess_image_quality(image)

    assert result.status == QualityStatus.REJECT
    assert result.metrics["exposure_mean"].status == QualityStatus.REJECT


def test_invalid_dimensions_raise_error():
    image = np.zeros((512,), dtype=np.float32)

    with pytest.raises(ValueError):
        assess_image_quality(image)


def test_nan_image_raises_error():
    image = np.ones((512, 512, 3), dtype=np.float32)
    image[0, 0, 0] = np.nan

    with pytest.raises(ValueError):
        assess_image_quality(image)


def test_thresholds_are_configurable():
    image = np.ones((512, 512, 3), dtype=np.float32) * 0.5

    thresholds = QualityThresholds(
        min_width=1024,
        min_height=1024,
    )

    result = assess_image_quality(image, thresholds)

    assert result.metrics["resolution"].status == QualityStatus.REJECT
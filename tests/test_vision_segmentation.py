import numpy as np
import pytest

from spectraderm.vision.segmentation import segment_skin


def test_segmentation_returns_valid_mask():
    image = np.full((256, 256, 3), [180, 130, 110], dtype=np.uint8)

    result = segment_skin(image)

    assert result.mask.shape == (256, 256)
    assert result.mask.dtype == np.uint8
    assert result.method == "ycrcb_normalized_rgb_baseline"
    assert 0.0 <= result.skin_fraction <= 1.0


def test_segmentation_rejects_invalid_shape():
    image = np.zeros((256, 256), dtype=np.uint8)

    with pytest.raises(ValueError):
        segment_skin(image)


def test_segmentation_rejects_nan():
    image = np.zeros((256, 256, 3), dtype=np.float32)
    image[0, 0, 0] = np.nan

    with pytest.raises(ValueError):
        segment_skin(image)
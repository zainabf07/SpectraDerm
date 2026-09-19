import numpy as np
import pytest

from spectraderm.vision.localization import localize_regions


def test_localization_finds_large_region():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:80, 20:80] = 255

    result = localize_regions(mask)

    assert len(result.candidates) == 1
    assert result.candidates[0].bbox == (20, 20, 60, 60)
    assert result.candidates[0].area == 3600


def test_localization_ignores_small_regions():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:12, 10:12] = 255
    mask[20:80, 20:80] = 255

    result = localize_regions(mask)

    assert len(result.candidates) == 1


def test_localization_rejects_invalid_mask():
    mask = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(ValueError):
        localize_regions(mask)

def test_localization_empty_mask_returns_no_candidates():
    mask = np.zeros((100, 100), dtype=np.uint8)

    result = localize_regions(mask)

    assert result.candidates == []


def test_localization_finds_multiple_regions():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[10:40, 10:40] = 255
    mask[60:90, 60:90] = 255

    result = localize_regions(mask)

    assert len(result.candidates) == 2
    assert result.candidates[0].area == 900
    assert result.candidates[1].area == 900


def test_localization_handles_border_touching_region():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[0:40, 0:40] = 255

    result = localize_regions(mask)

    assert len(result.candidates) == 1
    assert result.candidates[0].bbox == (0, 0, 40, 40)


def test_localization_rejects_invalid_numeric_values():
    mask = np.zeros((100, 100), dtype=np.float32)
    mask[20, 20] = np.nan

    with pytest.raises(ValueError):
        localize_regions(mask)

def test_localization_rejects_invalid_fraction():
    mask = np.zeros((100, 100), dtype=np.uint8)

    with pytest.raises(ValueError):
        localize_regions(mask, min_area_fraction=0)
import numpy as np
import pytest

from spectraderm.features.rgb_features import RGBFeatureResult, extract_rgb_features


@pytest.fixture
def rgb_image():
    image = np.zeros((12, 12, 3), dtype=np.uint8)
    image[..., 0] = 100
    image[..., 1] = 50
    image[..., 2] = 25
    image[4:8, 4:8] = [200, 100, 50]
    return image


@pytest.fixture
def square_mask():
    mask = np.zeros((12, 12), dtype=bool)
    mask[4:8, 4:8] = True
    return mask


def test_valid_uint8_rgb_extraction(rgb_image, square_mask):
    result = extract_rgb_features(rgb_image, square_mask)
    assert isinstance(result, RGBFeatureResult)
    assert result.image_shape == (12, 12, 3)
    assert result.roi_pixel_count == 16
    assert result.mask_fraction == pytest.approx(16 / 144)


def test_float_rgb_input_matches_uint8(rgb_image, square_mask):
    uint8_result = extract_rgb_features(rgb_image, square_mask)
    float_result = extract_rgb_features(rgb_image.astype(np.float32) / 255.0, square_mask)
    assert float_result.features == pytest.approx(uint8_result.features, nan_ok=True)


def test_expected_feature_keys_and_groups(rgb_image, square_mask):
    result = extract_rgb_features(rgb_image, square_mask)
    expected = {
        "color_mean_r", "color_std_h", "grayscale_mean", "gradient_std",
        "shape_circularity", "local_contrast_gray", "pigmentation_chroma_proxy",
    }
    assert expected <= result.features.keys()
    assert set(result.feature_groups) == {
        "color", "texture", "shape", "local_contrast", "pigmentation_related_rgb_proxies"
    }
    assert set().union(*map(set, result.feature_groups.values())) == set(result.features)


def test_color_and_hsv_statistics(rgb_image, square_mask):
    result = extract_rgb_features(rgb_image, square_mask).features
    assert result["color_mean_r"] == pytest.approx(200 / 255)
    assert result["color_mean_g"] == pytest.approx(100 / 255)
    assert result["color_median_b"] == pytest.approx(50 / 255)
    assert result["color_std_r"] == pytest.approx(0.0)
    assert result["color_mean_h"] == pytest.approx(1 / 18, abs=1e-6)
    assert result["color_mean_s"] == pytest.approx(0.75)
    assert result["color_mean_v"] == pytest.approx(200 / 255)


def test_texture_features_are_numerical(rgb_image, square_mask):
    features = extract_rgb_features(rgb_image, square_mask).features
    for name in ("grayscale_mean", "grayscale_std", "gradient_mean", "gradient_std", "local_variance_mean"):
        assert np.isfinite(features[name])


def test_shape_features_for_simple_square(rgb_image, square_mask):
    features = extract_rgb_features(rgb_image, square_mask).features
    assert features["shape_area_pixels"] == 16
    assert features["shape_bbox_width"] == 4
    assert features["shape_bbox_height"] == 4
    assert features["shape_aspect_ratio"] == 1
    assert features["shape_extent"] == 1
    assert features["shape_perimeter"] == pytest.approx(12.0)
    assert features["shape_circularity"] == pytest.approx(4 * np.pi * 16 / 12**2)


def test_local_contrast_uses_roi_context(rgb_image, square_mask):
    features = extract_rgb_features(rgb_image, square_mask).features
    assert features["local_contrast_r"] == pytest.approx(100 / 255)
    assert features["local_contrast_g"] == pytest.approx(50 / 255)
    assert features["local_contrast_b"] == pytest.approx(25 / 255)
    assert features["local_contrast_gray"] > 0


def test_pigmentation_related_features_are_rgb_proxies(rgb_image, square_mask):
    features = extract_rgb_features(rgb_image, square_mask).features
    assert features["pigmentation_darkness_proxy"] == pytest.approx(1 - (0.299 * 200 + 0.587 * 100 + 0.114 * 50) / 255)
    assert features["pigmentation_red_green_ratio"] == pytest.approx(2.0)
    assert features["pigmentation_red_blue_ratio"] == pytest.approx(4.0)
    assert features["pigmentation_chroma_proxy"] > 0


def test_no_mask_has_documented_undefined_shape_and_contrast(rgb_image):
    result = extract_rgb_features(rgb_image)
    assert np.isnan(result.features["shape_area_pixels"])
    assert np.isnan(result.features["local_contrast_gray"])
    assert len(result.warnings) == 2


@pytest.mark.parametrize(
    ("rgb", "exception"),
    [
        (np.zeros((8, 8), dtype=np.uint8), ValueError),
        (np.zeros((8, 8, 4), dtype=np.uint8), ValueError),
        (np.full((8, 8, 3), np.nan, dtype=np.float32), ValueError),
        (np.full((8, 8, 3), np.inf, dtype=np.float32), ValueError),
        (np.full((8, 8, 3), 1.1, dtype=np.float32), ValueError),
        (np.zeros((8, 8, 3), dtype=np.int16), TypeError),
    ],
)
def test_invalid_rgb_inputs_are_rejected(rgb, exception):
    with pytest.raises(exception):
        extract_rgb_features(rgb)


def test_invalid_masks_are_rejected(rgb_image):
    with pytest.raises(ValueError, match="dimensions"):
        extract_rgb_features(rgb_image, np.ones((11, 12), dtype=bool))
    with pytest.raises(ValueError, match="at least one"):
        extract_rgb_features(rgb_image, np.zeros((12, 12), dtype=bool))
    with pytest.raises(ValueError, match="shape"):
        extract_rgb_features(rgb_image, np.ones((12, 12, 1), dtype=bool))


def test_constant_image_has_no_infinite_computable_features():
    image = np.full((10, 10, 3), [64, 64, 64], dtype=np.uint8)
    mask = np.zeros((10, 10), dtype=bool)
    mask[2:8, 2:8] = True
    result = extract_rgb_features(image, mask)
    assert not any(np.isinf(value) for value in result.features.values())


def test_output_is_deterministic_and_numerical(rgb_image, square_mask):
    first = extract_rgb_features(rgb_image, square_mask)
    second = extract_rgb_features(rgb_image, square_mask)
    assert first.features == second.features
    assert all(isinstance(value, float) for value in first.features.values())

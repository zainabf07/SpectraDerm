import numpy as np
import pytest

from spectraderm.features.spectral_features import (
    HYPERSKIN_VIS_WAVELENGTHS,
    SpectralFeatureResult,
    extract_spectral_features,
)


@pytest.fixture
def cube():
    bands = np.arange(31, dtype=np.float64)
    return np.broadcast_to(bands, (4, 5, 31)).copy()


@pytest.fixture
def roi():
    mask = np.zeros((4, 5), dtype=bool)
    mask[:2, :2] = True
    return mask


def test_valid_cube_returns_result_and_metadata(cube):
    result = extract_spectral_features(cube)
    assert isinstance(result, SpectralFeatureResult)
    assert result.cube_shape == (4, 5, 31)
    assert result.roi_pixel_count == 20
    assert result.mask_fraction == 1.0


@pytest.mark.parametrize(
    "invalid_cube",
    [
        np.zeros((4, 5), dtype=float),
        np.zeros((4, 5, 30), dtype=float),
        np.zeros((0, 5, 31), dtype=float),
        np.zeros((4, 0, 31), dtype=float),
        np.full((4, 5, 31), np.nan),
        np.full((4, 5, 31), np.inf),
        np.full((4, 5, 31), "x", dtype=object),
    ],
)
def test_invalid_cube_inputs_are_rejected(invalid_cube):
    with pytest.raises((ValueError, TypeError)):
        extract_spectral_features(invalid_cube)


def test_non_array_cube_is_rejected():
    with pytest.raises(TypeError):
        extract_spectral_features([[[0.0] * 31]])


def test_default_wavelength_vector_is_exactly_canonical(cube):
    result = extract_spectral_features(cube)
    assert np.array_equal(HYPERSKIN_VIS_WAVELENGTHS, np.arange(400, 701, 10))
    assert np.array_equal(result.wavelengths_nm, HYPERSKIN_VIS_WAVELENGTHS)


def test_canonical_wavelengths_are_accepted(cube):
    result = extract_spectral_features(cube, HYPERSKIN_VIS_WAVELENGTHS)
    assert result.wavelengths_nm.size == 31


@pytest.mark.parametrize(
    "wavelengths",
    [
        np.arange(400, 700, 10),
        np.array([400] * 31, dtype=float),
        np.array([400, 420, 410] + list(range(430, 711, 10)), dtype=float)[:31],
        np.array([np.nan] + list(range(410, 701, 10))),
        np.array([np.inf] + list(range(410, 701, 10))),
    ],
)
def test_invalid_wavelength_vectors_are_rejected(cube, wavelengths):
    with pytest.raises(ValueError):
        extract_spectral_features(cube, wavelengths_nm=wavelengths)


def test_wavelengths_are_not_silently_sorted(cube):
    reversed_wavelengths = HYPERSKIN_VIS_WAVELENGTHS[::-1].copy()
    with pytest.raises(ValueError, match="strictly increasing"):
        extract_spectral_features(cube, wavelengths_nm=reversed_wavelengths)


def test_nonnumeric_wavelengths_are_rejected(cube):
    with pytest.raises(TypeError):
        extract_spectral_features(cube, wavelengths_nm=np.full(31, "x", dtype=object))


def test_known_band_mean_std_and_names(cube):
    result = extract_spectral_features(cube).features
    assert result["spectral_mean_400"] == 0.0
    assert result["spectral_mean_540"] == 14.0
    assert result["spectral_mean_700"] == 30.0
    assert result["spectral_std_540"] == 0.0
    assert sum(name.startswith("spectral_mean_") for name in result) == 31
    assert sum(name.startswith("spectral_std_") for name in result) == 31


def test_roi_changes_band_statistics(cube, roi):
    cube[:2, :2, 14] = 100.0
    result = extract_spectral_features(cube, mask=roi)
    assert result.features["spectral_mean_540"] == 100.0
    assert result.features["spectral_std_540"] == 0.0


def test_invalid_and_empty_masks_are_rejected(cube):
    with pytest.raises(ValueError, match="dimensions"):
        extract_spectral_features(cube, mask=np.ones((3, 5), dtype=bool))
    with pytest.raises(ValueError, match="shape"):
        extract_spectral_features(cube, mask=np.ones((4, 5, 1), dtype=bool))
    with pytest.raises(ValueError, match="at least one"):
        extract_spectral_features(cube, mask=np.zeros((4, 5), dtype=bool))
    with pytest.raises(ValueError, match="NaN"):
        extract_spectral_features(cube, mask=np.full((4, 5), np.nan))


def test_known_ratio_and_roi_ratio(cube, roi):
    cube[:, :, 14] = 10.0
    cube[:, :, 25] = 2.0
    cube[:2, :2, 14] = 6.0
    result = extract_spectral_features(cube, mask=roi).features
    assert result["ratio_540_650"] == pytest.approx(3.0)


def test_zero_ratio_denominator_returns_nan_and_warning(cube):
    cube[:, :, 25] = 0.0
    result = extract_spectral_features(cube)
    assert np.isnan(result.features["ratio_540_650"])
    assert any("ratio_540_650" in warning for warning in result.warnings)
    assert not any(np.isinf(value) for value in result.features.values())


def test_differences_preserve_sign_and_roi_value(cube, roi):
    cube[:, :, 14] = 8.0
    cube[:, :, 15] = 10.0
    cube[:2, :2, 14] = 12.0
    cube[:2, :2, 15] = 7.0
    assert extract_spectral_features(cube).features["difference_540_550"] == pytest.approx(-0.6)
    assert extract_spectral_features(cube, mask=roi).features["difference_540_550"] == 5.0


def test_slopes_use_actual_wavelength_spacing(cube):
    cube[:, :, 0] = 1.0
    cube[:, :, 10] = 21.0
    cube[:, :, 20] = 11.0
    cube[:, :, 30] = 11.0
    features = extract_spectral_features(cube).features
    assert features["slope_400_500"] == pytest.approx(0.2)
    assert features["slope_500_600"] == pytest.approx(-0.1)
    assert features["slope_600_700"] == pytest.approx(0.0)
    assert features["slope_400_700"] == pytest.approx(1 / 30)


def test_regional_statistics(cube, roi):
    selected = cube[roi]
    features = extract_spectral_features(cube, mask=roi).features
    assert features["regional_spectral_mean"] == pytest.approx(selected.mean())
    assert features["regional_spectral_std"] == pytest.approx(selected.std())
    assert features["regional_spectral_median"] == pytest.approx(np.median(selected))
    assert features["regional_spectral_min"] == 0.0
    assert features["regional_spectral_max"] == 30.0


def test_signature_is_index_aligned_regional_mean(cube, roi):
    cube[:2, :2, :] += 5.0
    result = extract_spectral_features(cube, mask=roi)
    assert result.spectral_signature.shape == (31,)
    assert np.array_equal(result.spectral_signature, cube[roi].mean(axis=0))
    assert result.wavelengths_nm[0] == 400
    assert result.wavelengths_nm[-1] == 700


def test_investigational_proxies_exist_and_are_finite(cube):
    cube += 1.0
    features = extract_spectral_features(cube).features
    assert np.isfinite(features["vascular_related_spectral_proxy"])
    assert np.isfinite(features["pigmentation_related_spectral_proxy"])


def test_no_unsupported_water_or_structural_features(cube):
    features = extract_spectral_features(cube).features
    forbidden = ("water", "hydration", "collagen", "structural", "tissue")
    assert not any(token in name for name in features for token in forbidden)


def test_custom_wavelengths_preserve_order_and_mark_unavailable_fixed_features(cube):
    custom = np.arange(401, 432, dtype=float)
    result = extract_spectral_features(cube, wavelengths_nm=custom)
    assert np.array_equal(result.wavelengths_nm, custom)
    assert result.features["spectral_mean_401"] == 0.0
    assert np.isnan(result.features["ratio_540_650"])
    assert any("unavailable" in warning for warning in result.warnings)


def test_result_is_deterministic_and_groups_cover_features(cube, roi):
    first = extract_spectral_features(cube, mask=roi)
    second = extract_spectral_features(cube, mask=roi)
    assert first.features == second.features
    assert set().union(*map(set, first.feature_groups.values())) == set(first.features)
    assert all(isinstance(value, float) for value in first.features.values())

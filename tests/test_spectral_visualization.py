import numpy as np
import pytest

from spectraderm.spectral.visualization import (
    HYPERSKIN_VIS_WAVELENGTHS,
    compare_reconstruction,
    extract_region_spectrum,
    get_band,
    normalize_band,
    spectral_to_false_color,
    validate_spectral_cube,
    wavelength_to_band_index,
)


@pytest.fixture
def spectral_cube():
    rng = np.random.default_rng(42)
    return rng.random((32, 32, 31), dtype=np.float32)


def test_wavelengths_are_31_bands():
    assert len(HYPERSKIN_VIS_WAVELENGTHS) == 31
    assert HYPERSKIN_VIS_WAVELENGTHS[0] == 400
    assert HYPERSKIN_VIS_WAVELENGTHS[-1] == 700


def test_validate_valid_cube(spectral_cube):
    validate_spectral_cube(spectral_cube)


def test_invalid_cube_band_count():
    cube = np.zeros((32, 32, 33), dtype=np.float32)

    with pytest.raises(ValueError):
        validate_spectral_cube(cube)


def test_invalid_cube_nan():
    cube = np.zeros((32, 32, 31), dtype=np.float32)
    cube[0, 0, 0] = np.nan

    with pytest.raises(ValueError):
        validate_spectral_cube(cube)


def test_wavelength_to_band_index():
    assert wavelength_to_band_index(400) == 0
    assert wavelength_to_band_index(550) == 15
    assert wavelength_to_band_index(700) == 30


def test_invalid_wavelength():
    with pytest.raises(ValueError):
        wavelength_to_band_index(800)


def test_get_band(spectral_cube):
    band = get_band(spectral_cube, 550)

    assert band.shape == (32, 32)
    assert np.isfinite(band).all()


def test_normalize_band():
    band = np.array(
        [[0.0, 1.0], [2.0, 3.0]],
        dtype=np.float32,
    )

    normalized = normalize_band(band)

    assert normalized.min() == 0.0
    assert normalized.max() == 1.0


def test_false_color_output(spectral_cube):
    false_color = spectral_to_false_color(spectral_cube)

    assert false_color.shape == (32, 32, 3)
    assert false_color.dtype == np.float32
    assert np.isfinite(false_color).all()
    assert false_color.min() >= 0
    assert false_color.max() <= 1


def test_region_spectrum(spectral_cube):
    mask = np.zeros((32, 32), dtype=bool)
    mask[10:20, 10:20] = True

    spectrum = extract_region_spectrum(
        spectral_cube,
        mask,
    )

    assert spectrum.shape == (31,)
    assert np.isfinite(spectrum).all()


def test_empty_region_rejected(spectral_cube):
    mask = np.zeros((32, 32), dtype=bool)

    with pytest.raises(ValueError):
        extract_region_spectrum(
            spectral_cube,
            mask,
        )


def test_ground_truth_comparison(spectral_cube):
    prediction = spectral_cube + 0.01

    result = compare_reconstruction(
        spectral_cube,
        prediction,
    )

    assert result["absolute_error"].shape == spectral_cube.shape
    assert result["mae"] > 0
    assert result["rmse"] > 0


def test_comparison_shape_mismatch(spectral_cube):
    prediction = np.zeros((16, 16, 31), dtype=np.float32)

    with pytest.raises(ValueError):
        compare_reconstruction(
            spectral_cube,
            prediction,
        )
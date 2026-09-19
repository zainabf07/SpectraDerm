"""Conventional features from AI-estimated 31-band VIS spectral cubes.

This module operates on reconstructed spectral information, not calibrated
spectral absorption or direct hyperspectral measurements.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np


HYPERSKIN_VIS_WAVELENGTHS = np.arange(400, 701, 10, dtype=np.int32)
_EPSILON = 1e-8
_RATIO_PAIRS = ((540, 650), (550, 650), (570, 650), (580, 650), (600, 650), (650, 700))
_DIFFERENCE_PAIRS = ((540, 550), (550, 570), (570, 600), (600, 650), (650, 700))
_SLOPE_PAIRS = ((400, 500), (500, 600), (600, 700), (400, 700))


@dataclass(frozen=True)
class SpectralFeatureResult:
    """Flat spectral features, regional mean signature, and extraction metadata."""

    features: dict[str, float]
    feature_groups: dict[str, list[str]]
    spectral_signature: np.ndarray
    wavelengths_nm: np.ndarray
    roi_pixel_count: int
    mask_fraction: float
    cube_shape: tuple[int, int, int]
    warnings: list[str]


def _validate_cube(spectral_cube: np.ndarray) -> np.ndarray:
    if not isinstance(spectral_cube, np.ndarray):
        raise TypeError("spectral_cube must be a NumPy array")
    if spectral_cube.ndim != 3:
        raise ValueError("spectral_cube must have shape (H, W, 31)")
    if spectral_cube.shape[2] != 31:
        raise ValueError("spectral_cube must have exactly 31 spectral bands")
    if spectral_cube.shape[0] == 0 or spectral_cube.shape[1] == 0:
        raise ValueError("spectral_cube spatial dimensions must be non-empty")
    if not np.issubdtype(spectral_cube.dtype, np.number):
        raise TypeError("spectral_cube must have a numeric dtype")
    if not np.isfinite(spectral_cube).all():
        raise ValueError("spectral_cube contains NaN or infinite values")
    return spectral_cube.astype(np.float64, copy=False)


def _validate_wavelengths(wavelengths_nm: Optional[np.ndarray]) -> np.ndarray:
    if wavelengths_nm is None:
        return HYPERSKIN_VIS_WAVELENGTHS.copy()
    if not isinstance(wavelengths_nm, np.ndarray):
        raise TypeError("wavelengths_nm must be a NumPy array")
    if wavelengths_nm.ndim != 1 or wavelengths_nm.size != 31:
        raise ValueError("wavelengths_nm must be a one-dimensional array with exactly 31 values")
    if not np.issubdtype(wavelengths_nm.dtype, np.number):
        raise TypeError("wavelengths_nm must have a numeric dtype")
    if not np.isfinite(wavelengths_nm).all():
        raise ValueError("wavelengths_nm contains NaN or infinite values")
    values = wavelengths_nm.astype(np.float64, copy=True)
    if not np.all(np.diff(values) > 0):
        raise ValueError("wavelengths_nm must be strictly increasing without duplicates")
    return values


def _validate_mask(mask: Optional[np.ndarray], cube_shape: tuple[int, int, int]) -> np.ndarray:
    height, width, _ = cube_shape
    if mask is None:
        return np.ones((height, width), dtype=bool)
    if not isinstance(mask, np.ndarray):
        raise TypeError("mask must be a NumPy array")
    if mask.ndim != 2:
        raise ValueError("mask must have shape (H, W)")
    if mask.shape != (height, width):
        raise ValueError("mask dimensions must match spectral_cube spatial dimensions")
    if not (np.issubdtype(mask.dtype, np.number) or mask.dtype == np.bool_):
        raise TypeError("mask must have a numeric or boolean dtype")
    if np.issubdtype(mask.dtype, np.floating) and not np.isfinite(mask).all():
        raise ValueError("mask contains NaN or infinite values")
    roi = mask.astype(bool)
    if not roi.any():
        raise ValueError("mask must include at least one ROI pixel")
    return roi


def _label(wavelength_nm: float) -> str:
    return str(int(wavelength_nm)) if float(wavelength_nm).is_integer() else f"{wavelength_nm:g}".replace(".", "_")


def _index_for(wavelengths_nm: np.ndarray, wavelength_nm: int) -> Optional[int]:
    matches = np.flatnonzero(wavelengths_nm == wavelength_nm)
    return int(matches[0]) if matches.size else None


def _undefined_feature(features: dict[str, float], warnings: list[str], name: str, reason: str) -> None:
    features[name] = float("nan")
    warnings.append(f"{name} is undefined: {reason}")


def extract_spectral_features(
    spectral_cube: np.ndarray,
    wavelengths_nm: Optional[np.ndarray] = None,
    mask: Optional[np.ndarray] = None,
) -> SpectralFeatureResult:
    """Extract deterministic features from a H x W x 31 estimated VIS cube.

    Custom wavelengths must be supplied in their existing strictly increasing
    order. Fixed 540--700 nm comparison features are NaN with a warning when a
    requested wavelength is absent; no wavelength is interpolated or invented.
    """
    cube = _validate_cube(spectral_cube)
    wavelengths = _validate_wavelengths(wavelengths_nm)
    roi = _validate_mask(mask, cube.shape)
    selected = cube[roi]
    signature = selected.mean(axis=0)
    band_std = selected.std(axis=0)
    warnings: list[str] = []
    features: dict[str, float] = {}

    band_intensity_names: list[str] = []
    for index, wavelength in enumerate(wavelengths):
        label = _label(wavelength)
        mean_name, std_name = f"spectral_mean_{label}", f"spectral_std_{label}"
        features[mean_name] = float(signature[index])
        features[std_name] = float(band_std[index])
        band_intensity_names.extend((mean_name, std_name))

    ratio_names: list[str] = []
    difference_names: list[str] = []
    slope_names: list[str] = []
    for numerator_nm, denominator_nm in _RATIO_PAIRS:
        name = f"ratio_{numerator_nm}_{denominator_nm}"
        ratio_names.append(name)
        numerator_index = _index_for(wavelengths, numerator_nm)
        denominator_index = _index_for(wavelengths, denominator_nm)
        if numerator_index is None or denominator_index is None:
            _undefined_feature(features, warnings, name, "a requested wavelength is unavailable")
        elif abs(signature[denominator_index]) <= _EPSILON:
            _undefined_feature(features, warnings, name, "the denominator mean is zero or near zero")
        else:
            features[name] = float(signature[numerator_index] / signature[denominator_index])

    for first_nm, second_nm in _DIFFERENCE_PAIRS:
        name = f"difference_{first_nm}_{second_nm}"
        difference_names.append(name)
        first_index = _index_for(wavelengths, first_nm)
        second_index = _index_for(wavelengths, second_nm)
        if first_index is None or second_index is None:
            _undefined_feature(features, warnings, name, "a requested wavelength is unavailable")
        else:
            features[name] = float(signature[first_index] - signature[second_index])

    for first_nm, second_nm in _SLOPE_PAIRS:
        name = f"slope_{first_nm}_{second_nm}"
        slope_names.append(name)
        first_index = _index_for(wavelengths, first_nm)
        second_index = _index_for(wavelengths, second_nm)
        if first_index is None or second_index is None:
            _undefined_feature(features, warnings, name, "a requested wavelength is unavailable")
        else:
            features[name] = float(
                (signature[second_index] - signature[first_index]) / (wavelengths[second_index] - wavelengths[first_index])
            )

    regional_names = [
        "regional_spectral_mean", "regional_spectral_std", "regional_spectral_median",
        "regional_spectral_min", "regional_spectral_max",
    ]
    features.update({
        "regional_spectral_mean": float(selected.mean()),
        "regional_spectral_std": float(selected.std()),
        "regional_spectral_median": float(np.median(selected)),
        "regional_spectral_min": float(selected.min()),
        "regional_spectral_max": float(selected.max()),
    })

    proxy_names = ["vascular_related_spectral_proxy", "pigmentation_related_spectral_proxy"]
    index_540, index_580 = _index_for(wavelengths, 540), _index_for(wavelengths, 580)
    if index_540 is None or index_580 is None:
        _undefined_feature(features, warnings, proxy_names[0], "540 nm or 580 nm is unavailable")
    elif abs(signature[index_540] + signature[index_580]) <= _EPSILON:
        _undefined_feature(features, warnings, proxy_names[0], "the 540 nm plus 580 nm denominator is zero or near zero")
    else:
        features[proxy_names[0]] = float(
            (signature[index_540] - signature[index_580]) / (signature[index_540] + signature[index_580])
        )

    index_540, index_650 = _index_for(wavelengths, 540), _index_for(wavelengths, 650)
    if index_540 is None or index_650 is None:
        _undefined_feature(features, warnings, proxy_names[1], "540 nm or 650 nm is unavailable")
    elif abs(signature[index_540]) <= _EPSILON:
        _undefined_feature(features, warnings, proxy_names[1], "the 540 nm denominator is zero or near zero")
    else:
        features[proxy_names[1]] = float(signature[index_650] / signature[index_540])

    return SpectralFeatureResult(
        features=features,
        feature_groups={
            "band_intensities": band_intensity_names,
            "spectral_ratios": ratio_names,
            "spectral_differences": difference_names,
            "spectral_slopes": slope_names,
            "regional_statistics": regional_names,
            "investigational_spectral_proxies": proxy_names,
        },
        spectral_signature=signature.copy(),
        wavelengths_nm=wavelengths.copy(),
        roi_pixel_count=int(roi.sum()),
        mask_fraction=float(roi.mean()),
        cube_shape=tuple(cube.shape),
        warnings=warnings,
    )

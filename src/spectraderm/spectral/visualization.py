from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


# Hyper-Skin VIS reconstruction:
# 31 bands from 400 nm to 700 nm in 10 nm steps.
HYPERSKIN_VIS_WAVELENGTHS = np.arange(400, 701, 10, dtype=np.int32)


@dataclass(frozen=True)
class SpectralVisualizationConfig:
    """Configuration for visualizing an estimated spectral cube."""

    wavelengths_nm: np.ndarray = field(
        default_factory=lambda: HYPERSKIN_VIS_WAVELENGTHS.copy()
    )


def validate_spectral_cube(spectral_cube: np.ndarray) -> None:
    """
    Validate an estimated spectral cube.

    Expected shape:
        (H, W, 31)

    Values are expected to be finite.
    """
    if not isinstance(spectral_cube, np.ndarray):
        raise TypeError("spectral_cube must be a NumPy array")

    if spectral_cube.ndim != 3:
        raise ValueError(
            f"spectral_cube must have 3 dimensions, "
            f"got {spectral_cube.ndim}"
        )

    if spectral_cube.shape[2] != 31:
        raise ValueError(
            f"Expected 31 spectral bands, "
            f"got {spectral_cube.shape[2]}"
        )

    if not np.isfinite(spectral_cube).all():
        raise ValueError(
            "spectral_cube contains NaN or infinite values"
        )


def wavelength_to_band_index(
    wavelength_nm: int,
    wavelengths_nm: np.ndarray = HYPERSKIN_VIS_WAVELENGTHS,
) -> int:
    """Return the spectral-band index for a wavelength."""
    matches = np.where(wavelengths_nm == wavelength_nm)[0]

    if len(matches) == 0:
        raise ValueError(
            f"Wavelength {wavelength_nm} nm is not available. "
            f"Available wavelengths: "
            f"{wavelengths_nm.tolist()}"
        )

    return int(matches[0])


def get_band(
    spectral_cube: np.ndarray,
    wavelength_nm: int,
) -> np.ndarray:
    """Extract one reconstructed spectral band."""
    validate_spectral_cube(spectral_cube)

    index = wavelength_to_band_index(wavelength_nm)

    return spectral_cube[:, :, index]


def normalize_band(band: np.ndarray) -> np.ndarray:
    """
    Normalize a spectral band to [0, 1] for visualization.

    This is display normalization only. It does not alter
    the original reconstructed spectral data.
    """
    band = np.asarray(band, dtype=np.float32)

    if not np.isfinite(band).all():
        raise ValueError("band contains NaN or infinite values")

    minimum = float(band.min())
    maximum = float(band.max())

    if maximum <= minimum:
        return np.zeros_like(band, dtype=np.float32)

    normalized = (band - minimum) / (maximum - minimum)

    return normalized.astype(np.float32)


def spectral_to_false_color(
    spectral_cube: np.ndarray,
    red_nm: int = 650,
    green_nm: int = 550,
    blue_nm: int = 450,
) -> np.ndarray:
    """
    Create a false-color visualization from selected
    reconstructed VIS bands.

    Default:
        R = 650 nm
        G = 550 nm
        B = 450 nm

    This is a visualization of AI-estimated spectral information.
    It is NOT an actual multispectral/NIR camera image.
    """
    validate_spectral_cube(spectral_cube)

    red = normalize_band(get_band(spectral_cube, red_nm))
    green = normalize_band(get_band(spectral_cube, green_nm))
    blue = normalize_band(get_band(spectral_cube, blue_nm))

    return np.stack([red, green, blue], axis=-1)


def extract_region_spectrum(
    spectral_cube: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    """
    Calculate the mean reconstructed spectrum inside a selected region.

    Parameters
    ----------
    spectral_cube:
        Estimated spectral cube with shape (H, W, 31).

    mask:
        Boolean region mask with shape (H, W).

    Returns
    -------
    np.ndarray
        Mean spectrum with shape (31,).
    """
    validate_spectral_cube(spectral_cube)

    if not isinstance(mask, np.ndarray):
        raise TypeError("mask must be a NumPy array")

    if mask.dtype != np.bool_:
        raise TypeError("mask must have boolean dtype")

    if mask.shape != spectral_cube.shape[:2]:
        raise ValueError(
            "mask shape must match the spatial dimensions "
            "of spectral_cube"
        )

    if not np.any(mask):
        raise ValueError("mask does not contain any selected pixels")

    selected_pixels = spectral_cube[mask]

    return selected_pixels.mean(axis=0).astype(np.float32)


def compare_reconstruction(
    ground_truth: np.ndarray,
    prediction: np.ndarray,
) -> dict[str, np.ndarray | float]:
    """
    Compare reconstructed spectral data with ground truth.

    Intended for datasets such as Hyper-Skin where measured
    spectral ground truth is available.

    Returns display/analysis metrics and an absolute-error map.
    """
    if not isinstance(ground_truth, np.ndarray):
        raise TypeError("ground_truth must be a NumPy array")

    if not isinstance(prediction, np.ndarray):
        raise TypeError("prediction must be a NumPy array")

    if ground_truth.shape != prediction.shape:
        raise ValueError(
            "ground_truth and prediction must have identical shapes"
        )

    if ground_truth.ndim != 3 or ground_truth.shape[2] != 31:
        raise ValueError(
            "Expected spectral arrays with shape (H, W, 31)"
        )

    if not np.isfinite(ground_truth).all():
        raise ValueError("ground_truth contains invalid values")

    if not np.isfinite(prediction).all():
        raise ValueError("prediction contains invalid values")

    error = np.abs(ground_truth - prediction)

    mae = float(np.mean(error))
    rmse = float(
        np.sqrt(np.mean((ground_truth - prediction) ** 2))
    )

    return {
        "absolute_error": error.astype(np.float32),
        "mae": mae,
        "rmse": rmse,
    }
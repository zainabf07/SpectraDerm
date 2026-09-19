from pathlib import Path

import numpy as np
import pytest

from spectraderm.spectral.reconstruction import (
    SpectralReconstructionConfig,
    reconstruct_spectral,
    validate_rgb_input,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = (
    PROJECT_ROOT
    / "models"
    / "mstpp_hyperskin_vis_best_10pairs.pth"
)


def test_rgb_validation_accepts_valid_input():
    rgb = np.zeros((64, 64, 3), dtype=np.float32)

    validate_rgb_input(rgb)


def test_mstpp_checkpoint_exists():
    assert CHECKPOINT.exists()


def test_reconstruction_requires_checkpoint():
    rgb = np.zeros((64, 64, 3), dtype=np.float32)

    config = SpectralReconstructionConfig(
        input_channels=3,
        output_bands=31,
    )

    with pytest.raises(ValueError, match="checkpoint_path"):
        reconstruct_spectral(rgb, config)


def test_reconstruction_rejects_33_bands():
    rgb = np.zeros((32, 32, 3), dtype=np.float32)

    config = SpectralReconstructionConfig(
        input_channels=3,
        output_bands=33,
        checkpoint_path=CHECKPOINT,
    )

    with pytest.raises(
        ValueError,
        match="exactly 31 bands",
    ):
        reconstruct_spectral(rgb, config)


def test_invalid_rgb_shape_is_rejected():
    rgb = np.zeros((64, 64), dtype=np.float32)

    with pytest.raises(ValueError):
        validate_rgb_input(rgb)


def test_invalid_rgb_range_is_rejected():
    rgb = np.ones((64, 64, 3), dtype=np.float32) * 2

    with pytest.raises(ValueError):
        validate_rgb_input(rgb)


def test_nan_rgb_is_rejected():
    rgb = np.zeros((64, 64, 3), dtype=np.float32)
    rgb[0, 0, 0] = np.nan

    with pytest.raises(ValueError):
        validate_rgb_input(rgb)


def test_invalid_output_bands_are_rejected():
    rgb = np.zeros((32, 32, 3), dtype=np.float32)

    config = SpectralReconstructionConfig(
        input_channels=3,
        output_bands=0,
    )

    with pytest.raises(ValueError):
        reconstruct_spectral(rgb, config)
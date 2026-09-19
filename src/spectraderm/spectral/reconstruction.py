from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SpectralReconstructionConfig:
    input_channels: int = 3
    output_bands: int = 31
    model_name: str = "mstpp_hyperskin_vis"
    checkpoint_path: str | Path | None = None
    device: str | None = None


@dataclass(frozen=True)
class SpectralReconstructionResult:
    spectrum: np.ndarray
    estimated: bool
    output_bands: int
    model_name: str


def validate_rgb_input(rgb: np.ndarray) -> None:
    """Validate an RGB image expected by the reconstruction model."""

    if not isinstance(rgb, np.ndarray):
        raise TypeError("rgb must be a NumPy array")

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("rgb must have shape (H, W, 3)")

    if not np.isfinite(rgb).all():
        raise ValueError("rgb contains NaN or infinite values")

    if rgb.min() < 0 or rgb.max() > 1:
        raise ValueError("rgb values must be in the range [0, 1]")


def reconstruct_spectral(
    rgb: np.ndarray,
    config: SpectralReconstructionConfig,
) -> SpectralReconstructionResult:
    """
    Reconstruct a 31-band VIS spectral image from an RGB image.

    Input:
        RGB NumPy array with shape (H, W, 3), values in [0, 1].

    Output:
        Estimated VIS spectral image with shape (H, W, 31).

    Important:
        The returned spectrum is AI-estimated, not directly measured.
    """

    validate_rgb_input(rgb)

    if config.input_channels != 3:
        raise ValueError("RGB input requires input_channels=3")

    if config.output_bands != 31:
        raise ValueError(
            "The Hyper-Skin VIS MST++ model produces exactly 31 bands"
        )

    if config.checkpoint_path is None:
        raise ValueError(
            "checkpoint_path is required for MST++ spectral reconstruction"
        )

    # Import lazily so the rest of SpectraDerm can still be imported
    # in environments where PyTorch is not installed.
    from .mstpp import MSTPlusPlusModel

    model = MSTPlusPlusModel(
        checkpoint_path=config.checkpoint_path,
        device=config.device,
    )

    # NumPy HWC -> PyTorch BCHW
    tensor = np.transpose(rgb, (2, 0, 1))[None, ...]

    import torch

    rgb_tensor = torch.from_numpy(
        tensor.astype(np.float32, copy=False)
    )

    predicted = model(rgb_tensor)

    # PyTorch BCHW -> NumPy HWC
    spectrum = (
        predicted.detach()
        .cpu()
        .numpy()[0]
        .transpose(1, 2, 0)
        .astype(np.float32)
    )

    return SpectralReconstructionResult(
        spectrum=spectrum,
        estimated=True,
        output_bands=31,
        model_name=config.model_name,
    )
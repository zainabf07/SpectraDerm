from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = (
    PROJECT_ROOT
    / "models"
    / "mstpp_hyperskin_vis_best_10pairs.pth"
)


def test_mstpp_checkpoint_exists():
    """The trained Hyper-Skin MST++ checkpoint must exist."""
    assert CHECKPOINT.exists(), (
        f"MST++ checkpoint not found: {CHECKPOINT}"
    )


def test_mstpp_rgb_to_vis_integration():
    """
    Verify the complete RGB -> 31-band VIS reconstruction interface.

    This test requires PyTorch because the actual MST++ model is used.
    """

    torch = pytest.importorskip("torch")

    from spectraderm.spectral.reconstruction import (
        SpectralReconstructionConfig,
        reconstruct_spectral,
    )

    # Small synthetic RGB image for interface testing.
    # Values are normalized to [0, 1].
    rgb = np.random.default_rng(42).random(
        (128, 128, 3),
        dtype=np.float32,
    )

    config = SpectralReconstructionConfig(
        input_channels=3,
        output_bands=31,
        model_name="mstpp_hyperskin_vis",
        checkpoint_path=CHECKPOINT,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )

    result = reconstruct_spectral(rgb, config)

    # Output must be H x W x 31.
    assert result.spectrum.shape == (128, 128, 31)

    # Output should be float32.
    assert result.spectrum.dtype == np.float32

    # Output must contain finite values.
    assert np.isfinite(result.spectrum).all()

    # This is an AI-estimated spectrum.
    assert result.estimated is True

    # Metadata should match the model.
    assert result.output_bands == 31
    assert result.model_name == "mstpp_hyperskin_vis"
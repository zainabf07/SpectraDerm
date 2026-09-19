from __future__ import annotations

from pathlib import Path
import sys

import torch
import torch.nn as nn


class MSTPlusPlusModel(nn.Module):
    """
    SpectraDerm wrapper for the official Hyper-Skin MST++ architecture.

    RGB input:
        [B, 3, H, W]

    VIS output:
        [B, 31, H, W]
    """

    def __init__(
        self,
        checkpoint_path: str | Path,
        device: str | torch.device | None = None,
    ) -> None:
        super().__init__()

        self.checkpoint_path = Path(checkpoint_path)

        if not self.checkpoint_path.exists():
            raise FileNotFoundError(
                f"MST++ checkpoint not found: "
                f"{self.checkpoint_path}"
            )

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = torch.device(device)

        # Official Hyper-Skin MST++ implementation is kept outside
        # the SpectraDerm source tree.
        official_reconstruction_dir = (
            Path(__file__).resolve().parents[3]
            / "external"
            / "Hyper-Skin-2023"
            / "hsiData"
            / "models"
            / "reconstruction"
        )

        mst_file = official_reconstruction_dir / "MST_Plus_Plus.py"

        if not mst_file.exists():
            raise FileNotFoundError(
                "Official MST++ implementation was not found.\n"
                f"Expected: {mst_file}\n\n"
                "Place the official Hyper-Skin MST++ source under "
                "external/Hyper-Skin-2023/."
            )

        # Make the official reconstruction directory importable.
        sys.path.insert(0, str(official_reconstruction_dir))

        try:
            import MST_Plus_Plus
        except ImportError as exc:
            raise ImportError(
                "Could not import the official MST++ implementation."
            ) from exc

        # Same architecture used during our Hyper-Skin training.
        self.model = MST_Plus_Plus.MST_Plus_Plus(
            in_channels=3,
            out_channels=31,
            n_feat=31,
            stage=3,
        )

        checkpoint = torch.load(
            self.checkpoint_path,
            map_location=self.device,
            weights_only=False,
        )

        self.model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        self.model.to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def forward(self, rgb: torch.Tensor) -> torch.Tensor:
        """
        Reconstruct 31-band VIS from RGB.

        Args:
            rgb: Tensor [B, 3, H, W], normalized to [0, 1].

        Returns:
            Tensor [B, 31, H, W].
        """

        if not isinstance(rgb, torch.Tensor):
            raise TypeError("rgb must be a torch.Tensor")

        if rgb.ndim != 4:
            raise ValueError(
                f"Expected RGB tensor [B,3,H,W], "
                f"got shape {tuple(rgb.shape)}"
            )

        if rgb.shape[1] != 3:
            raise ValueError(
                f"Expected 3 RGB channels, "
                f"got {rgb.shape[1]}"
            )

        if not torch.isfinite(rgb).all():
            raise ValueError(
                "RGB input contains NaN or infinite values."
            )

        if torch.any(rgb < 0) or torch.any(rgb > 1):
            raise ValueError(
                "RGB input must be normalized to [0, 1]."
            )

        rgb = rgb.to(self.device)

        return self.model(rgb)
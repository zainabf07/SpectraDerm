import torch
from torch import nn


class RGBToSpectralCNN(nn.Module):
    """Small baseline RGB-to-spectral reconstruction network."""

    def __init__(self, output_bands: int = 31):
        super().__init__()

        if output_bands <= 0:
            raise ValueError("output_bands must be positive")

        self.output_bands = output_bands

        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
        )

        self.decoder = nn.Sequential(
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, output_bands, kernel_size=1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 4 or x.shape[1] != 3:
            raise ValueError("input must have shape (N, 3, H, W)")

        return self.decoder(self.encoder(x))
    
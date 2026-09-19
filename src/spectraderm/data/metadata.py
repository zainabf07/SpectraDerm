"""Dataset metadata contracts established during SpectraDerm Phase 1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetMetadata:
    """Stable dataset facts used to validate data-loading contracts."""

    identifier: str
    spectral_bands: int
    spectral_variable: str
    rgb_channels: int = 3
    rendered_rgb_reference: bool = False
    spectral_wavelengths_known: bool = False


HYPERSKIN = DatasetMetadata(
    identifier="hyper_skin",
    spectral_bands=31,
    spectral_variable="cube",
)

UMINHO_HSFD = DatasetMetadata(
    identifier="uminho_hsfd",
    spectral_bands=33,
    spectral_variable="datao",
    rendered_rgb_reference=True,
    spectral_wavelengths_known=True,
)

"""Phase 1 RGB and measured spectral data loaders."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
from PIL import Image
from scipy.io import loadmat

from spectraderm.data.metadata import HYPERSKIN, UMINHO_HSFD


def load_rgb(path: Path) -> np.ndarray:
    """Load an RGB image as a uint8 H x W x 3 array."""
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError(f"Expected RGB image with 3 channels, got {rgb.shape}")
    return rgb


def load_hyperskin_vis(path: Path) -> np.ndarray:
    """Load Hyper-Skin VIS HDF5 data and return H x W x 31 band ordering."""
    with h5py.File(path, "r") as file:
        if HYPERSKIN.spectral_variable not in file:
            raise KeyError(f"Missing '{HYPERSKIN.spectral_variable}' in {path}")
        spectral = file[HYPERSKIN.spectral_variable][:]
    if spectral.ndim != 3:
        raise ValueError(f"Expected a 3D Hyper-Skin VIS cube, got {spectral.shape}")
    spectral = np.transpose(spectral, (1, 2, 0)).astype(np.float32)
    if spectral.shape[-1] != HYPERSKIN.spectral_bands:
        raise ValueError(f"Expected {HYPERSKIN.spectral_bands} VIS bands, got {spectral.shape[-1]}")
    return spectral


def load_uminho_reflectance(path: Path) -> np.ndarray:
    """Load UMINHO measured reflectance without clipping or rescaling values."""
    values = loadmat(path, variable_names=[UMINHO_HSFD.spectral_variable])
    if UMINHO_HSFD.spectral_variable not in values:
        raise KeyError(f"Missing '{UMINHO_HSFD.spectral_variable}' in {path}")
    spectral = np.asarray(values[UMINHO_HSFD.spectral_variable], dtype=np.float32)
    if spectral.ndim != 3 or spectral.shape[-1] != UMINHO_HSFD.spectral_bands:
        raise ValueError(f"Expected H x W x {UMINHO_HSFD.spectral_bands}, got {spectral.shape}")
    return spectral

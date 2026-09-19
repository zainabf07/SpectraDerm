"""Offline array-contract tests for Phase 1 preprocessing."""

import unittest

import numpy as np

from spectraderm.preprocessing.normalization import normalize_rgb, preserve_spectral_scale
from spectraderm.preprocessing.quality import validate_pair
from spectraderm.preprocessing.transforms import (
    horizontal_flip_pair,
    resize_pair_opencv,
    resize_pair_pillow,
)


class PreprocessingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rgb_uint8 = np.zeros((4, 6, 3), dtype=np.uint8)
        self.rgb_uint8[:, 0, :] = 255

    def test_rgb_normalization_contract(self) -> None:
        rgb = normalize_rgb(self.rgb_uint8)
        self.assertEqual(rgb.dtype, np.float32)
        self.assertEqual(rgb.shape, (4, 6, 3))
        self.assertEqual(float(rgb.min()), 0.0)
        self.assertEqual(float(rgb.max()), 1.0)

    def test_spectral_scale_is_preserved(self) -> None:
        spectral = preserve_spectral_scale(np.full((4, 6, 33), 1.25, dtype=np.float64))
        self.assertEqual(spectral.dtype, np.float32)
        self.assertEqual(float(spectral.max()), 1.25)

    def test_pair_validation_rejects_nonfinite_values(self) -> None:
        rgb = normalize_rgb(self.rgb_uint8)
        spectral = np.zeros((4, 6, 31), dtype=np.float32)
        spectral[0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "NaN or Inf"):
            validate_pair(rgb, spectral, expected_bands=31)

    def test_paired_flip_preserves_correspondence(self) -> None:
        rgb = normalize_rgb(self.rgb_uint8)
        spectral = np.repeat(rgb[:, :, :1], 31, axis=2).astype(np.float32)
        flipped_rgb, flipped_spectral = horizontal_flip_pair(rgb, spectral)
        np.testing.assert_array_equal(flipped_rgb[:, :, 0], flipped_spectral[:, :, 0])

    def test_resize_preserves_output_contracts(self) -> None:
        rgb = normalize_rgb(self.rgb_uint8)
        hyper_vis = np.full((4, 6, 31), 1.25, dtype=np.float32)
        uminho_reflectance = np.full((4, 6, 33), 1.25, dtype=np.float32)
        hyper_rgb, hyper_vis = resize_pair_opencv(rgb, hyper_vis)
        uminho_rgb, uminho_reflectance = resize_pair_pillow(rgb, uminho_reflectance)
        self.assertEqual(hyper_rgb.shape, (256, 256, 3))
        self.assertEqual(hyper_vis.shape, (256, 256, 31))
        self.assertEqual(uminho_rgb.shape, (256, 256, 3))
        self.assertEqual(uminho_reflectance.shape, (256, 256, 33))
        self.assertGreater(float(uminho_reflectance.max()), 1.0)

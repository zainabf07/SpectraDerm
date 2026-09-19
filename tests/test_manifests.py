"""Tests for committed Phase 1 manifest metadata."""

from pathlib import Path
import unittest

from spectraderm.data.manifests import (
    HYPERSKIN_COLUMNS,
    UMINHO_COLUMNS,
    load_manifest,
    validate_hyperskin_manifest,
    validate_uminho_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_hyperskin_manifest_contract(self) -> None:
        manifest = load_manifest(PROJECT_ROOT / "data/manifests/hyperskin_manifest.csv")
        self.assertEqual(tuple(manifest.columns), HYPERSKIN_COLUMNS)
        self.assertEqual(len(manifest), 306)
        validate_hyperskin_manifest(manifest)

    def test_uminho_manifest_contract_and_split_counts(self) -> None:
        manifest = load_manifest(PROJECT_ROOT / "data/manifests/uminho_hsfd_manifest.csv")
        self.assertEqual(tuple(manifest.columns), UMINHO_COLUMNS)
        self.assertEqual(len(manifest), 29)
        self.assertEqual(manifest["split"].value_counts().to_dict(), {"train": 20, "test": 5, "valid": 4})
        validate_uminho_manifest(manifest)

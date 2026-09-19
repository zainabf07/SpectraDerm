"""Subject-aware split integrity tests."""

from pathlib import Path
import unittest

from spectraderm.data.manifests import load_manifest
from spectraderm.preprocessing.splits import create_uminho_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SplitTests(unittest.TestCase):
    def test_uminho_split_is_reproducible_and_disjoint(self) -> None:
        manifest = load_manifest(PROJECT_ROOT / "data/manifests/uminho_hsfd_manifest.csv")
        regenerated = create_uminho_split(manifest.drop(columns="split"), seed=42)
        self.assertEqual(regenerated["split"].value_counts().to_dict(), {"train": 20, "test": 5, "valid": 4})
        self.assertEqual(regenerated["face_id"].nunique(), 29)
        for split in ("train", "valid", "test"):
            self.assertEqual(regenerated.loc[regenerated["split"] == split, "face_id"].duplicated().sum(), 0)

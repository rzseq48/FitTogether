from __future__ import annotations

import random
import unittest
from pathlib import Path

from scripts.ml.config import MLConfig, seed_everything


class TestMLConfig(unittest.TestCase):
    def test_paths_and_as_dict(self) -> None:
        cfg = MLConfig(data_dir=Path("data"), output_dir=Path("out"))
        payload = cfg.as_dict()

        self.assertEqual(cfg.model_path, Path("out/food_model.pth"))
        self.assertEqual(cfg.labels_path, Path("out/labels.json"))
        self.assertEqual(cfg.nutrition_path, Path("out/nutrition_map.json"))
        self.assertEqual(cfg.bundle_path, Path("out/model_bundle.pt"))

        self.assertEqual(payload["data_dir"], "data")
        self.assertEqual(payload["output_dir"], "out")
        self.assertIn("device", payload)

    def test_seed_everything_reproducibility(self) -> None:
        seed_everything(123)
        first = random.random()
        seed_everything(123)
        second = random.random()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

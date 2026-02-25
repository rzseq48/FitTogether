from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
import torch.nn as nn
from PIL import Image

from scripts.ml.infer import FoodPredictor


class _DummyModel(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = torch.tensor([[0.1, 2.0]], device=x.device)
        return logits.repeat(x.size(0), 1)


class TestFoodPredictor(unittest.TestCase):
    def test_predict_and_chatbot_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            image_path = tmp_path / "sample.jpg"
            Image.new("RGB", (24, 24), color=(12, 45, 78)).save(image_path)

            nutrition_path = tmp_path / "nutrition_map.json"
            nutrition_path.write_text(
                json.dumps(
                    {
                        "idli": {"calories": 58, "protein": 2, "carbs": 12, "fat": 1},
                        "dosa": {"calories": 165, "protein": 4, "carbs": 32, "fat": 4},
                        "unknown": {"calories": 250, "protein": 10, "carbs": 30, "fat": 10},
                    }
                ),
                encoding="utf-8",
            )

            def _to_tensor(_img):
                return torch.zeros((3, 224, 224), dtype=torch.float32)

            with (
                patch("scripts.ml.infer.build_model", return_value=_DummyModel()),
                patch("scripts.ml.infer.build_transforms", return_value=(_to_tensor, _to_tensor, _to_tensor)),
                patch.object(FoodPredictor, "_load_labels", return_value={"0": "idli", "1": "dosa"}),
                patch.object(FoodPredictor, "_load_checkpoint", return_value={"model_state": {}}),
            ):
                predictor = FoodPredictor(nutrition_path=nutrition_path, tta_passes=3)
                top = predictor.predict(str(image_path), top_k=1)[0]
                self.assertEqual(top["food"], "dosa")
                self.assertIn("nutrition", top)

                response = predictor.predict_for_chatbot(str(image_path))
                self.assertIn("Dosa", response)
                self.assertIn("Calories", response)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import torch
from PIL import Image

try:
    from .config import MLConfig
    from .data import build_transforms
    from .model import build_model
except ImportError:  # pragma: no cover
    from config import MLConfig
    from data import build_transforms
    from model import build_model


class FoodPredictor:

    def __init__(
        self,
        model_path: Optional[Path] = None,
        labels_path: Optional[Path] = None,
        nutrition_path: Optional[Path] = None,
        bundle_path: Optional[Path] = None,
        tta_passes: Optional[int] = None,
    ):
        cfg = MLConfig()
        self.device = cfg.device

        self.model_path = Path(model_path) if model_path else cfg.model_path
        self.labels_path = Path(labels_path) if labels_path else cfg.labels_path
        self.nutrition_path = Path(nutrition_path) if nutrition_path else cfg.nutrition_path
        self.bundle_path = Path(bundle_path) if bundle_path else cfg.bundle_path

        # Allow overriding TTA passes at load time; fall back to config.
        self.tta_passes = tta_passes if tta_passes is not None else cfg.tta_passes

        self.labels = self._load_labels()
        with self.nutrition_path.open("r", encoding="utf-8") as f:
            self.nutrition: Dict[str, dict] = json.load(f)

        self.model = build_model(cfg, num_classes=len(self.labels))
        checkpoint = self._load_checkpoint()
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.eval()
        self.model.to(self.device)

        _, self.eval_transform, self.tta_transform = build_transforms(cfg.image_size)
        print(
            f"FoodPredictor loaded — {len(self.labels)} classes, "
            f"TTA passes={self.tta_passes}"
        )

    # ── Loaders ───────────────────────────────────────────────────────────────

    def _load_labels(self) -> Dict[str, str]:
        if self.bundle_path.exists():
            bundle = torch.load(self.bundle_path, map_location="cpu")
            if "idx_to_label" in bundle:
                return {str(k): v for k, v in bundle["idx_to_label"].items()}
        with self.labels_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_checkpoint(self) -> dict:
        if self.bundle_path.exists():
            bundle = torch.load(self.bundle_path, map_location=self.device)
            if "model_state" in bundle:
                return bundle
        return torch.load(self.model_path, map_location=self.device)

    # ── Core inference ────────────────────────────────────────────────────────

    def _image_to_probs(self, img: Image.Image) -> torch.Tensor:
        """
        Returns averaged probability tensor over TTA passes.

        Pass 1:  deterministic centre-crop (eval_transform)
        Pass 2…N: random crop + random flip + slight colour jitter (tta_transform)

        Averaging multiple stochastic views of the same image reduces variance
        and consistently improves top-1 accuracy by ~1-2%.
        """
        tensors: List[torch.Tensor] = []

        # First pass: deterministic eval crop
        t = self.eval_transform(img).unsqueeze(0).to(self.device)
        tensors.append(t)

        # Additional TTA passes with random augmentation
        for _ in range(self.tta_passes - 1):
            t = self.tta_transform(img).unsqueeze(0).to(self.device)
            tensors.append(t)

        batch = torch.cat(tensors, dim=0)   # (tta_passes, C, H, W)
        with torch.no_grad():
            logits = self.model(batch)       # (tta_passes, num_classes)
            probs = torch.softmax(logits, dim=1)

        return probs.mean(dim=0)             # (num_classes,)

    # ── Public API ────────────────────────────────────────────────────────────

    def predict(self, image_path: str, top_k: int = 3) -> List[dict]:
        img = Image.open(image_path).convert("RGB")
        probs = self._image_to_probs(img)

        top_k = min(top_k, len(self.labels))
        top_probs, top_idxs = probs.topk(top_k)

        results = []
        for prob, idx in zip(top_probs, top_idxs):
            cls = self.labels[str(idx.item())]
            nutrition = self.nutrition.get(cls, self.nutrition.get("unknown", {}))
            if not nutrition:
                import warnings
                warnings.warn(
                    f"No nutrition data found for class '{cls}'; returning empty dict.",
                    stacklevel=2,
                )
            results.append(
                {
                    "food": cls,
                    "confidence": round(prob.item(), 3),
                    "nutrition": nutrition,
                    "recipe_query": f"Indian {cls} recipe",
                }
            )
        return results

    def predict_for_chatbot(self, image_path: str) -> str:
        results = self.predict(image_path, top_k=1)
        if not results:
            return "I couldn't identify this food item."

        top = results[0]
        nutrition = top["nutrition"]
        return (
            f"I think this is **{top['food'].replace('_', ' ').title()}** "
            f"({top['confidence'] * 100:.0f}% confident)\n\n"
            f"Nutrition (per serving):\n"
            f"- Calories: {nutrition.get('calories', '?')} kcal\n"
            f"- Protein: {nutrition.get('protein', '?')} g\n"
            f"- Carbs: {nutrition.get('carbs', '?')} g\n"
            f"- Fat: {nutrition.get('fat', '?')} g\n\n"
            f"Want a recipe? Search: \"{top['recipe_query']}\""
        )
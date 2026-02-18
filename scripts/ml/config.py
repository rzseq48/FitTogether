from __future__ import annotations

import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import torch


def _default_data_dir() -> Path:
    return Path(
        "/home/rohanseq48/Git_projects/prenatal-landing-page/FitTogether/test_images/Indian Food Images"
    )


def _default_output_dir() -> Path:
    return Path(
        "/home/rohanseq48/Git_projects/prenatal-landing-page/FitTogether/ml_model"
    )


@dataclass
class MLConfig:
    data_dir: Path = _default_data_dir()
    output_dir: Path = _default_output_dir()
    image_size: int = 224
    batch_size: int = 32
    epochs: int = 15
    lr: float = 1e-4
    weight_decay: float = 1e-4
    val_split: float = 0.15
    test_split: float = 0.10
    seed: int = 42
    num_workers: int = min(4, os.cpu_count() or 1)
    model_name: str = "efficientnet_b0"
    freeze_policy: str = "last_blocks"
    dropout_1: float = 0.4
    dropout_2: float = 0.2
    hidden_dim: int = 512
    patience: int = 5
    grad_clip_norm: float = 1.0
    label_smoothing: float = 0.05
    amp: bool = True
    detect_duplicates: bool = True

    @property
    def device(self) -> torch.device:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    @property
    def model_path(self) -> Path:
        return self.output_dir / "food_model.pth"

    @property
    def labels_path(self) -> Path:
        return self.output_dir / "labels.json"

    @property
    def nutrition_path(self) -> Path:
        return self.output_dir / "nutrition_map.json"

    @property
    def history_path(self) -> Path:
        return self.output_dir / "training_history.json"

    @property
    def metrics_summary_path(self) -> Path:
        return self.output_dir / "metrics_summary.json"

    @property
    def per_class_metrics_path(self) -> Path:
        return self.output_dir / "per_class_metrics.csv"

    @property
    def confusion_matrix_path(self) -> Path:
        return self.output_dir / "confusion_matrix.csv"

    @property
    def duplicates_log_path(self) -> Path:
        return self.output_dir / "duplicates_removed.json"

    @property
    def bundle_path(self) -> Path:
        return self.output_dir / "model_bundle.pt"

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["data_dir"] = str(self.data_dir)
        payload["output_dir"] = str(self.output_dir)
        payload["device"] = str(self.device)
        return payload


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass


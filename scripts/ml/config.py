from __future__ import annotations

import os
import random
from dataclasses import asdict, dataclass, field
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
    # ── Paths ────────────────────────────────────────────────────────────────
    data_dir: Path = field(default_factory=_default_data_dir)
    output_dir: Path = field(default_factory=_default_output_dir)

    # ── Model ────────────────────────────────────────────────────────────────
    model_name: str = "efficientnet_b0"
    image_size: int = 224
    hidden_dim: int = 512
    dropout_1: float = 0.4
    dropout_2: float = 0.2

    # ── Training ─────────────────────────────────────────────────────────────
    epochs: int = 20
    batch_size: int = 32
    lr: float = 3e-4           # slightly higher default; warmup keeps it safe
    weight_decay: float = 1e-4
    label_smoothing: float = 0.05
    grad_clip_norm: float = 1.0
    amp: bool = True

    # ── Scheduler / Optimiser ────────────────────────────────────────────────
    # "onecycle" | "cosine_warmup"
    scheduler: str = "cosine_warmup"
    # Fraction of total steps used for linear warmup (cosine_warmup only)
    warmup_fraction: float = 0.1
    # Min lr at end of cosine decay (cosine_warmup only)
    eta_min_fraction: float = 0.01   # eta_min = lr * eta_min_fraction

    # ── Freeze / Unfreeze ────────────────────────────────────────────────────
    # "all_backbone" | "last_blocks" | "full_finetune"
    freeze_policy: str = "last_blocks"
    # Epoch at which to unfreeze the full backbone (0 = never unfreeze).
    # When > 0, the model starts with freeze_policy applied, then at this
    # epoch all backbone weights become trainable (full fine-tune).
    unfreeze_epoch: int = 7

    # ── Augmentation ─────────────────────────────────────────────────────────
    # RandAugment magnitude (0 = disabled, recommended 7-9)
    randaugment_magnitude: int = 8
    # RandomErasing probability (0 = disabled)
    random_erasing_prob: float = 0.25
    # Mixup alpha (0 = disabled, recommended 0.2-0.4)
    mixup_alpha: float = 0.2

    # ── Sampling ─────────────────────────────────────────────────────────────
    # Use WeightedRandomSampler to up-sample minority classes during training
    weighted_sampling: bool = True

    # ── Early Stopping ───────────────────────────────────────────────────────
    patience: int = 6

    # ── Data splits ──────────────────────────────────────────────────────────
    val_split: float = 0.15
    test_split: float = 0.10
    seed: int = 42
    num_workers: int = min(4, os.cpu_count() or 1)
    detect_duplicates: bool = True

    # ── TTA (Test-Time Augmentation) ─────────────────────────────────────────
    # Number of augmented passes during inference (1 = disabled)
    tta_passes: int = 5

    # ─────────────────────────────────────────────────────────────────────────
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
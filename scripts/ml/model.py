from __future__ import annotations

import torch.nn as nn
from torchvision import models

try:
    from .config import MLConfig
except ImportError:  # pragma: no cover
    from config import MLConfig


def _enable_trainable_layers(model: nn.Module, freeze_policy: str) -> None:
    for p in model.parameters():
        p.requires_grad = True

    if freeze_policy == "full_finetune":
        return

    if freeze_policy == "all_backbone":
        for p in model.features.parameters():
            p.requires_grad = False
        return

    for p in model.parameters():
        p.requires_grad = False
    for name, p in model.named_parameters():
        if any(key in name for key in ["features.6", "features.7", "features.8", "classifier"]):
            p.requires_grad = True


def build_model(cfg: MLConfig, num_classes: int):
    if cfg.model_name != "efficientnet_b0":
        raise ValueError(f"Unsupported model_name '{cfg.model_name}', expected efficientnet_b0")

    model = models.efficientnet_b0(weights="IMAGENET1K_V1")
    _enable_trainable_layers(model, cfg.freeze_policy)

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=cfg.dropout_1),
        nn.Linear(in_features, cfg.hidden_dim),
        nn.ReLU(inplace=True),
        nn.Dropout(p=cfg.dropout_2),
        nn.Linear(cfg.hidden_dim, num_classes),
    )

    # Always train classifier head regardless of freeze policy.
    for p in model.classifier.parameters():
        p.requires_grad = True

    return model.to(cfg.device)

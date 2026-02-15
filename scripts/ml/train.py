from __future__ import annotations

from contextlib import nullcontext
from typing import Dict

import torch
import torch.nn as nn
import torch.optim as optim

try:
    from .config import MLConfig
    from .metrics import summarize_eval
except ImportError:  # pragma: no cover
    from config import MLConfig
    from metrics import summarize_eval


class EarlyStopping:
    def __init__(self, patience: int):
        self.patience = patience
        self.best = float("-inf")
        self.bad_epochs = 0

    def step(self, current: float) -> bool:
        if current > self.best:
            self.best = current
            self.bad_epochs = 0
            return False
        self.bad_epochs += 1
        return self.bad_epochs >= self.patience


def _autocast_context(cfg: MLConfig):
    if cfg.amp and cfg.device.type == "cuda":
        return torch.cuda.amp.autocast()
    return nullcontext()


def run_train_epoch(model, loader, optimizer, criterion, cfg: MLConfig, scaler):
    model.train()
    total_loss = 0.0
    total = 0

    for imgs, labels in loader:
        imgs = imgs.to(cfg.device, non_blocking=True)
        labels = labels.to(cfg.device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        with _autocast_context(cfg):
            logits = model(imgs)
            loss = criterion(logits, labels)

        if scaler is not None:
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=cfg.grad_clip_norm)
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=cfg.grad_clip_norm)
            optimizer.step()

        total_loss += loss.item() * imgs.size(0)
        total += imgs.size(0)

    return total_loss / max(total, 1)


def run_eval_epoch(model, loader, criterion, cfg: MLConfig, labels_map: Dict[str, str]):
    model.eval()
    total_loss = 0.0
    total = 0
    all_true = []
    all_pred = []
    top3_correct = 0

    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(cfg.device, non_blocking=True)
            labels = labels.to(cfg.device, non_blocking=True)
            with _autocast_context(cfg):
                logits = model(imgs)
                loss = criterion(logits, labels)

            total_loss += loss.item() * imgs.size(0)
            total += imgs.size(0)

            pred = logits.argmax(dim=1)
            all_true.append(labels.cpu())
            all_pred.append(pred.cpu())

            topk = min(3, logits.size(1))
            _, top_idx = logits.topk(topk, dim=1)
            top3_correct += top_idx.eq(labels.view(-1, 1)).sum().item()

    y_true = torch.cat(all_true) if all_true else torch.tensor([])
    y_pred = torch.cat(all_pred) if all_pred else torch.tensor([])

    metrics = summarize_eval(
        y_true=y_true,
        y_pred=y_pred,
        top3_correct=top3_correct,
        total=total,
        num_classes=len(labels_map),
        labels=labels_map,
    )

    return {
        "loss": total_loss / max(total, 1),
        "top1_acc": metrics["top1_acc"],
        "top3_acc": metrics["top3_acc"],
        "macro_f1": metrics["macro_f1"],
        "confusion_matrix": metrics["confusion_matrix"],
        "per_class": metrics["per_class"],
    }


def train_model(model, train_loader, val_loader, cfg: MLConfig, labels_map: Dict[str, str], model_path):
    criterion = nn.CrossEntropyLoss(label_smoothing=cfg.label_smoothing)
    optimizer = optim.AdamW(
        (p for p in model.parameters() if p.requires_grad),
        lr=cfg.lr,
        weight_decay=cfg.weight_decay,
    )

    steps_per_epoch = max(1, len(train_loader))
    scheduler = optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=cfg.lr,
        epochs=cfg.epochs,
        steps_per_epoch=steps_per_epoch,
        pct_start=0.2,
    )

    use_scaler = cfg.amp and cfg.device.type == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_scaler) if use_scaler else None
    stopper = EarlyStopping(cfg.patience)

    history = []
    best_metric = float("-inf")
    best_epoch = 0

    print("\nTraining started\n")
    for epoch in range(1, cfg.epochs + 1):
        train_loss = run_train_epoch(model, train_loader, optimizer, criterion, cfg, scaler)
        scheduler.step()

        val_metrics = run_eval_epoch(model, val_loader, criterion, cfg, labels_map)
        val_metric = val_metrics["macro_f1"]

        row = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "val_loss": round(val_metrics["loss"], 6),
            "val_acc": round(val_metrics["top1_acc"], 6),
            "val_top3": round(val_metrics["top3_acc"], 6),
            "val_macro_f1": round(val_metrics["macro_f1"], 6),
            "lr": optimizer.param_groups[0]["lr"],
        }
        history.append(row)

        print(
            f"Epoch {epoch:02d}/{cfg.epochs} "
            f"train_loss={train_loss:.4f} val_loss={val_metrics['loss']:.4f} "
            f"val_acc={val_metrics['top1_acc']:.3f} val_f1={val_metrics['macro_f1']:.3f}"
        )

        if val_metric > best_metric:
            best_metric = val_metric
            best_epoch = epoch
            torch.save(
                {
                    "epoch": epoch,
                    "model_state": model.state_dict(),
                    "best_metric": best_metric,
                    "val_acc": val_metrics["top1_acc"],
                },
                model_path,
            )
            print(f"  saved best checkpoint (macro_f1={best_metric:.4f})")

        if stopper.step(val_metric):
            print(f"Early stopping triggered at epoch {epoch}")
            break

    return {
        "history": history,
        "best_metric": best_metric,
        "best_epoch": best_epoch,
    }

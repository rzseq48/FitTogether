from __future__ import annotations

import math
from contextlib import nullcontext
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.optim as optim

try:
    from .config import MLConfig
    from .metrics import summarize_eval
except ImportError:  # pragma: no cover
    from config import MLConfig
    from metrics import summarize_eval


# ── Early stopping ────────────────────────────────────────────────────────────

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


# ── AMP context ───────────────────────────────────────────────────────────────

def _autocast_context(cfg: MLConfig):
    if cfg.amp and cfg.device.type == "cuda":
        return torch.cuda.amp.autocast()
    return nullcontext()


# ── Mixup ─────────────────────────────────────────────────────────────────────

def mixup_batch(
    imgs: torch.Tensor,
    labels: torch.Tensor,
    alpha: float,
    num_classes: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Returns mixed images and soft one-hot labels.
    lam ~ Beta(alpha, alpha); image = lam * x_a + (1-lam) * x_b
    label = lam * onehot_a + (1-lam) * onehot_b
    """
    lam = float(torch.distributions.Beta(alpha, alpha).sample())
    batch_size = imgs.size(0)
    idx = torch.randperm(batch_size, device=imgs.device)

    mixed_imgs = lam * imgs + (1 - lam) * imgs[idx]

    one_hot = torch.zeros(batch_size, num_classes, device=imgs.device)
    one_hot.scatter_(1, labels.view(-1, 1), 1)
    mixed_labels = lam * one_hot + (1 - lam) * one_hot[idx]

    return mixed_imgs, mixed_labels


def soft_cross_entropy(logits: torch.Tensor, soft_targets: torch.Tensor) -> torch.Tensor:
    """Cross-entropy loss accepting soft (non-integer) targets."""
    log_probs = torch.log_softmax(logits, dim=1)
    return -(soft_targets * log_probs).sum(dim=1).mean()


# ── Cosine warmup scheduler ───────────────────────────────────────────────────

class CosineWarmupScheduler(optim.lr_scheduler.LambdaLR):
    """
    Linear warmup for `warmup_steps` steps, then cosine decay to `eta_min`.
    Operates per-step (call scheduler.step() after every optimizer.step()).
    """

    def __init__(
        self,
        optimizer: optim.Optimizer,
        warmup_steps: int,
        total_steps: int,
        eta_min_fraction: float = 0.01,
    ):
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.eta_min_fraction = eta_min_fraction

        def lr_lambda(step: int) -> float:
            if step < warmup_steps:
                return step / max(1, warmup_steps)
            progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
            cosine = 0.5 * (1 + math.cos(math.pi * progress))
            return eta_min_fraction + (1 - eta_min_fraction) * cosine

        super().__init__(optimizer, lr_lambda=lr_lambda)


# ── Epoch runners ─────────────────────────────────────────────────────────────

def run_train_epoch(
    model: nn.Module,
    loader,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    cfg: MLConfig,
    scaler: Optional[torch.cuda.amp.GradScaler],
    scheduler,
    num_classes: int,
) -> float:
    model.train()
    total_loss = 0.0
    total = 0

    use_mixup = cfg.mixup_alpha > 0.0

    for imgs, labels in loader:
        imgs = imgs.to(cfg.device, non_blocking=True)
        labels = labels.to(cfg.device, non_blocking=True)

        if use_mixup:
            imgs, soft_labels = mixup_batch(imgs, labels, cfg.mixup_alpha, num_classes)
        
        optimizer.zero_grad(set_to_none=True)

        with _autocast_context(cfg):
            logits = model(imgs)
            if use_mixup:
                loss = soft_cross_entropy(logits, soft_labels)
            else:
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

        # ✅ Step the scheduler every batch (correct for both OneCycleLR and
        #    CosineWarmupScheduler, which are both step-level schedulers).
        scheduler.step()

        total_loss += loss.item() * imgs.size(0)
        total += imgs.size(0)

    return total_loss / max(total, 1)


def run_eval_epoch(
    model: nn.Module,
    loader,
    criterion: nn.Module,
    cfg: MLConfig,
    labels_map: Dict[str, str],
) -> dict:
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


# ── Progressive unfreezing ────────────────────────────────────────────────────

def unfreeze_backbone(model: nn.Module, optimizer: optim.Optimizer, cfg: MLConfig) -> None:
    """
    Unlock all backbone parameters and add them to the optimizer at a lower lr.
    Called once at cfg.unfreeze_epoch. Using a lower backbone lr (backbone_lr)
    prevents catastrophic forgetting of ImageNet features.
    """
    backbone_lr = cfg.lr * 0.1
    new_params = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            param.requires_grad = True
            new_params.append(param)

    if new_params:
        optimizer.add_param_group({"params": new_params, "lr": backbone_lr})
        print(f"  Progressive unfreeze: {len(new_params)} backbone params unlocked (lr={backbone_lr:.2e})")


# ── Main training loop ────────────────────────────────────────────────────────

def train_model(
    model: nn.Module,
    train_loader,
    val_loader,
    cfg: MLConfig,
    labels_map: Dict[str, str],
    model_path,
) -> dict:
    num_classes = len(labels_map)
    criterion = nn.CrossEntropyLoss(label_smoothing=cfg.label_smoothing)

    # Only pass currently-trainable params to the optimiser at init.
    optimizer = optim.AdamW(
        (p for p in model.parameters() if p.requires_grad),
        lr=cfg.lr,
        weight_decay=cfg.weight_decay,
    )

    # ── Scheduler ─────────────────────────────────────────────────────────────
    steps_per_epoch = max(1, len(train_loader))
    total_steps = cfg.epochs * steps_per_epoch

    if cfg.scheduler == "cosine_warmup":
        warmup_steps = int(total_steps * cfg.warmup_fraction)
        scheduler = CosineWarmupScheduler(
            optimizer,
            warmup_steps=warmup_steps,
            total_steps=total_steps,
            eta_min_fraction=cfg.eta_min_fraction,
        )
        print(f"Scheduler: cosine_warmup (warmup={warmup_steps} steps, total={total_steps} steps)")
    else:
        # OneCycleLR — now correctly called per-step inside run_train_epoch
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=cfg.lr,
            total_steps=total_steps,
            pct_start=0.2,
        )
        print(f"Scheduler: OneCycleLR (total_steps={total_steps})")

    use_scaler = cfg.amp and cfg.device.type == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_scaler) if use_scaler else None
    stopper = EarlyStopping(cfg.patience)

    history = []
    best_metric = float("-inf")
    best_epoch = 0
    backbone_unfrozen = False

    print("\nTraining started\n")
    for epoch in range(1, cfg.epochs + 1):

        # ── Progressive unfreezing ─────────────────────────────────────────
        if (
            cfg.unfreeze_epoch > 0
            and not backbone_unfrozen
            and epoch >= cfg.unfreeze_epoch
        ):
            print(f"\nEpoch {epoch}: triggering progressive backbone unfreeze")
            unfreeze_backbone(model, optimizer, cfg)
            backbone_unfrozen = True

        train_loss = run_train_epoch(
            model, train_loader, optimizer, criterion, cfg, scaler, scheduler, num_classes
        )

        val_metrics = run_eval_epoch(model, val_loader, criterion, cfg, labels_map)
        val_metric = val_metrics["macro_f1"]

        current_lr = optimizer.param_groups[0]["lr"]
        row = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "val_loss": round(val_metrics["loss"], 6),
            "val_acc": round(val_metrics["top1_acc"], 6),
            "val_top3": round(val_metrics["top3_acc"], 6),
            "val_macro_f1": round(val_metrics["macro_f1"], 6),
            "lr": current_lr,
        }
        history.append(row)

        print(
            f"Epoch {epoch:02d}/{cfg.epochs} "
            f"train_loss={train_loss:.4f} val_loss={val_metrics['loss']:.4f} "
            f"val_acc={val_metrics['top1_acc']:.3f} val_f1={val_metrics['macro_f1']:.3f} "
            f"lr={current_lr:.2e}"
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
            print(f"  ✓ saved best checkpoint (macro_f1={best_metric:.4f})")

        if stopper.step(val_metric):
            print(f"Early stopping triggered at epoch {epoch}")
            break

    return {
        "history": history,
        "best_metric": best_metric,
        "best_epoch": best_epoch,
    }
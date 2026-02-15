from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import torch
import torch.nn as nn

try:
    from .config import MLConfig, seed_everything
    from .data import (
        build_label_map_and_samples,
        build_loaders,
        deduplicate_samples,
        detect_structure,
        save_duplicates_log,
        stratified_split,
        validate_no_split_leakage,
    )
    from .metrics import sort_worst_classes
    from .model import build_model
    from .train import run_eval_epoch, train_model
except ImportError:  # pragma: no cover
    from config import MLConfig, seed_everything
    from data import (
        build_label_map_and_samples,
        build_loaders,
        deduplicate_samples,
        detect_structure,
        save_duplicates_log,
        stratified_split,
        validate_no_split_leakage,
    )
    from metrics import sort_worst_classes
    from model import build_model
    from train import run_eval_epoch, train_model

DEFAULT_NUTRITION = {
    "biryani": {"calories": 350, "protein": 15, "carbs": 45, "fat": 12},
    "butter_chicken": {"calories": 290, "protein": 25, "carbs": 10, "fat": 18},
    "dal": {"calories": 180, "protein": 10, "carbs": 28, "fat": 4},
    "dosa": {"calories": 165, "protein": 4, "carbs": 32, "fat": 4},
    "idli": {"calories": 58, "protein": 2, "carbs": 12, "fat": 0.4},
    "naan": {"calories": 262, "protein": 9, "carbs": 45, "fat": 5},
    "paneer": {"calories": 265, "protein": 18, "carbs": 4, "fat": 20},
    "samosa": {"calories": 260, "protein": 5, "carbs": 30, "fat": 13},
    "tikka_masala": {"calories": 300, "protein": 28, "carbs": 12, "fat": 16},
    "unknown": {"calories": 250, "protein": 10, "carbs": 30, "fat": 10},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FitTogether ML pipeline")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--num-workers", type=int, default=None)
    parser.add_argument("--freeze-policy", choices=["all_backbone", "last_blocks", "full_finetune"], default=None)
    parser.add_argument("--disable-amp", action="store_true")
    parser.add_argument("--disable-dedup", action="store_true")
    return parser.parse_args()


def apply_overrides(cfg: MLConfig, args: argparse.Namespace) -> MLConfig:
    if args.data_dir is not None:
        cfg.data_dir = args.data_dir
    if args.output_dir is not None:
        cfg.output_dir = args.output_dir
    if args.epochs is not None:
        cfg.epochs = args.epochs
    if args.batch_size is not None:
        cfg.batch_size = args.batch_size
    if args.lr is not None:
        cfg.lr = args.lr
    if args.seed is not None:
        cfg.seed = args.seed
    if args.num_workers is not None:
        cfg.num_workers = args.num_workers
    if args.freeze_policy is not None:
        cfg.freeze_policy = args.freeze_policy
    if args.disable_amp:
        cfg.amp = False
    if args.disable_dedup:
        cfg.detect_duplicates = False
    return cfg


def save_csvs(cfg: MLConfig, labels_map: dict, per_class: list, confusion: torch.Tensor) -> None:
    with cfg.per_class_metrics_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["class_idx", "class_name", "precision", "recall", "f1", "support"])
        writer.writeheader()
        for row in per_class:
            writer.writerow(row)

    ordered_labels = [labels_map[str(i)] for i in range(len(labels_map))]
    with cfg.confusion_matrix_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["true\\pred", *ordered_labels])
        for idx, row in enumerate(confusion.tolist()):
            writer.writerow([ordered_labels[idx], *row])


def save_bundle(cfg: MLConfig, model, idx_to_label: dict, best_metric: float) -> None:
    torch.save(
        {
            "model_state": model.state_dict(),
            "idx_to_label": idx_to_label,
            "training_config": cfg.as_dict(),
            "best_metric": best_metric,
            "model_name": cfg.model_name,
        },
        cfg.bundle_path,
    )


def run_pipeline(cfg: MLConfig) -> None:
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    seed_everything(cfg.seed)

    print("=" * 70)
    print("FitTogether ML pipeline")
    print("=" * 70)
    print(f"Device: {cfg.device}")

    structure, items, resolved = detect_structure(cfg.data_dir)
    print(f"Resolved data dir: {resolved}")
    print(f"Structure: {structure}")

    label_map, samples = build_label_map_and_samples(structure, items)
    if len(samples) == 0:
        raise RuntimeError("No images discovered in dataset")
    if len(label_map) < 2:
        raise RuntimeError("At least 2 classes are required for training")

    idx_to_label = {str(v): k for k, v in label_map.items()}
    with cfg.labels_path.open("w", encoding="utf-8") as f:
        json.dump(idx_to_label, f, indent=2)

    nutrition_map = {cls: DEFAULT_NUTRITION.get(cls.lower(), DEFAULT_NUTRITION["unknown"]) for cls in label_map}
    with cfg.nutrition_path.open("w", encoding="utf-8") as f:
        json.dump(nutrition_map, f, indent=2)

    print(f"Classes: {len(label_map)} | Samples: {len(samples)}")

    if cfg.detect_duplicates:
        deduped, duplicates, hash_map = deduplicate_samples(samples)
        samples = deduped
        if duplicates:
            save_duplicates_log(cfg.duplicates_log_path, duplicates)
            print(f"Removed {len(duplicates)} duplicate files")
    else:
        hash_map = {p: str(p) for p, _ in samples}

    train_samples, val_samples, test_samples = stratified_split(
        samples, val_split=cfg.val_split, test_split=cfg.test_split, seed=cfg.seed
    )
    validate_no_split_leakage(train_samples, val_samples, test_samples, hash_map)

    print(
        f"Split sizes -> train={len(train_samples)} val={len(val_samples)} test={len(test_samples)}"
    )

    train_loader, val_loader, test_loader = build_loaders(
        cfg, train_samples, val_samples, test_samples
    )

    model = build_model(cfg, num_classes=len(label_map))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Trainable params: {trainable:,}/{total:,}")

    train_out = train_model(
        model,
        train_loader,
        val_loader,
        cfg=cfg,
        labels_map=idx_to_label,
        model_path=cfg.model_path,
    )

    checkpoint = torch.load(cfg.model_path, map_location=cfg.device)
    model.load_state_dict(checkpoint["model_state"])

    criterion = nn.CrossEntropyLoss(label_smoothing=cfg.label_smoothing)
    test_metrics = run_eval_epoch(
        model,
        test_loader,
        criterion,
        cfg=cfg,
        labels_map=idx_to_label,
    )

    history_payload = {
        "history": train_out["history"],
        "best_epoch": train_out["best_epoch"],
        "best_metric": train_out["best_metric"],
        "test": {
            "loss": test_metrics["loss"],
            "top1_acc": test_metrics["top1_acc"],
            "top3_acc": test_metrics["top3_acc"],
            "macro_f1": test_metrics["macro_f1"],
        },
    }
    with cfg.history_path.open("w", encoding="utf-8") as f:
        json.dump(history_payload, f, indent=2)

    summary = {
        "best_epoch": train_out["best_epoch"],
        "val_macro_f1": train_out["best_metric"],
        "test_top1_acc": test_metrics["top1_acc"],
        "test_top3_acc": test_metrics["top3_acc"],
        "test_macro_f1": test_metrics["macro_f1"],
    }
    with cfg.metrics_summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    save_csvs(
        cfg,
        labels_map=idx_to_label,
        per_class=test_metrics["per_class"],
        confusion=test_metrics["confusion_matrix"],
    )

    save_bundle(cfg, model, idx_to_label=idx_to_label, best_metric=train_out["best_metric"])

    # Backward-compatible legacy checkpoint output.
    torch.save(
        {
            "epoch": train_out["best_epoch"],
            "model_state": model.state_dict(),
            "val_acc": checkpoint.get("val_acc", 0.0),
        },
        cfg.model_path,
    )

    worst = sort_worst_classes(test_metrics["per_class"], k=5)

    print("\nSummary")
    print(f"best_epoch={train_out['best_epoch']}")
    print(f"val_macro_f1={train_out['best_metric']:.4f}")
    print(f"test_top1_acc={test_metrics['top1_acc']:.4f}")
    print(f"test_top3_acc={test_metrics['top3_acc']:.4f}")
    print(f"test_macro_f1={test_metrics['macro_f1']:.4f}")
    print("Worst 5 classes by F1:")
    for row in worst:
        print(
            f"  {row['class_name']}: f1={row['f1']:.3f} "
            f"precision={row['precision']:.3f} recall={row['recall']:.3f}"
        )

    print("\nArtifacts")
    print(f"- {cfg.model_path}")
    print(f"- {cfg.labels_path}")
    print(f"- {cfg.nutrition_path}")
    print(f"- {cfg.bundle_path}")
    print(f"- {cfg.history_path}")
    print(f"- {cfg.metrics_summary_path}")
    print(f"- {cfg.per_class_metrics_path}")
    print(f"- {cfg.confusion_matrix_path}")


def main() -> None:
    cfg = apply_overrides(MLConfig(), parse_args())
    run_pipeline(cfg)


if __name__ == "__main__":
    main()

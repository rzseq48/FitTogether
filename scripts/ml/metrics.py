from __future__ import annotations

from typing import Dict, List

import torch


def confusion_matrix(y_true: torch.Tensor, y_pred: torch.Tensor, num_classes: int) -> torch.Tensor:
    matrix = torch.zeros((num_classes, num_classes), dtype=torch.int64)
    for t, p in zip(y_true.view(-1), y_pred.view(-1)):
        matrix[t.long(), p.long()] += 1
    return matrix


def per_class_from_confusion(matrix: torch.Tensor, labels: Dict[str, str]) -> List[dict]:
    rows: List[dict] = []
    for idx in range(matrix.size(0)):
        tp = matrix[idx, idx].item()
        fp = matrix[:, idx].sum().item() - tp
        fn = matrix[idx, :].sum().item() - tp
        support = matrix[idx, :].sum().item()

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        if precision + recall:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = 0.0

        rows.append(
            {
                "class_idx": idx,
                "class_name": labels.get(str(idx), str(idx)),
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": int(support),
            }
        )
    return rows


def summarize_eval(
    y_true: torch.Tensor,
    y_pred: torch.Tensor,
    top3_correct: int,
    total: int,
    num_classes: int,
    labels: Dict[str, str],
) -> dict:
    matrix = confusion_matrix(y_true, y_pred, num_classes=num_classes)
    per_class = per_class_from_confusion(matrix, labels)
    macro_f1 = sum(x["f1"] for x in per_class) / len(per_class) if per_class else 0.0
    top1_acc = (y_true == y_pred).float().mean().item() if total else 0.0
    top3_acc = top3_correct / total if total else 0.0

    return {
        "top1_acc": top1_acc,
        "top3_acc": top3_acc,
        "macro_f1": macro_f1,
        "confusion_matrix": matrix,
        "per_class": per_class,
    }


def sort_worst_classes(per_class: List[dict], k: int = 5) -> List[dict]:
    return sorted(per_class, key=lambda x: x["f1"])[:k]

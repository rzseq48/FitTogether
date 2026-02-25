from __future__ import annotations

import unittest

import torch

from scripts.ml.metrics import (
    confusion_matrix,
    per_class_from_confusion,
    sort_worst_classes,
    summarize_eval,
)


class TestMetrics(unittest.TestCase):
    def test_confusion_and_per_class(self) -> None:
        y_true = torch.tensor([0, 1, 1, 0])
        y_pred = torch.tensor([0, 1, 0, 0])
        matrix = confusion_matrix(y_true, y_pred, num_classes=2)
        self.assertEqual(matrix.tolist(), [[2, 0], [1, 1]])

        labels = {"0": "idli", "1": "dosa"}
        per_class = per_class_from_confusion(matrix, labels)
        self.assertEqual(len(per_class), 2)
        self.assertEqual(per_class[0]["class_name"], "idli")

    def test_summarize_eval_and_sort(self) -> None:
        y_true = torch.tensor([0, 1, 1, 0])
        y_pred = torch.tensor([0, 1, 0, 0])
        labels = {"0": "idli", "1": "dosa"}

        result = summarize_eval(
            y_true=y_true,
            y_pred=y_pred,
            top3_correct=4,
            total=4,
            num_classes=2,
            labels=labels,
        )
        self.assertIn("macro_f1", result)
        self.assertAlmostEqual(result["top1_acc"], 0.75, places=6)
        self.assertAlmostEqual(result["top3_acc"], 1.0, places=6)

        worst = sort_worst_classes(result["per_class"], k=1)
        self.assertEqual(len(worst), 1)
        self.assertEqual(worst[0]["class_name"], "dosa")


if __name__ == "__main__":
    unittest.main()

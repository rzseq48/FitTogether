from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.ml.data import (
    build_label_map_and_samples,
    deduplicate_samples,
    detect_structure,
    save_duplicates_log,
    stratified_split,
    validate_no_split_leakage,
)


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (12, 12), color=color).save(path)


class TestDataHelpers(unittest.TestCase):
    def test_detect_structure_subfolder_and_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "wrapper" / "dataset"
            _write_image(base / "idli" / "a.jpg", (255, 0, 0))
            _write_image(base / "dosa" / "b.jpg", (0, 255, 0))

            structure, items, resolved = detect_structure(Path(tmp))
            self.assertEqual(structure, "subfolder")
            self.assertEqual(resolved, base)
            self.assertEqual({item.name for item in items}, {"idli", "dosa"})

    def test_detect_structure_flat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_image(root / "idli_1.jpg", (255, 0, 0))
            _write_image(root / "dosa_2.png", (0, 255, 0))

            structure, items, _ = detect_structure(root)
            self.assertEqual(structure, "flat")
            self.assertEqual(len(items), 2)

    def test_build_label_map_flat_and_subfolder(self) -> None:
        flat_items = [Path("idli_1.jpg"), Path("dosa_2.jpg"), Path("idli_3.jpg")]
        flat_map, flat_samples = build_label_map_and_samples("flat", flat_items)
        self.assertEqual(set(flat_map.keys()), {"idli", "dosa"})
        self.assertEqual(len(flat_samples), 3)

        subfolders = [Path("biryani"), Path("idli")]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dirs = []
            for folder in subfolders:
                d = tmp_path / folder
                dirs.append(d)
                _write_image(d / "sample.jpg", (1, 2, 3))
            sub_map, sub_samples = build_label_map_and_samples("subfolder", dirs)
            self.assertEqual(set(sub_map.keys()), {"biryani", "idli"})
            self.assertEqual(len(sub_samples), 2)

    def test_deduplicate_and_save_duplicates_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one = root / "one.jpg"
            dup = root / "dup.jpg"
            other = root / "other.jpg"
            content = b"same-bytes"
            one.write_bytes(content)
            dup.write_bytes(content)
            other.write_bytes(b"other")

            samples = [(one, 0), (dup, 0), (other, 1)]
            deduped, duplicates, hash_map = deduplicate_samples(samples)
            self.assertEqual(len(deduped), 2)
            self.assertEqual(len(duplicates), 1)
            self.assertEqual(hash_map[one], hash_map[dup])

            log_path = root / "duplicates_removed.json"
            save_duplicates_log(log_path, duplicates)
            payload = json.loads(log_path.read_text(encoding="utf-8"))
            self.assertIn("duplicates_removed", payload)
            self.assertEqual(len(payload["duplicates_removed"]), 1)

    def test_stratified_split_and_no_leakage(self) -> None:
        samples = []
        for label in [0, 1]:
            for idx in range(10):
                samples.append((Path(f"class{label}_{idx}.jpg"), label))

        train, val, test = stratified_split(samples, val_split=0.2, test_split=0.2, seed=42)
        self.assertTrue(train)
        self.assertTrue(val)
        self.assertTrue(test)

        hash_map = {path: str(path) for path, _ in samples}
        validate_no_split_leakage(train, val, test, hash_map)

        # Force leakage by mapping one train and one val sample to the same hash.
        bad_hash_map = dict(hash_map)
        bad_hash_map[train[0][0]] = "same"
        bad_hash_map[val[0][0]] = "same"
        with self.assertRaises(RuntimeError):
            validate_no_split_leakage(train, val, test, bad_hash_map)


if __name__ == "__main__":
    unittest.main()

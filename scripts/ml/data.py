from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms

try:
    from .config import MLConfig
except ImportError:  # pragma: no cover
    from config import MLConfig

ImageSample = Tuple[Path, int]


# ── Directory / file helpers ──────────────────────────────────────────────────

def _resolve_data_dir(base: Path) -> Path:
    current = base
    while True:
        subdirs = [d for d in current.iterdir() if d.is_dir()]
        images = _find_images(current)
        if len(subdirs) == 1 and not images:
            print(f"  -> Stepping into wrapper folder: {subdirs[0].name}")
            current = subdirs[0]
            continue
        return current


def _find_images(path: Path) -> List[Path]:
    return sorted(
        [
            *path.glob("*.jpg"),
            *path.glob("*.jpeg"),
            *path.glob("*.png"),
            *path.glob("*.JPG"),
            *path.glob("*.JPEG"),
            *path.glob("*.PNG"),
        ]
    )


def detect_structure(data_dir: Path) -> Tuple[str, Sequence[Path], Path]:
    resolved_dir = _resolve_data_dir(data_dir)
    subdirs = sorted([d for d in resolved_dir.iterdir() if d.is_dir()])
    images = _find_images(resolved_dir)

    if subdirs:
        return "subfolder", subdirs, resolved_dir
    if images:
        return "flat", images, resolved_dir
    raise ValueError(f"No images found in {resolved_dir}")


def _label_from_filename(image_path: Path) -> str:
    stem = image_path.stem
    head = stem.split("_")[0]
    if head and not head.isdigit():
        return head
    return stem


# ── Label map / sample builders ───────────────────────────────────────────────

def build_label_map_and_samples(
    structure: str, items: Sequence[Path]
) -> Tuple[Dict[str, int], List[ImageSample]]:
    if structure == "subfolder":
        classes = sorted([x.name for x in items])
        label_map = {name: idx for idx, name in enumerate(classes)}
        samples: List[ImageSample] = []
        for category in items:
            for image in _find_images(category):
                samples.append((image, label_map[category.name]))
        return label_map, samples

    labels = [_label_from_filename(img) for img in items]
    classes = sorted(set(labels))
    label_map = {name: idx for idx, name in enumerate(classes)}
    samples = [(img, label_map[label]) for img, label in zip(items, labels)]
    return label_map, samples


# ── Deduplication ─────────────────────────────────────────────────────────────

def deduplicate_samples(
    samples: Sequence[ImageSample],
) -> Tuple[List[ImageSample], List[dict], Dict[Path, str]]:
    hash_to_primary: Dict[str, Path] = {}
    sample_hashes: Dict[Path, str] = {}
    deduped: List[ImageSample] = []
    duplicates: List[dict] = []

    for path, label in samples:
        digest = _file_sha1(path)
        sample_hashes[path] = digest
        existing = hash_to_primary.get(digest)
        if existing is None:
            hash_to_primary[digest] = path
            deduped.append((path, label))
            continue
        duplicates.append({"duplicate": str(path), "kept": str(existing), "sha1": digest})

    return deduped, duplicates, sample_hashes


def _file_sha1(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


# ── Stratified split ──────────────────────────────────────────────────────────

def stratified_split(
    samples: Sequence[ImageSample], val_split: float, test_split: float, seed: int
) -> Tuple[List[ImageSample], List[ImageSample], List[ImageSample]]:
    by_class: Dict[int, List[Path]] = defaultdict(list)
    for path, label in samples:
        by_class[label].append(path)

    rng = random.Random(seed)
    train: List[ImageSample] = []
    val: List[ImageSample] = []
    test: List[ImageSample] = []

    for label, class_paths in by_class.items():
        class_paths = sorted(class_paths)
        rng.shuffle(class_paths)
        n_total = len(class_paths)

        n_test = int(n_total * test_split)
        n_val = int(n_total * val_split)

        if n_total >= 3:
            if n_test == 0:
                n_test = 1
            if n_val == 0:
                n_val = 1
            if n_test + n_val >= n_total:
                n_val = max(1, n_total - n_test - 1)
            if n_test + n_val >= n_total:
                n_test = max(1, n_total - n_val - 1)

        test_paths = class_paths[:n_test]
        val_paths = class_paths[n_test : n_test + n_val]
        train_paths = class_paths[n_test + n_val :]

        train.extend([(p, label) for p in train_paths])
        val.extend([(p, label) for p in val_paths])
        test.extend([(p, label) for p in test_paths])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def validate_no_split_leakage(
    train: Sequence[ImageSample],
    val: Sequence[ImageSample],
    test: Sequence[ImageSample],
    hash_map: Dict[Path, str],
) -> None:
    train_hashes = {hash_map[path] for path, _ in train}
    val_hashes = {hash_map[path] for path, _ in val}
    test_hashes = {hash_map[path] for path, _ in test}

    if train_hashes & val_hashes:
        raise RuntimeError("Data leakage detected between train and val splits")
    if train_hashes & test_hashes:
        raise RuntimeError("Data leakage detected between train and test splits")
    if val_hashes & test_hashes:
        raise RuntimeError("Data leakage detected between val and test splits")


# ── Dataset ───────────────────────────────────────────────────────────────────

class FoodDataset(Dataset):
    def __init__(self, samples: Sequence[ImageSample], image_size: int, transform=None):
        self.samples = list(samples)
        self.image_size = image_size
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        path, label = self.samples[idx]
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            img = Image.new("RGB", (self.image_size, self.image_size))
        if self.transform:
            img = self.transform(img)
        return img, label


# ── Transforms ────────────────────────────────────────────────────────────────

def build_transforms(
    image_size: int,
    randaugment_magnitude: int = 8,
    random_erasing_prob: float = 0.25,
):
    """
    Train transform:
      Resize → RandomCrop → HFlip → RandAugment → ToTensor → Normalize → RandomErasing

    RandAugment (magnitude=8) applies a random selection of photometric /
    geometric ops each batch — much stronger than fixed ColorJitter alone.
    RandomErasing randomly occludes a patch, improving occlusion robustness.

    Eval transform: centre-crop only (no stochastic ops).
    """
    normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])

    train_ops = [
        transforms.Resize((image_size + 32, image_size + 32)),
        transforms.RandomCrop(image_size),
        transforms.RandomHorizontalFlip(p=0.5),
    ]

    if randaugment_magnitude > 0:
        # num_ops=2, magnitude in [1, 31]
        train_ops.append(transforms.RandAugment(num_ops=2, magnitude=randaugment_magnitude))

    train_ops += [transforms.ToTensor(), normalize]

    if random_erasing_prob > 0:
        train_ops.append(
            transforms.RandomErasing(
                p=random_erasing_prob,
                scale=(0.02, 0.20),
                ratio=(0.3, 3.3),
                value="random",
            )
        )

    train_tf = transforms.Compose(train_ops)

    eval_tf = transforms.Compose(
        [
            transforms.Resize((image_size + 32, image_size + 32)),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            normalize,
        ]
    )

    # TTA transform: same as eval but with a horizontal flip — averaged at
    # inference time by FoodPredictor.
    tta_tf = transforms.Compose(
        [
            transforms.Resize((image_size + 32, image_size + 32)),
            transforms.RandomCrop(image_size),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
            transforms.ToTensor(),
            normalize,
        ]
    )

    return train_tf, eval_tf, tta_tf


# ── Weighted sampler ──────────────────────────────────────────────────────────

def make_weighted_sampler(samples: Sequence[ImageSample]) -> WeightedRandomSampler:
    """
    Builds a WeightedRandomSampler so that each class is sampled equally
    regardless of its raw frequency — helps with class imbalance.
    """
    label_counts: Dict[int, int] = defaultdict(int)
    for _, label in samples:
        label_counts[label] += 1

    total = len(samples)
    class_weights = {cls: total / count for cls, count in label_counts.items()}
    sample_weights = [class_weights[label] for _, label in samples]

    return WeightedRandomSampler(
        weights=sample_weights,
        num_samples=total,
        replacement=True,
    )


# ── DataLoaders ───────────────────────────────────────────────────────────────

def build_loaders(
    cfg: MLConfig,
    train_samples: Sequence[ImageSample],
    val_samples: Sequence[ImageSample],
    test_samples: Sequence[ImageSample],
):
    train_tf, eval_tf, _ = build_transforms(
        cfg.image_size,
        randaugment_magnitude=cfg.randaugment_magnitude,
        random_erasing_prob=cfg.random_erasing_prob,
    )

    train_dataset = FoodDataset(train_samples, image_size=cfg.image_size, transform=train_tf)

    # Weighted sampler replaces shuffle=True — gives balanced class exposure.
    if cfg.weighted_sampling:
        sampler = make_weighted_sampler(train_samples)
        train_loader = DataLoader(
            train_dataset,
            batch_size=cfg.batch_size,
            sampler=sampler,          # mutually exclusive with shuffle
            num_workers=cfg.num_workers,
            pin_memory=torch.cuda.is_available(),
        )
    else:
        train_loader = DataLoader(
            train_dataset,
            batch_size=cfg.batch_size,
            shuffle=True,
            num_workers=cfg.num_workers,
            pin_memory=torch.cuda.is_available(),
        )

    val_loader = DataLoader(
        FoodDataset(val_samples, image_size=cfg.image_size, transform=eval_tf),
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=cfg.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    test_loader = DataLoader(
        FoodDataset(test_samples, image_size=cfg.image_size, transform=eval_tf),
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=cfg.num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    return train_loader, val_loader, test_loader


# ── Misc ──────────────────────────────────────────────────────────────────────

def save_duplicates_log(path: Path, duplicates: Sequence[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump({"duplicates_removed": list(duplicates)}, f, indent=2)
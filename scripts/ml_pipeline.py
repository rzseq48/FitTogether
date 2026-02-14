# =============================================================================
# FitTogether — Indian Food ML Pipeline
# =============================================================================
# Handles: classification, nutrition estimation, recipe suggestion
# Model:   EfficientNet-B0 (pretrained on ImageNet, fine-tuned on your data)
# Usage:   python ml_pipeline.py
# =============================================================================

import os
import json
import shutil
import random
import warnings
from pathlib import Path
from collections import Counter

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIG — edit these paths/settings as needed
# =============================================================================

_BASE        = Path("/home/rohanseq48/Git_projects/prenatal-landing-page/FitTogether/test_images/Indian Food Images")

# Auto-resolve: if _BASE only has one subfolder (itself acting as a wrapper),
# step inside it to find the real category folders
def _resolve_data_dir(base: Path) -> Path:
    subdirs = [d for d in base.iterdir() if d.is_dir()]
    images  = list(base.glob("*.jpg")) + list(base.glob("*.jpeg")) + list(base.glob("*.png"))
    # If there's exactly one subdir and no images at this level, go one level deeper
    if len(subdirs) == 1 and not images:
        print(f"  ↳ Stepping into wrapper folder: {subdirs[0].name}")
        return _resolve_data_dir(subdirs[0])
    return base

DATA_DIR     = _resolve_data_dir(_BASE)
OUTPUT_DIR   = Path("/home/rohanseq48/Git_projects/prenatal-landing-page/FitTogether/ml_model")
SPLIT_DIR    = OUTPUT_DIR / "dataset_split"
MODEL_PATH   = OUTPUT_DIR / "food_model.pth"
LABELS_PATH  = OUTPUT_DIR / "labels.json"
NUTRITION_PATH = OUTPUT_DIR / "nutrition_map.json"

IMG_SIZE     = 224
BATCH_SIZE   = 32
EPOCHS       = 15
LR           = 1e-4
VAL_SPLIT    = 0.15
TEST_SPLIT   = 0.10
DEVICE       = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Using device: {DEVICE}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# STEP 1: DETECT DATASET STRUCTURE
# =============================================================================

def detect_structure(data_dir: Path):
    """Auto-detect whether images are in subfolders or flat with filename labels."""
    subdirs = [d for d in data_dir.iterdir() if d.is_dir()]
    images  = list(data_dir.glob("*.jpg")) + list(data_dir.glob("*.jpeg")) + list(data_dir.glob("*.png"))

    if subdirs:
        print(f"✅ Subfolder structure detected — {len(subdirs)} categories found")
        return "subfolder", subdirs
    elif images:
        print(f"✅ Flat structure detected — {len(images)} images, parsing filenames for labels")
        return "flat", images
    else:
        raise ValueError(f"No images found in {data_dir}")


def build_label_map_from_subfolders(subdirs):
    classes = sorted([d.name for d in subdirs])
    label_map = {cls: idx for idx, cls in enumerate(classes)}
    samples   = []
    for d in subdirs:
        imgs = list(d.glob("*.jpg")) + list(d.glob("*.jpeg")) + list(d.glob("*.png"))
        for img in imgs:
            samples.append((img, label_map[d.name]))
    return label_map, samples


def build_label_map_from_filenames(images):
    """Extract label from filename prefix before underscore or digits."""
    labels = []
    for img in images:
        stem  = img.stem
        parts = stem.split('_')
        label = parts[0] if not parts[0].isdigit() else stem
        labels.append(label)

    classes   = sorted(set(labels))
    label_map = {cls: idx for idx, cls in enumerate(classes)}
    samples   = [(img, label_map[label]) for img, label in zip(images, labels)]
    return label_map, samples


# =============================================================================
# STEP 2: TRAIN / VAL / TEST SPLIT
# =============================================================================

def split_dataset(samples, val_split=VAL_SPLIT, test_split=TEST_SPLIT):
    random.seed(42)
    random.shuffle(samples)
    n       = len(samples)
    n_test  = int(n * test_split)
    n_val   = int(n * val_split)
    test    = samples[:n_test]
    val     = samples[n_test:n_test + n_val]
    train   = samples[n_test + n_val:]
    print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    return train, val, test


# =============================================================================
# STEP 3: DATASET CLASS
# =============================================================================

class FoodDataset(Dataset):
    def __init__(self, samples, transform=None):
        self.samples   = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            img = Image.new("RGB", (IMG_SIZE, IMG_SIZE))
        if self.transform:
            img = self.transform(img)
        return img, label


def get_transforms():
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
        transforms.RandomCrop(IMG_SIZE),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
        transforms.RandomRotation(15),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225]),
    ])
    return train_tf, val_tf


# =============================================================================
# STEP 4: MODEL — EfficientNet-B0 fine-tuned
# =============================================================================

def build_model(num_classes: int):
    model = models.efficientnet_b0(weights="IMAGENET1K_V1")

    # Freeze early layers, fine-tune last 3 blocks + classifier
    for name, param in model.named_parameters():
        param.requires_grad = False

    for name, param in model.named_parameters():
        if any(x in name for x in ["features.6", "features.7", "features.8", "classifier"]):
            param.requires_grad = True

    # Replace classifier head
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_features, 512),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(512, num_classes),
    )
    return model.to(DEVICE)


# =============================================================================
# STEP 5: TRAINING LOOP
# =============================================================================

def train_epoch(model, loader, optimizer, criterion):
    model.train()
    total_loss, correct, total = 0, 0, 0
    for imgs, labels in loader:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(imgs)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * imgs.size(0)
        correct    += (outputs.argmax(1) == labels).sum().item()
        total      += imgs.size(0)
    return total_loss / total, correct / total


def eval_epoch(model, loader, criterion):
    model.eval()
    total_loss, correct, total = 0, 0, 0
    with torch.no_grad():
        for imgs, labels in loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            outputs     = model(imgs)
            loss        = criterion(outputs, labels)
            total_loss += loss.item() * imgs.size(0)
            correct    += (outputs.argmax(1) == labels).sum().item()
            total      += imgs.size(0)
    return total_loss / total, correct / total


def train(model, train_loader, val_loader, epochs=EPOCHS):
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR, weight_decay=1e-4
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_acc = 0
    history = []

    print("\n📈 Training started...\n")
    for epoch in range(1, epochs + 1):
        train_loss, train_acc = train_epoch(model, train_loader, optimizer, criterion)
        val_loss,   val_acc   = eval_epoch(model, val_loader, criterion)
        scheduler.step()

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc":  round(train_acc, 4),
            "val_loss":   round(val_loss, 4),
            "val_acc":    round(val_acc, 4),
        })

        print(f"Epoch {epoch:02d}/{epochs} | "
              f"Train Loss: {train_loss:.4f} Acc: {train_acc:.3f} | "
              f"Val Loss: {val_loss:.4f} Acc: {val_acc:.3f}")

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "epoch":      epoch,
                "model_state": model.state_dict(),
                "val_acc":    best_val_acc,
            }, MODEL_PATH)
            print(f"  ✅ Best model saved (val_acc={best_val_acc:.3f})")

    print(f"\n🏆 Training complete! Best val accuracy: {best_val_acc:.3f}")
    return history


# =============================================================================
# STEP 6: NUTRITION MAP (template — expand per your food classes)
# =============================================================================

DEFAULT_NUTRITION = {
    "biryani":         {"calories": 350, "protein": 15, "carbs": 45, "fat": 12},
    "butter_chicken":  {"calories": 290, "protein": 25, "carbs": 10, "fat": 18},
    "dal":             {"calories": 180, "protein": 10, "carbs": 28, "fat": 4},
    "dosa":            {"calories": 165, "protein": 4,  "carbs": 32, "fat": 4},
    "idli":            {"calories": 58,  "protein": 2,  "carbs": 12, "fat": 0.4},
    "naan":            {"calories": 262, "protein": 9,  "carbs": 45, "fat": 5},
    "paneer":          {"calories": 265, "protein": 18, "carbs": 4,  "fat": 20},
    "samosa":          {"calories": 260, "protein": 5,  "carbs": 30, "fat": 13},
    "tikka_masala":    {"calories": 300, "protein": 28, "carbs": 12, "fat": 16},
    "unknown":         {"calories": 250, "protein": 10, "carbs": 30, "fat": 10},
}


# =============================================================================
# STEP 7: INFERENCE ENGINE (used by chatbot)
# =============================================================================

class FoodPredictor:
    """
    Load trained model and predict food class, nutrition, and recipe suggestion.
    Use this class in your FitTogether chatbot.
    """

    def __init__(self, model_path=MODEL_PATH, labels_path=LABELS_PATH, nutrition_path=NUTRITION_PATH):
        with open(labels_path)    as f: self.labels    = json.load(f)  # {idx: class_name}
        with open(nutrition_path) as f: self.nutrition = json.load(f)

        num_classes = len(self.labels)
        self.model  = build_model(num_classes)
        checkpoint  = torch.load(model_path, map_location=DEVICE)
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.eval()

        _, self.transform = get_transforms()
        print(f"✅ FoodPredictor loaded — {num_classes} classes")

    def predict(self, image_path: str, top_k: int = 3):
        img     = Image.open(image_path).convert("RGB")
        tensor  = self.transform(img).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            logits  = self.model(tensor)
            probs   = torch.softmax(logits, dim=1)[0]

        top_probs, top_idxs = probs.topk(top_k)
        results = []
        for prob, idx in zip(top_probs, top_idxs):
            cls       = self.labels[str(idx.item())]
            nutrition = self.nutrition.get(cls, self.nutrition.get("unknown", {}))
            results.append({
                "food":      cls,
                "confidence": round(prob.item(), 3),
                "nutrition": nutrition,
                "recipe_query": f"Indian {cls} recipe",
            })

        return results

    def predict_for_chatbot(self, image_path: str):
        """Returns a chatbot-friendly response string."""
        results = self.predict(image_path, top_k=1)
        if not results:
            return "I couldn't identify this food item."

        top = results[0]
        n   = top["nutrition"]
        return (
            f"🍽️ I think this is **{top['food'].replace('_', ' ').title()}** "
            f"({top['confidence']*100:.0f}% confident)\n\n"
            f"📊 **Nutrition (per serving):**\n"
            f"  • Calories: {n.get('calories', '?')} kcal\n"
            f"  • Protein:  {n.get('protein', '?')}g\n"
            f"  • Carbs:    {n.get('carbs', '?')}g\n"
            f"  • Fat:      {n.get('fat', '?')}g\n\n"
            f"🔍 Want a recipe? Search: \"{top['recipe_query']}\""
        )


# =============================================================================
# MAIN — runs the full pipeline
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  FitTogether — Indian Food ML Pipeline")
    print("=" * 60)

    # Step 1: Detect structure
    print("\n🔍 Step 1: Detecting dataset structure...")
    structure, items = detect_structure(DATA_DIR)

    # Step 2: Build label map
    print("\n🏷️  Step 2: Building label map...")
    if structure == "subfolder":
        label_map, samples = build_label_map_from_subfolders(items)
    else:
        label_map, samples = build_label_map_from_filenames(items)

    num_classes = len(label_map)
    print(f"  {num_classes} food categories | {len(samples)} total images")
    print(f"  Categories: {list(label_map.keys())[:10]}{'...' if num_classes > 10 else ''}")

    if len(samples) == 0:
        print(f"\n ERROR: No images found! Resolved DATA_DIR: {DATA_DIR}")
        print(f"   Contents: {[x.name for x in DATA_DIR.iterdir()][:10]}")
        exit(1)

    if num_classes < 2:
        print(f"\n ERROR: Only {num_classes} class found - need at least 2 to train.")
        print(f"   Resolved DATA_DIR: {DATA_DIR}")
        print(f"   Subdirs: {[d.name for d in DATA_DIR.iterdir() if d.is_dir()]}")
        exit(1)

    # Save labels (idx → class_name for inference)
    idx_to_label = {str(v): k for k, v in label_map.items()}
    with open(LABELS_PATH, "w") as f:
        json.dump(idx_to_label, f, indent=2)
    print(f"  Labels saved → {LABELS_PATH}")

    # Save nutrition map
    nutrition_map = {cls: DEFAULT_NUTRITION.get(cls.lower(), DEFAULT_NUTRITION["unknown"])
                     for cls in label_map}
    with open(NUTRITION_PATH, "w") as f:
        json.dump(nutrition_map, f, indent=2)
    print(f"  Nutrition map saved → {NUTRITION_PATH}")

    # Step 3: Split dataset
    print("\n✂️  Step 3: Splitting dataset...")
    train_samples, val_samples, test_samples = split_dataset(samples)

    # Step 4: Build data loaders
    print("\n📦 Step 4: Building data loaders...")
    train_tf, val_tf = get_transforms()
    train_loader = DataLoader(FoodDataset(train_samples, train_tf),
                              batch_size=BATCH_SIZE, shuffle=True,  num_workers=4, pin_memory=True)
    val_loader   = DataLoader(FoodDataset(val_samples,   val_tf),
                              batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)
    test_loader  = DataLoader(FoodDataset(test_samples,  val_tf),
                              batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

    # Step 5: Build model
    print(f"\n🧠 Step 5: Building EfficientNet-B0 model ({num_classes} classes)...")
    model = build_model(num_classes)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"  Trainable params: {trainable:,} / {total:,}")

    # Step 6: Train
    print(f"\n🚀 Step 6: Training for {EPOCHS} epochs...")
    history = train(model, train_loader, val_loader)

    # Step 7: Final test evaluation
    print("\n🧪 Step 7: Final test set evaluation...")
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state"])
    test_loss, test_acc = eval_epoch(model, test_loader, nn.CrossEntropyLoss())
    print(f"  Test Accuracy: {test_acc:.3f} | Test Loss: {test_loss:.4f}")

    # Save history
    history_path = OUTPUT_DIR / "training_history.json"
    with open(history_path, "w") as f:
        json.dump({"history": history, "test_acc": test_acc, "test_loss": test_loss}, f, indent=2)
    print(f"\n📊 Training history saved → {history_path}")

    print("\n" + "=" * 60)
    print("✅ Pipeline complete! Files saved:")
    print(f"   Model:      {MODEL_PATH}")
    print(f"   Labels:     {LABELS_PATH}")
    print(f"   Nutrition:  {NUTRITION_PATH}")
    print(f"   History:    {history_path}")
    print("\n💡 To use in your chatbot:")
    print("   from ml_pipeline import FoodPredictor")
    print("   predictor = FoodPredictor()")
    print("   response  = predictor.predict_for_chatbot('photo.jpg')")
    print("=" * 60)
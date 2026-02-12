import zipfile
from pathlib import Path
from collections import Counter

with zipfile.ZipFile('food.zip', 'r') as z:
    all_files = z.namelist()

    # Read the txt file
    txt_files = [f for f in all_files if f.endswith('.txt')]
    print("=== TXT FILE CONTENTS ===")
    for txt in txt_files:
        with z.open(txt) as f:
            content = f.read().decode('utf-8', errors='ignore')
            print(f"\n--- {txt} ---")
            print(content[:2000])  # First 2000 chars

    # Show first 30 image filenames
    imgs = [f for f in all_files if f.endswith('.jpg')]
    print("\n=== FIRST 30 IMAGE FILENAMES ===")
    for img in imgs[:30]:
        print(img)

    # Check if filenames contain category info
    print("\n=== FILENAME PATTERN ANALYSIS ===")
    # Try to extract prefixes/categories from filenames
    names = [Path(f).stem for f in imgs]
    # Check for numeric-only names
    numeric = sum(1 for n in names if n.isdigit())
    print(f"Purely numeric filenames: {numeric}/{len(imgs)}")

    # Check for underscore patterns (e.g. pizza_001, burger_002)
    has_underscore = [n for n in names if '_' in n]
    print(f"Filenames with underscores: {len(has_underscore)}")
    if has_underscore:
        print("  Examples:", has_underscore[:10])

    # Try to extract prefix before underscore or digits
    prefixes = []
    for n in names:
        parts = n.split('_')
        if len(parts) > 1 and not parts[0].isdigit():
            prefixes.append(parts[0])
    if prefixes:
        prefix_counts = Counter(prefixes)
        print(f"\nUnique prefixes (potential categories): {len(prefix_counts)}")
        for p, c in prefix_counts.most_common(20):
            print(f"  {p}: {c} images")
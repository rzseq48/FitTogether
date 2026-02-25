# FitTogether 💪

A mobile fitness and nutrition tracking app powered by AI. Snap a photo of your food, get instant calorie estimates, log your meals, and get coached — all in one place.

> Built with Expo (React Native), Supabase, and a custom-trained PyTorch food recognition model.

---

## Features

- **AI Food Tracker** — Take a photo of any meal and the app identifies the food, estimates calories and nutrition, and saves it to your personal log
- **Fitness Tracker** — Log and track your workouts over time
- **AI Coach** — Personalized guidance based on your activity and nutrition data
- **Supabase Backend** — Auth, real-time database, and storage all powered by Supabase

---

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile App | [Expo](https://expo.dev) (React Native) |
| Routing | Expo Router (file-based) |
| Backend / DB | [Supabase](https://supabase.com) |
| ML Model | PyTorch (custom-trained food classifier) |
| Inference | Python (`scripts/ml/infer.py`) |

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+ (for ML pipeline)
- A [Supabase](https://supabase.com) project

### Install & Run

```bash
# Install JS dependencies
npm install

# Start the Expo dev server
npx expo start
```

From there you can open the app in:
- [Expo Go](https://expo.dev/go)
- [iOS Simulator](https://docs.expo.dev/workflow/ios-simulator/)
- [Android Emulator](https://docs.expo.dev/workflow/android-studio-emulator/)

### Environment Variables

Create a `.env` file in the root with your Supabase credentials:

```env
EXPO_PUBLIC_SUPABASE_URL=your_supabase_url
EXPO_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

---

## ML Pipeline (Food Recognition Model)

The food classifier is a fine-tuned image classification model trained on Indian food images.

### Training

```bash
python3 scripts/ml/main.py \
  --data-dir "test_images/Indian Food Images" \
  --epochs 15 \
  --batch-size 32 \
  --seed 42
```

**Optional flags:**

- `--freeze-policy {all_backbone,last_blocks,full_finetune}` — control which layers are trained
- `--output-dir ml_model` — where to save artifacts
- `--disable-amp` — disable automatic mixed precision
- `--disable-dedup` — disable dataset deduplication

### Output Artifacts

Training writes to `ml_model/`:

| File | Description |
|---|---|
| `food_model.pth` | Model checkpoint |
| `model_bundle.pt` | Packaged artifact for inference |
| `labels.json` | Class label mapping |
| `nutrition_map.json` | Nutrition data per food class |
| `training_history.json` | Loss/accuracy over epochs |
| `metrics_summary.json` | Final evaluation metrics |
| `per_class_metrics.csv` | Per-class precision/recall/F1 |
| `confusion_matrix.csv` | Full confusion matrix |

### Inference

```python
from scripts.ml.infer import FoodPredictor

predictor = FoodPredictor()
result = predictor.predict_for_chatbot("photo.jpg")
print(result)
```

### ML Pipeline Tests

Run the ML unit test suite:

```bash
.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Project Structure

```
FitTogether/
├── app/
│   ├── (tabs)/
│   │   ├── food.tsx          # Food tracker tab (photo → AI → calories)
│   │   ├── workout.tsx       # Workout tracker tab
│   │   ├── chat.tsx          # AI coach chat tab
│   │   └── _layout.tsx       # Tab navigator layout
│   ├── auth/
│   │   ├── login.tsx
│   │   └── signup.tsx
│   ├── index.tsx             # Entry / redirect
│   └── _layout.tsx           # Root layout
├── components/               # Shared UI components
├── constants/
│   └── theme.ts              # App theme / design tokens
├── hooks/                    # Custom React hooks
├── lib/
│   └── supabase.ts           # Supabase client setup
├── scripts/
│   └── ml/                   # ML training & inference pipeline
│       ├── main.py           # Training entry point
│       ├── model.py          # Model architecture
│       ├── data.py           # Dataset & preprocessing
│       ├── train.py          # Training loop
│       ├── infer.py          # Inference / FoodPredictor
│       ├── metrics.py        # Evaluation metrics
│       └── config.py         # Hyperparameters & config
├── ml_model/                 # Trained model artifacts (gitignored)
│   ├── food_model.pth
│   ├── labels.json
│   └── nutrition_map.json
└── test_images/              # Training dataset (Indian food images)
```

---

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---

## License

[MIT](LICENSE)

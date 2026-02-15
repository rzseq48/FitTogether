# Welcome to your Expo app 👋

This is an [Expo](https://expo.dev) project created with [`create-expo-app`](https://www.npmjs.com/package/create-expo-app).

## Get started

1. Install dependencies

   ```bash
   npm install
   ```

2. Start the app

   ```bash
   npx expo start
   ```

In the output, you'll find options to open the app in a

- [development build](https://docs.expo.dev/develop/development-builds/introduction/)
- [Android emulator](https://docs.expo.dev/workflow/android-studio-emulator/)
- [iOS simulator](https://docs.expo.dev/workflow/ios-simulator/)
- [Expo Go](https://expo.dev/go), a limited sandbox for trying out app development with Expo

You can start developing by editing the files inside the **app** directory. This project uses [file-based routing](https://docs.expo.dev/router/introduction).

## Get a fresh project

When you're ready, run:

```bash
npm run reset-project
```

This command will move the starter code to the **app-example** directory and create a blank **app** directory where you can start developing.

## Learn more

To learn more about developing your project with Expo, look at the following resources:

- [Expo documentation](https://docs.expo.dev/): Learn fundamentals, or go into advanced topics with our [guides](https://docs.expo.dev/guides).
- [Learn Expo tutorial](https://docs.expo.dev/tutorial/introduction/): Follow a step-by-step tutorial where you'll create a project that runs on Android, iOS, and the web.

## Join the community

Join our community of developers creating universal apps.

- [Expo on GitHub](https://github.com/expo/expo): View our open source platform and contribute.
- [Discord community](https://chat.expo.dev): Chat with Expo users and ask questions.
Day 1: Built authentication and food tracking

## ML pipeline (food model)

Train and evaluate the model with the modular pipeline:

```bash
python3 scripts/ml/main.py \
  --data-dir "test_images/Indian Food Images" \
  --epochs 15 \
  --batch-size 32 \
  --seed 42
```

Available useful flags:

- `--freeze-policy {all_backbone,last_blocks,full_finetune}`
- `--disable-amp`
- `--disable-dedup`
- `--output-dir ml_model`

The run writes artifacts to `ml_model/`, including:

- `food_model.pth` (legacy checkpoint)
- `labels.json`
- `nutrition_map.json`
- `model_bundle.pt` (new packaged artifact)
- `training_history.json`
- `metrics_summary.json`
- `per_class_metrics.csv`
- `confusion_matrix.csv`

Inference usage:

```python
from scripts.ml.infer import FoodPredictor

predictor = FoodPredictor()
print(predictor.predict_for_chatbot("photo.jpg"))
```

Legacy import remains supported:

```python
from scripts.ml_pipeline import FoodPredictor
```

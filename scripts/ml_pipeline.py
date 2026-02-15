"""Backward-compatible entrypoint for FitTogether ML pipeline.

Preferred entrypoint:
    python3 scripts/ml/main.py

Legacy compatibility:
    from scripts.ml_pipeline import FoodPredictor
"""

try:
    from scripts.ml.infer import FoodPredictor
    from scripts.ml.main import main
except ModuleNotFoundError:  # Allows: python3 scripts/ml_pipeline.py
    from ml.infer import FoodPredictor
    from ml.main import main

__all__ = ["FoodPredictor", "main"]


if __name__ == "__main__":
    main()

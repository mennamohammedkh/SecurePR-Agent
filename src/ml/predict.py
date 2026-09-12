"""
predict.py
------------
Person 1 — Data/ML Owner
Secure Agentic Code Review — Inference / Team Integration Point

Exposes predict_merge(pr_features), the function Person 2 will call from
inside the LangGraph AgentState to get a merge-probability estimate for a
given Pull Request's features.

The best model (by F1-score on the test set, per evaluate.py's output) is
loaded by default -- currently SVM, but this is read dynamically from
results/metrics.csv so it stays correct if you retrain and a different
model wins.

USAGE (standalone test):
  python predict.py --demo

USAGE (as a library, from Person 2's code):
  from predict import predict_merge
  result = predict_merge({
      "pr_size": 120, "code_churn": 150, "review_activity": 5,
      "num_reviewers": 2, "num_commits": 4, "num_changed_files": 6,
      "additions": 90, "deletions": 30, "pr_description_length": 240,
      "num_comments": 3,
      # tfidf_0 ... tfidf_49 only required if the model was trained
      # with --text-features; omit them otherwise.
  })
  # -> {"merge_probability": 0.78, "model": "svm"}
"""

import argparse
import json
import os
import pickle
import numpy as np
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(_THIS_DIR, "..", "..", "models")
RESULTS_DIR = os.path.join(_THIS_DIR, "..", "..", "results")

_MODEL_FILENAMES = {
    "logistic_regression": "logistic_regression.pkl",
    "random_forest": "random_forest.pkl",
    "svm": "svm.pkl",
}
_NEEDS_SCALING = {"logistic_regression": True, "random_forest": False, "svm": True}

_cache = {}


def _pick_best_model_name() -> str:
    """Reads results/metrics.csv and returns the model name with the highest F1."""
    metrics_path = os.path.join(RESULTS_DIR, "metrics.csv")
    if os.path.exists(metrics_path):
        df = pd.read_csv(metrics_path, index_col=0)
        best_display_name = df["F1"].idxmax()
        # map "Random Forest" -> "random_forest", etc.
        return best_display_name.lower().replace(" ", "_").replace("-", "_")
    return "random_forest"  # sensible default if evaluate.py hasn't run yet


def _load_artifacts(model_name: str = None):
    """Loads (and caches) the model, scaler, and feature column list."""
    if model_name is None:
        model_name = _pick_best_model_name()

    if model_name in _cache:
        return _cache[model_name]

    model_path = os.path.join(MODELS_DIR, _MODEL_FILENAMES[model_name])
    scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")
    features_path = os.path.join(MODELS_DIR, "feature_columns.json")

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    with open(features_path) as f:
        feature_cols = json.load(f)

    artifacts = (model, scaler, feature_cols, model_name)
    _cache[model_name] = artifacts
    return artifacts


def predict_merge(pr_features: dict, model_name: str = None) -> dict:
    """
    Predicts the probability that a Pull Request will be merged.

    Args:
        pr_features: dict mapping feature name -> value. Must contain (at
            minimum) the base features produced by feature_engineering.py:
            pr_size, code_churn, review_activity, num_reviewers,
            num_commits, num_changed_files, additions, deletions,
            pr_description_length, num_comments
            (plus tfidf_0..tfidf_49 if the loaded model was trained with
            --text-features; missing ones default to 0).
        model_name: one of "logistic_regression", "random_forest", "svm".
            If None, automatically uses the best model per results/metrics.csv.

    Returns:
        {"merge_probability": float, "model": str}
    """
    model, scaler, feature_cols, resolved_model_name = _load_artifacts(model_name)

    row = [pr_features.get(col, 0.0) for col in feature_cols]
    X = np.array([row], dtype=float)

    if _NEEDS_SCALING[resolved_model_name]:
        X = scaler.transform(X)

    proba = float(model.predict_proba(X)[0, 1])

    return {
        "merge_probability": round(proba, 4),
        "model": resolved_model_name,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="run a demo prediction with example features")
    parser.add_argument("--model", type=str, default=None, choices=list(_MODEL_FILENAMES.keys()))
    args = parser.parse_args()

    if args.demo:
        example = {
            "pr_size": 120, "code_churn": 150, "review_activity": 5,
            "num_reviewers": 2, "num_commits": 4, "num_changed_files": 6,
            "additions": 90, "deletions": 30, "pr_description_length": 240,
            "num_comments": 3,
        }
        result = predict_merge(example, model_name=args.model)
        print(f"Input features: {example}")
        print(f"Prediction: {result}")


if __name__ == "__main__":
    main()

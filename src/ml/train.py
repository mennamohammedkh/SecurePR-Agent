"""
train.py
----------
Person 1 — Data/ML Owner
Secure Agentic Code Review — Baseline Model Training

Trains 3 baseline models on data/train.csv to predict `target_merged`:
  1. Logistic Regression
  2. Random Forest
  3. SVM (RBF kernel, probability=True)

Saves each trained model (+ the fitted StandardScaler) as a .pkl file
under models/, ready to be loaded by evaluate.py / predict.py.

USAGE:
  python train.py --train ../../data/train.csv \
      --features ../../data/feature_columns.json --outdir ../../models
"""

import argparse
import json
import pickle
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler


def load_training_data(train_path: str, features_path: str):
    df = pd.read_csv(train_path)
    with open(features_path) as f:
        feature_cols = json.load(f)
    X = df[feature_cols].values
    y = df["target_merged"].values
    return X, y, feature_cols


def train_models(X, y, feature_cols):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    models = {}

    print("Training Logistic Regression...")
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr.fit(X_scaled, y)
    models["logistic_regression"] = lr

    print("Training Random Forest...")
    rf = RandomForestClassifier(n_estimators=300, max_depth=10, class_weight="balanced", random_state=42)
    rf.fit(X, y)  # tree-based model: unscaled features are fine
    models["random_forest"] = rf

    print("Training SVM...")
    svm = SVC(kernel="rbf", probability=True, class_weight="balanced", random_state=42)
    svm.fit(X_scaled, y)
    models["svm"] = svm

    return models, scaler


def save_models(models: dict, scaler: StandardScaler, feature_cols: list, outdir: str):
    import os
    os.makedirs(outdir, exist_ok=True)

    for name, model in models.items():
        path = f"{outdir}/{name}.pkl"
        with open(path, "wb") as f:
            pickle.dump(model, f)
        print(f"Saved {path}")

    with open(f"{outdir}/scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open(f"{outdir}/feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"Saved {outdir}/scaler.pkl and feature_columns.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=str, default="../../data/train.csv")
    parser.add_argument("--features", type=str, default="../../data/feature_columns.json")
    parser.add_argument("--outdir", type=str, default="../../models")
    args = parser.parse_args()

    X, y, feature_cols = load_training_data(args.train, args.features)
    print(f"Training on {len(X)} samples, {len(feature_cols)} features.")

    models, scaler = train_models(X, y, feature_cols)
    save_models(models, scaler, feature_cols, args.outdir)

    print("\nTraining complete. Run evaluate.py next to compute test-set metrics.")


if __name__ == "__main__":
    main()

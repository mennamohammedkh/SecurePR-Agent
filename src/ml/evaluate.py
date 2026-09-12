"""
evaluate.py
-------------
Person 1 — Data/ML Owner
Secure Agentic Code Review — Model Evaluation

Loads the 3 trained models from models/, evaluates each on data/test.csv,
and produces:
  - results/metrics.csv          (Accuracy, Precision, Recall, F1, ROC-AUC per model)
  - results/confusion_matrix.png (3-panel confusion matrix comparison)
  - results/feature_importance.png (Random Forest feature importance)

USAGE:
  python evaluate.py --test ../../data/test.csv --models ../../models --out ../../results
"""

import argparse
import json
import pickle
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, ConfusionMatrixDisplay,
)


def load_model(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def evaluate_model(model, X, y, needs_scaling, scaler):
    X_input = scaler.transform(X) if needs_scaling else X
    y_pred = model.predict(X_input)
    y_proba = model.predict_proba(X_input)[:, 1]

    metrics = {
        "Accuracy": accuracy_score(y, y_pred),
        "Precision": precision_score(y, y_pred, zero_division=0),
        "Recall": recall_score(y, y_pred, zero_division=0),
        "F1": f1_score(y, y_pred, zero_division=0),
        "ROC-AUC": roc_auc_score(y, y_proba),
    }
    cm = confusion_matrix(y, y_pred)
    return metrics, cm, y_pred, y_proba


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=str, default="../../data/test.csv")
    parser.add_argument("--models", type=str, default="../../models")
    parser.add_argument("--out", type=str, default="../../results")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    with open(f"{args.models}/feature_columns.json") as f:
        feature_cols = json.load(f)

    df = pd.read_csv(args.test)
    X = df[feature_cols].values
    y = df["target_merged"].values

    scaler = load_model(f"{args.models}/scaler.pkl")

    model_specs = [
        ("Logistic Regression", "logistic_regression.pkl", True),
        ("Random Forest", "random_forest.pkl", False),
        ("SVM", "svm.pkl", True),
    ]

    all_metrics = {}
    all_cms = {}
    for display_name, filename, needs_scaling in model_specs:
        model = load_model(f"{args.models}/{filename}")
        metrics, cm, y_pred, y_proba = evaluate_model(model, X, y, needs_scaling, scaler)
        all_metrics[display_name] = metrics
        all_cms[display_name] = cm
        print(f"\n=== {display_name} ===")
        for k, v in metrics.items():
            print(f"  {k:10s}: {v:.3f}")

    # --- metrics.csv ---
    metrics_df = pd.DataFrame(all_metrics).T
    metrics_df.index.name = "Model"
    metrics_df = metrics_df.round(3)
    metrics_df.to_csv(f"{args.out}/metrics.csv")
    print(f"\nSaved comparison table -> {args.out}/metrics.csv")
    print(metrics_df)

    # --- confusion_matrix.png (3-panel) ---
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (display_name, _, _) in zip(axes, model_specs):
        cm = all_cms[display_name]
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Not Merged", "Merged"])
        disp.plot(ax=ax, colorbar=False, cmap="Blues")
        ax.set_title(display_name)
    plt.tight_layout()
    plt.savefig(f"{args.out}/confusion_matrix.png", dpi=150)
    plt.close()
    print(f"Saved confusion matrices -> {args.out}/confusion_matrix.png")

    # --- feature_importance.png (Random Forest) ---
    rf = load_model(f"{args.models}/random_forest.pkl")
    importances = dict(zip(feature_cols, rf.feature_importances_))
    top_features = dict(sorted(importances.items(), key=lambda x: -x[1])[:15])

    plt.figure(figsize=(9, 6))
    plt.barh(list(top_features.keys())[::-1], list(top_features.values())[::-1], color="#C44E52")
    plt.title("Random Forest — Top 15 Feature Importances")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig(f"{args.out}/feature_importance.png", dpi=150)
    plt.close()
    print(f"Saved feature importance chart -> {args.out}/feature_importance.png")

    # best model summary
    best_model = metrics_df["F1"].idxmax()
    print(f"\nBest model by F1-score: {best_model} (F1={metrics_df.loc[best_model, 'F1']})")


if __name__ == "__main__":
    main()

"""
ML vs LLM Merge Prediction — Comparison على نفس الـheld-out test set (بند 17)
=================================================================================
بيستخدم data/test.csv (نفس test set بتاع Person 1، فيه target_merged الحقيقي)
+ data/cleaned_prs.csv (عشان نجيب pr_title/pr_description للـLLM، لأن
test.csv فيه features رقمية جاهزة بس مش النص الخام).

تشغيل:
    PYTHONPATH=. python evaluation/merge_prediction_comparison.py
"""
import csv
import json
import os

from src.ml.predict import predict_merge
from src.review.merge_predictor import predict_merge_llm

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SAMPLE_SIZE = 20  # عينة من test.csv (تشغيل أسرع)؛ زوّديها لو عايزة تقييم أشمل


def load_test_rows(limit=SAMPLE_SIZE):
    with open(os.path.join(DATA_DIR, "test.csv")) as f:
        rows = list(csv.DictReader(f))
    return rows[:limit]


def load_pr_text_by_id():
    with open(os.path.join(DATA_DIR, "cleaned_prs.csv")) as f:
        rows = list(csv.DictReader(f))
    return {r["pr_id"]: r for r in rows}


def _accuracy(preds, labels, threshold=0.5):
    correct = sum(1 for p, y in zip(preds, labels) if (p >= threshold) == bool(int(y)))
    return correct / len(labels) if labels else 0.0


def run_comparison():
    test_rows = load_test_rows()
    pr_text_by_id = load_pr_text_by_id()

    ml_preds, llm_preds, labels = [], [], []

    for row in test_rows:
        pr_id = row["pr_id"]
        label = row["target_merged"]

        # --- ML: نفس الـfeature row بالظبط زي ما اتدرب عليها الموديل (60 عمود) ---
        features = {k: float(v) for k, v in row.items() if k not in ("target_merged", "pr_id", "repository")}
        ml_result = predict_merge(features)
        ml_preds.append(ml_result["merge_probability"])

        # --- LLM: نص PR الحقيقي (title/description) من cleaned_prs.csv ---
        pr_text = pr_text_by_id.get(pr_id, {})
        llm_context = {
            "diff": "",  # الـdataset ده متسجلش فيه diff خام، بس description
            "pr_description": pr_text.get("pr_description", ""),
            "commit_message": "",
            "repository_context": "",
        }
        llm_result = predict_merge_llm(llm_context)
        llm_preds.append(llm_result.get("merge_probability") or 0.5)

        labels.append(label)

    ml_acc = _accuracy(ml_preds, labels)
    llm_acc = _accuracy(llm_preds, labels)

    print(f"Sample size: {len(labels)} PRs from the real held-out test set (test.csv)")
    print(f"{'Model':20} {'Accuracy':>10}")
    print("-" * 32)
    print(f"{'Random Forest/SVM ML':20} {ml_acc:>10.1%}")
    print(f"{'LLM (mock mode)':20} {llm_acc:>10.1%}")
    print()
    print("NOTE: LLM ran in MOCK_MODE (no ANTHROPIC_API_KEY) -- its predictions")
    print("are template-based, not a real reasoning pass over the PR. This")
    print("comparison validates the HARNESS (same test set, same metric) and")
    print("should be re-run once a real API key is available for a meaningful")
    print("quality comparison.")

    return {"ml_accuracy": ml_acc, "llm_accuracy": llm_acc, "n": len(labels)}


if __name__ == "__main__":
    run_comparison()

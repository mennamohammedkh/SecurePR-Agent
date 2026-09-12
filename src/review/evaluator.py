"""
evaluator.py
--------------
Person 3 — LLM / Review Owner
Secure Agentic Code Review — Evaluation

Runs the Code Review Agent across all 4 context experiments (A-D) x all 4
prompt patterns (zero_shot, few_shot, role_based, reflection) = 16
combinations, over the labeled sample set in data/sample_prs_for_review.json,
and produces:

  - results/prompt_comparison.csv  (per-combination Accuracy/Precision/
                                     Recall/F1/BLEU/ROUGE-L/avg inference time)
  - results/review_metrics.csv     (best combination's per-PR breakdown)
  - results/examples.json          (a few full example reviews, for the report)

BLEU and ROUGE-L are implemented locally (no nltk/rouge-score dependency
required) so this runs in any plain Python + scikit-learn environment.

USAGE:
  python evaluator.py --data ../../data/sample_prs_for_review.json --out ../../results
"""

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from code_review_agent import review_code
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

EXPERIMENTS = ["A", "B", "C", "D"]
PATTERNS = ["zero_shot", "few_shot", "role_based", "reflection"]


# ---------------------------------------------------------------------------
# Lightweight BLEU / ROUGE-L (no external dependency)
# ---------------------------------------------------------------------------

def simple_bleu(candidate: str, reference: str) -> float:
    """BLEU-1 with brevity penalty -- unigram precision, no external deps."""
    cand_tokens = candidate.lower().split()
    ref_tokens = reference.lower().split()
    if not cand_tokens or not ref_tokens:
        return 0.0

    cand_counts = Counter(cand_tokens)
    ref_counts = Counter(ref_tokens)
    overlap = sum(min(cand_counts[t], ref_counts[t]) for t in cand_counts)
    precision = overlap / len(cand_tokens)

    bp = 1.0 if len(cand_tokens) >= len(ref_tokens) else \
        pow(2.718281828, 1 - len(ref_tokens) / max(len(cand_tokens), 1))
    return precision * bp


def _lcs_length(a: list, b: list) -> int:
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def simple_rouge_l(candidate: str, reference: str) -> float:
    """ROUGE-L F-measure based on the longest common subsequence."""
    cand_tokens = candidate.lower().split()
    ref_tokens = reference.lower().split()
    if not cand_tokens or not ref_tokens:
        return 0.0
    lcs = _lcs_length(cand_tokens, ref_tokens)
    if lcs == 0:
        return 0.0
    precision = lcs / len(cand_tokens)
    recall = lcs / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Evaluation loop
# ---------------------------------------------------------------------------

def review_to_text(review: dict) -> str:
    """Concatenates a review's issue descriptions+suggestions into one string
    for BLEU/ROUGE comparison against the human-written reference comment."""
    parts = [review.get("summary", "")]
    for issue in review.get("issues", []):
        parts.append(issue.get("description", ""))
        parts.append(issue.get("suggestion", ""))
    return " ".join(parts)


def evaluate_combination(prs: list, experiment: str, pattern: str) -> dict:
    y_true, y_pred = [], []
    bleu_scores, rouge_scores, times = [], [], []
    per_pr_records = []

    for pr in prs:
        review = review_code(pr, experiment=experiment, pattern=pattern)

        predicted_has_issue = len(review.get("issues", [])) > 0
        y_true.append(int(pr["has_issue"]))
        y_pred.append(int(predicted_has_issue))

        gen_text = review_to_text(review)
        ref_text = pr.get("reference_comment", "")
        bleu = simple_bleu(gen_text, ref_text)
        rouge = simple_rouge_l(gen_text, ref_text)
        bleu_scores.append(bleu)
        rouge_scores.append(rouge)
        times.append(review.get("_inference_time_sec", 0.0))

        per_pr_records.append({
            "pr_id": pr["pr_id"], "experiment": experiment, "pattern": pattern,
            "ground_truth_has_issue": pr["has_issue"], "predicted_has_issue": predicted_has_issue,
            "bleu": round(bleu, 3), "rouge_l": round(rouge, 3),
            "num_issues_found": len(review.get("issues", [])),
        })

    metrics = {
        "experiment": experiment,
        "pattern": pattern,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "avg_bleu": sum(bleu_scores) / len(bleu_scores),
        "avg_rouge_l": sum(rouge_scores) / len(rouge_scores),
        "avg_inference_time_sec": sum(times) / len(times),
        "n_prs": len(prs),
    }
    return metrics, per_pr_records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="../../data/sample_prs_for_review.json")
    parser.add_argument("--out", type=str, default="../../results")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    with open(args.data) as f:
        prs = json.load(f)
    print(f"Loaded {len(prs)} labeled sample PRs.")

    all_metrics = []
    all_per_pr = []
    for experiment in EXPERIMENTS:
        for pattern in PATTERNS:
            print(f"Evaluating experiment={experiment}, pattern={pattern} ...")
            metrics, per_pr = evaluate_combination(prs, experiment, pattern)
            all_metrics.append(metrics)
            all_per_pr.extend(per_pr)

    import pandas as pd
    comparison_df = pd.DataFrame(all_metrics).round(3)
    comparison_df.to_csv(f"{args.out}/prompt_comparison.csv", index=False)
    print(f"\nSaved comparison across all {len(all_metrics)} combinations -> {args.out}/prompt_comparison.csv")
    print(comparison_df.sort_values("f1", ascending=False).head(5).to_string(index=False))

    best_row = comparison_df.loc[comparison_df["f1"].idxmax()]
    print(f"\nBest combination: experiment={best_row['experiment']}, pattern={best_row['pattern']} "
          f"(F1={best_row['f1']}, BLEU={best_row['avg_bleu']}, ROUGE-L={best_row['avg_rouge_l']})")

    per_pr_df = pd.DataFrame(all_per_pr)
    best_subset = per_pr_df[
        (per_pr_df["experiment"] == best_row["experiment"]) & (per_pr_df["pattern"] == best_row["pattern"])
    ]
    best_subset.to_csv(f"{args.out}/review_metrics.csv", index=False)
    print(f"Saved per-PR breakdown for the best combination -> {args.out}/review_metrics.csv")

    # examples.json: full example reviews for 3 PRs, using the best combination
    examples = []
    for pr in prs[:3]:
        review = review_code(pr, experiment=best_row["experiment"], pattern=best_row["pattern"])
        examples.append({
            "pr_id": pr["pr_id"],
            "experiment": best_row["experiment"],
            "pattern": best_row["pattern"],
            "input_context": pr,
            "generated_review": review,
        })
    with open(f"{args.out}/examples.json", "w") as f:
        json.dump(examples, f, indent=2)
    print(f"Saved example reviews -> {args.out}/examples.json")


if __name__ == "__main__":
    main()

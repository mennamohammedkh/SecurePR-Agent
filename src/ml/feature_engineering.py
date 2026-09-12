"""
feature_engineering.py
------------------------
Person 1 — Data/ML Owner
Secure Agentic Code Review — Feature Engineering

Loads data/cleaned_prs.csv, derives the features requested in the spec,
optionally adds TF-IDF text features from title/description/commit
messages, and produces a 70/15/15 train/validation/test split.

Features derived:
  PR Size, Code Churn, Review Activity, Number of Reviewers,
  Commit Count, Files Changed, Lines Added, Lines Deleted,
  PR Description Length, Comment Count
  (+ optional TF-IDF text features)

USAGE:
  python feature_engineering.py --in ../../data/cleaned_prs.csv \
      --outdir ../../data --text-features
"""

import argparse
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer

BASE_FEATURES = [
    "pr_size", "code_churn", "review_activity", "num_reviewers",
    "num_commits", "num_changed_files", "additions", "deletions",
    "pr_description_length", "num_comments",
]


def engineer_features(df: pd.DataFrame, text_features: bool = False):
    df["pr_size"] = df["additions"].fillna(0) + df["deletions"].fillna(0)
    df["code_churn"] = df["changed_lines"].fillna(0)
    df["review_activity"] = df["num_reviews"].fillna(0) + df["num_comments"].fillna(0)
    df["pr_description_length"] = df["pr_description"].fillna("").astype(str).str.len()

    feature_cols = list(BASE_FEATURES)

    if text_features:
        text_corpus = (
            df["pr_title"].fillna("").astype(str) + " " +
            df["pr_description"].fillna("").astype(str) + " " +
            df["commit_messages"].fillna("[]").astype(str)
        )
        vectorizer = TfidfVectorizer(max_features=50, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(text_corpus).toarray()
        tfidf_cols = [f"tfidf_{i}" for i in range(tfidf_matrix.shape[1])]
        tfidf_df = pd.DataFrame(tfidf_matrix, columns=tfidf_cols, index=df.index)
        df = pd.concat([df, tfidf_df], axis=1)
        feature_cols += tfidf_cols
        print(f"Added {len(tfidf_cols)} TF-IDF text features.")

    df["target_merged"] = df["merged"].astype(int)
    return df, feature_cols


def split_and_save(df: pd.DataFrame, feature_cols: list, outdir: str):
    keep_cols = feature_cols + ["target_merged", "pr_id", "repository"]
    data = df[keep_cols].dropna(subset=feature_cols)

    train_df, temp_df = train_test_split(
        data, test_size=0.30, random_state=42, stratify=data["target_merged"]
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=42, stratify=temp_df["target_merged"]
    )

    train_df.to_csv(f"{outdir}/train.csv", index=False)
    val_df.to_csv(f"{outdir}/validation.csv", index=False)
    test_df.to_csv(f"{outdir}/test.csv", index=False)

    print(f"\nSplit sizes: train={len(train_df)}, validation={len(val_df)}, test={len(test_df)}")
    print(f"Saved to {outdir}/train.csv, validation.csv, test.csv")

    with open(f"{outdir}/feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"Saved feature column list -> {outdir}/feature_columns.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", type=str, default="../../data/cleaned_prs.csv")
    parser.add_argument("--outdir", type=str, default="../../data")
    parser.add_argument("--text-features", action="store_true", help="add TF-IDF text features (optional, per spec)")
    args = parser.parse_args()

    df = pd.read_csv(args.in_path)
    df, feature_cols = engineer_features(df, text_features=args.text_features)
    print(f"Feature columns ({len(feature_cols)}): {feature_cols}")
    split_and_save(df, feature_cols, args.outdir)


if __name__ == "__main__":
    main()

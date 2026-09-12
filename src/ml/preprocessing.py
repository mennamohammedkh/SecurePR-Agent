"""
preprocessing.py
------------------
Person 1 — Data/ML Owner
Secure Agentic Code Review — Data Cleaning

Loads data/raw_prs.json and produces data/cleaned_prs.csv after:
  1. Handling missing values
  2. Removing exact duplicates
  3. Excluding invalid PRs (e.g., zero commits, missing core fields)
  4. Feature normalization (numeric columns -> z-score, saved as *_norm)
  5. Class balance check (merged vs. not merged)
  6. Outlier analysis (IQR method) with a report, without silently
     dropping outliers (flagged instead, so you decide per-model)

USAGE:
  python preprocessing.py --in ../../data/raw_prs.json --out ../../data/cleaned_prs.csv
"""

import argparse
import json
import pandas as pd
import numpy as np

NUMERIC_COLS = [
    "num_commits", "num_changed_files", "additions", "deletions",
    "changed_lines", "num_comments", "num_reviews", "num_reviewers",
]


def load_raw(path: str) -> pd.DataFrame:
    with open(path) as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} raw records.")
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    missing_report = df.isnull().sum()
    missing_report = missing_report[missing_report > 0]
    if len(missing_report):
        print("\nMissing values per column:")
        print(missing_report)

    # numeric fields central to the ML task: impute with median rather than
    # dropping the row outright (keeps sample size for a small dataset)
    for col in NUMERIC_COLS:
        if col in df.columns and df[col].isnull().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)

    # text fields: empty string is a valid value (an empty description IS
    # information -- treat missing the same way)
    for col in ["pr_description", "pr_title"]:
        if col in df.columns:
            df[col] = df[col].fillna("")

    print(f"Missing-value handling: {before} -> {len(df)} rows (no rows dropped, imputed instead).")
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    # a PR is uniquely identified by (repository, pr_id) -- list-typed
    # columns (labels, review_decisions, etc.) make a full-row dedup
    # unhashable, so we key on the natural identifier instead.
    df = df.drop_duplicates(subset=["repository", "pr_id"], keep="first").reset_index(drop=True)
    print(f"Duplicate removal: {before} -> {len(df)} rows ({before - len(df)} duplicates dropped).")
    return df


def exclude_invalid_prs(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    valid = (
        df["pr_id"].notna()
        & df["repository"].notna()
        & df["author"].notna()
        & (df["num_commits"].fillna(0) > 0)
        & (df["num_changed_files"].fillna(0) > 0)
    )
    df = df[valid].reset_index(drop=True)
    print(f"Invalid PR exclusion: {before} -> {len(df)} rows ({before - len(df)} invalid PRs dropped).")
    return df


def normalize_features(df: pd.DataFrame) -> pd.DataFrame:
    for col in NUMERIC_COLS:
        if col in df.columns:
            mean, std = df[col].mean(), df[col].std()
            df[col + "_norm"] = (df[col] - mean) / std if std > 0 else 0.0
    print(f"Normalized {len(NUMERIC_COLS)} numeric columns (z-score, suffix '_norm').")
    return df


def check_class_balance(df: pd.DataFrame):
    counts = df["merged"].value_counts()
    total = len(df)
    print("\nClass balance (merged target):")
    for val, cnt in counts.items():
        print(f"  {val}: {cnt} ({cnt / total * 100:.1f}%)")
    ratio = counts.min() / counts.max()
    if ratio < 0.5:
        print(f"  [warn] Class imbalance detected (minority/majority ratio = {ratio:.2f}). "
              f"Consider class_weight='balanced' or resampling in train.py.")
    else:
        print(f"  Classes reasonably balanced (ratio = {ratio:.2f}).")


def outlier_analysis(df: pd.DataFrame) -> pd.DataFrame:
    print("\nOutlier analysis (IQR method):")
    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outlier_mask = (df[col] < lower) | (df[col] > upper)
        n_outliers = outlier_mask.sum()
        print(f"  {col}: {n_outliers} outliers ({n_outliers / len(df) * 100:.1f}%), bounds=[{lower:.1f}, {upper:.1f}]")
        df[col + "_is_outlier"] = outlier_mask
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", type=str, default="../../data/raw_prs.json")
    parser.add_argument("--out", type=str, default="../../data/cleaned_prs.csv")
    args = parser.parse_args()

    df = load_raw(args.in_path)
    df = handle_missing_values(df)
    df = remove_duplicates(df)
    df = exclude_invalid_prs(df)
    df = normalize_features(df)
    df = outlier_analysis(df)
    check_class_balance(df)

    # convert list-typed columns to JSON strings for CSV storage
    for col in ["review_decisions", "labels", "ai_reviewer_names", "commit_messages", "modified_files"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)

    df.to_csv(args.out, index=False)
    print(f"\nSaved cleaned dataset: {len(df)} rows, {len(df.columns)} columns -> {args.out}")


if __name__ == "__main__":
    main()

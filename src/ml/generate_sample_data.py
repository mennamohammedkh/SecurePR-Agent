"""
generate_sample_data.py
--------------------------
Generates a SYNTHETIC raw_prs.json with the exact same schema as
data_collection.py's real GitHub output, so the rest of the pipeline
(preprocessing -> feature_engineering -> train -> evaluate -> predict)
can be built and tested immediately, without a GITHUB_TOKEN.

Once your token is ready, run data_collection.py instead to overwrite
data/raw_prs.json with real data -- nothing downstream needs to change,
since the schema is identical.

USAGE:
  python generate_sample_data.py --n-per-repo 300 --out ../../data/raw_prs.json
"""

import argparse
import json
import os
import numpy as np

np.random.seed(42)

REPOS = ["facebook/react", "microsoft/vscode", "pytorch/pytorch", "pandas-dev/pandas", "vercel/next.js"]
AUTHORS = [f"dev_{i}" for i in range(1, 40)] + ["dependabot[bot]", "renovate[bot]"]
AI_REVIEWERS_POOL = ["coderabbitai[bot]", "copilot-pull-request-reviewer[bot]", None, None, None, None]
LABELS_POOL = ["bug", "enhancement", "documentation", "good first issue", "needs-review", "breaking-change"]


def random_labels():
    n = np.random.randint(0, 3)
    return list(np.random.choice(LABELS_POOL, size=n, replace=False)) if n else []


def make_record(repo, pr_id):
    ai_reviewer = np.random.choice(AI_REVIEWERS_POOL)
    ai_reviewer_present = ai_reviewer is not None
    ai_code_present = bool(np.random.rand() < 0.25)

    num_reviewers = int(np.random.randint(1, 4))
    num_reviews = num_reviewers + int(np.random.randint(0, 2))
    num_comments = int(np.random.poisson(4))
    num_commits = int(np.random.randint(1, 10))
    num_changed_files = int(np.random.randint(1, 12))
    additions = int(np.random.exponential(60))
    deletions = int(np.random.exponential(30))
    pr_desc_len = int(np.random.randint(20, 800))

    # merge probability driven mostly by review activity (realistic-ish, and
    # deliberately NOT purely a function of the size features, so downstream
    # models have a genuine — if imperfect — learning task)
    merge_prob = 1 / (1 + np.exp(0.15 * num_comments - 0.4 * num_reviewers + 0.3))
    merged = bool(np.random.rand() < merge_prob)

    created = np.datetime64("2025-01-01") + np.timedelta64(int(np.random.randint(0, 500)), "D")
    merge_hours = float(np.random.exponential(30)) if merged else None
    merged_date = (created + np.timedelta64(int(merge_hours or 0), "h")) if merged else None

    return {
        "pr_id": pr_id,
        "repository": repo,
        "pr_title": f"Fix issue #{pr_id} in module {np.random.randint(1, 20)}",
        "pr_description": ("This PR addresses a bug " * np.random.randint(1, 5))[:pr_desc_len],
        "author": str(np.random.choice(AUTHORS)),
        "created_date": str(created),
        "merged_date": str(merged_date) if merged_date is not None else None,
        "closed_date": None,
        "num_commits": num_commits,
        "num_changed_files": num_changed_files,
        "additions": additions,
        "deletions": deletions,
        "changed_lines": additions + deletions,
        "num_comments": num_comments,
        "num_reviews": num_reviews,
        "review_decisions": list(np.random.choice(["APPROVED", "CHANGES_REQUESTED", "COMMENTED"], size=num_reviews)),
        "num_reviewers": num_reviewers,
        "labels": random_labels(),
        "merged": merged,
        "merge_time_hours": merge_hours,
        "ai_reviewer_present": bool(ai_reviewer_present),
        "ai_reviewer_names": [ai_reviewer] if ai_reviewer_present else [],
        "ai_code_present": ai_code_present,
        "commit_messages": ["fix bug", "update tests"],
        "modified_files": [f"src/module_{i}.py" for i in range(min(num_changed_files, 5))],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-per-repo", type=int, default=300)
    parser.add_argument("--out", type=str, default="../../data/raw_prs.json")
    args = parser.parse_args()

    records = []
    for repo in REPOS:
        for i in range(1, args.n_per_repo + 1):
            records.append(make_record(repo, i))

    # sprinkle in a few messy rows on purpose, so preprocessing.py has
    # something real to clean (missing values, exact duplicates)
    for _ in range(15):
        idx = np.random.randint(0, len(records))
        messy = dict(records[idx])
        messy["pr_description"] = None
        messy["additions"] = None
        records.append(messy)
    records.append(dict(records[0]))  # one exact duplicate
    records.append(dict(records[1]))  # another exact duplicate

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(records, f, indent=2, default=str)

    print(f"Generated {len(records)} synthetic raw PR records -> {args.out}")


if __name__ == "__main__":
    main()

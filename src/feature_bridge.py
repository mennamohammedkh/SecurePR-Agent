"""
Person 2 (Integration) — Features بتاعة Person 1's ML model.

بعد المراجعة (بند 3 في الـchecklist): الأصل كان دايمًا بيقرّب الـfeatures
من نص الـdiff، حتى لو كانت بيانات GitHub الحقيقية متاحة. ده بالظبط
الممنوع صراحة ("ممنوع نعتمد على diff-derived approximation في النتيجة
النهائية لو GitHub metadata متاحة"). دلوقتي `build_features()`:

  1. لو عندنا pr_repo + pr_number → يجيب العدد الحقيقي من GitHub
     (commits, reviews, comments) + الـadditions/deletions/changed_files
     من pr_metadata (اللي run_agent_pipeline بيحفظه من get_pull_request).
  2. لو مفيش (اختبار synthetic زي run_demo.py، أو GitHub API فشل)
     → يرجع للتقريب من الـdiff، لكن بيسجل ml_features_source بوضوح
     عشان يبقى شفاف في التقرير مش مخفي.
"""
from typing import Dict, Tuple

from src import integration_bridge


def approximate_features_from_diff(pr_diff: str, pr_description: str) -> Dict[str, float]:
    lines = (pr_diff or "").splitlines()
    additions = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
    changed_files = max(1, sum(1 for l in lines if l.startswith("+++") or l.startswith("diff --git")))

    return {
        "pr_size": additions + deletions,
        "code_churn": additions + deletions,
        "review_activity": 0.0,
        "num_reviewers": 0.0,
        "num_commits": 1.0,
        "num_changed_files": float(changed_files),
        "additions": float(additions),
        "deletions": float(deletions),
        "pr_description_length": float(len(pr_description or "")),
        "num_comments": 0.0,
    }


def _features_from_github(pr_repo: str, pr_number: int, pr_metadata: dict, pr_description: str) -> Dict[str, float]:
    import threading

    results = {}

    def _fetch(key, fn):
        results[key] = fn(pr_repo, pr_number)

    # الـ3 نداءات دي كل واحدة فيها timeout داخلي (integration_bridge) لحد
    # 8 ثواني. لو شغّلناهم واحد ورا التاني (sequential)، أسوأ حالة ممكن
    # توصل لـ24 ثانية بس عشان الـfeatures. تشغيلهم بالتوازي (threads) يورد
    # نفس أسوأ حالة لـ~8 ثواني بس، مهم لسرعة الـDemo.
    threads = [
        threading.Thread(target=_fetch, args=("commits", integration_bridge.safe_get_commit_history)),
        threading.Thread(target=_fetch, args=("comments", integration_bridge.safe_get_pr_comments)),
        threading.Thread(target=_fetch, args=("reviews", integration_bridge.safe_get_reviews)),
    ]
    for t in threads:
        t.daemon = True
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    commits = results.get("commits", [])
    comments = results.get("comments", [])
    reviews = results.get("reviews", [])

    reviewers = {r.get("author") for r in reviews if r.get("author")}
    additions = (pr_metadata or {}).get("additions", 0) or 0
    deletions = (pr_metadata or {}).get("deletions", 0) or 0
    changed_files = (pr_metadata or {}).get("changed_files", 0) or 0

    return {
        "pr_size": float(additions + deletions),
        "code_churn": float(additions + deletions),
        "review_activity": float(len(reviews) + len(comments)),
        "num_reviewers": float(len(reviewers)),
        "num_commits": float(len(commits)) or 1.0,
        "num_changed_files": float(changed_files) or 1.0,
        "additions": float(additions),
        "deletions": float(deletions),
        "pr_description_length": float(len(pr_description or "")),
        "num_comments": float(len(comments)),
    }


def build_features(
    pr_diff: str,
    pr_description: str,
    pr_repo: str = "",
    pr_number: int = None,
    pr_metadata: dict = None,
) -> Tuple[Dict[str, float], str]:
    """
    بترجع (features, source) — الـsource قيمتها "github_real" أو
    "diff_approximation"، عشان الشفافية في الـfinal_response/التقرير.
    """
    has_real_metadata = bool(pr_repo and pr_number and pr_metadata and "error" not in (pr_metadata or {}))
    if has_real_metadata:
        return _features_from_github(pr_repo, pr_number, pr_metadata, pr_description), "github_real"
    return approximate_features_from_diff(pr_diff, pr_description), "diff_approximation"

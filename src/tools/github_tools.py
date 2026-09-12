"""
github_tools.py
================
Person 5 - RAG / Tools / UI Owner
GitHub Tools: أدوات الاتصال بـ GitHub API عشان الـAgents تقدر تجيب معلومات عن الـPull Requests.

بيستخدم PyGithub (github.Github) لو الـtoken موجود، وبيرجع requests كـfallback
لو حابب تستخدم REST API مباشرة بدل الـlibrary.

Environment Variables المطلوبة:
    GITHUB_TOKEN : Personal Access Token عشان الـAuthentication مع GitHub API
"""

import os
import threading
import requests
from github import Github, GithubException

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API_BASE = "https://api.github.com"
GITHUB_CALL_TIMEOUT_SEC = 8.0

_github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()


def _run_bounded(fn, *args, timeout: float = GITHUB_CALL_TIMEOUT_SEC, default=None, **kwargs):
    """
    Person 2 (Integration) — طبقة حماية دخل github_tools.py نفسه.

    اكتشفنا (بمحاكاة فعلية عن طريق Streamlit's AppTest) إن ui/app.py بينادي
    get_pull_request() مباشرة (مش عن طريق pipeline بتاعنا)، وده معناه إن
    حماية الـtimeout اللي حطيناها في src/integration_bridge.py كانت
    بتحمي بس النداءات الجاية من جوه run_agent_pipeline، لكن مكنتش بتحمي
    أي نداء مباشر تاني (زي اللي في الـUI). النتيجة: زرار "Analyze PR"
    كان ممكن يعلّق فعليًا لدقايق طويلة (نفس مشكلة الـ403 backoff اللي
    شفناها قبل كده) لأن PyGithub بيحسب backoff داخلي طويل قبل ما يرجّع.

    الحل الصح: الحماية تتحط هنا في المصدر نفسه (جوه github_tools.py) عشان
    أي حد يستخدم الدوال دي — الـUI، الـpipeline، أو أي Tool تاني بعدين —
    يستفيد من نفس الحماية أوتوماتيك من غير ما يحتاج يتذكر يلفها بنفسه.
    """
    result_box: dict = {}

    def _runner():
        try:
            result_box["value"] = fn(*args, **kwargs)
        except Exception as exc:
            result_box["error"] = exc

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        return default
    if "error" in result_box:
        return default
    return result_box.get("value", default)


def _headers():
    """يبني الـheaders اللي محتاجينها لأي request مباشر لـGitHub REST API."""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _get_pull_request_impl(repo_name: str, pr_number: int) -> dict:
    try:
        repo = _github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        return {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "state": pr.state,
            "user": pr.user.login if pr.user else None,
            "base": pr.base.ref,
            "head": pr.head.ref,
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
            "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
            "mergeable": pr.mergeable,
            "merged": pr.merged,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "html_url": pr.html_url,
        }
    except GithubException as e:
        return {"error": str(e)}


def get_pull_request(repo_name: str, pr_number: int) -> dict:
    """
    بترجع تفاصيل الـPull Request نفسه (العنوان، الوصف، الحالة، الـauthor، ...).

    Args:
        repo_name: اسم الـrepository بصيغة "owner/repo"
        pr_number: رقم الـPR

    Returns:
        dict فيه بيانات الـPR، أو {"error": "..."} لو فشل أو استغرق أكتر
        من GITHUB_CALL_TIMEOUT_SEC ثانية (Integration safety net).
    """
    return _run_bounded(
        _get_pull_request_impl, repo_name, pr_number,
        default={"error": f"Timed out after {GITHUB_CALL_TIMEOUT_SEC}s or GitHub API unreachable."},
    )


def _get_pr_diff_impl(repo_name: str, pr_number: int) -> str:
    url = f"{GITHUB_API_BASE}/repos/{repo_name}/pulls/{pr_number}"
    headers = _headers()
    headers["Accept"] = "application/vnd.github.v3.diff"
    response = requests.get(url, headers=headers, timeout=GITHUB_CALL_TIMEOUT_SEC)
    if response.status_code == 200:
        return response.text
    return f"Error fetching diff: {response.status_code} - {response.text}"


def get_pr_diff(repo_name: str, pr_number: int) -> str:
    """
    بترجع الـdiff الكامل للـPR (raw diff) عشان الـCode Review Agent يقرأه.

    Args:
        repo_name: اسم الـrepository بصيغة "owner/repo"
        pr_number: رقم الـPR

    Returns:
        str فيه الـdiff, أو رسالة خطأ (بما فيها timeout)
    """
    return _run_bounded(
        _get_pr_diff_impl, repo_name, pr_number,
        default=f"Error fetching diff: timed out after {GITHUB_CALL_TIMEOUT_SEC}s.",
    )


def _get_changed_files_impl(repo_name: str, pr_number: int) -> list:
    try:
        repo = _github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        files = []
        for f in pr.get_files():
            files.append({
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "patch": f.patch,
            })
        return files
    except GithubException as e:
        return [{"error": str(e)}]


def get_changed_files(repo_name: str, pr_number: int) -> list:
    """
    بترجع لستة بالملفات اللي اتغيرت في الـPR مع نوع التغيير (added/modified/removed)
    وعدد الـadditions/deletions لكل ملف.

    Args:
        repo_name: اسم الـrepository بصيغة "owner/repo"
        pr_number: رقم الـPR

    Returns:
        list[dict]
    """
    return _run_bounded(
        _get_changed_files_impl, repo_name, pr_number,
        default=[{"error": f"Timed out after {GITHUB_CALL_TIMEOUT_SEC}s or GitHub API unreachable."}],
    )


def _get_commit_history_impl(repo_name: str, pr_number: int) -> list:
    try:
        repo = _github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        commits = []
        for c in pr.get_commits():
            commits.append({
                "sha": c.sha,
                "message": c.commit.message,
                "author": c.commit.author.name if c.commit.author else None,
                "date": c.commit.author.date.isoformat() if c.commit.author else None,
            })
        return commits
    except GithubException as e:
        return [{"error": str(e)}]


def get_commit_history(repo_name: str, pr_number: int) -> list:
    """
    بترجع الـcommits اللي حصلت جوه الـPR بالترتيب.

    Args:
        repo_name: اسم الـrepository بصيغة "owner/repo"
        pr_number: رقم الـPR

    Returns:
        list[dict]
    """
    return _run_bounded(
        _get_commit_history_impl, repo_name, pr_number,
        default=[{"error": f"Timed out after {GITHUB_CALL_TIMEOUT_SEC}s or GitHub API unreachable."}],
    )


def _get_pr_comments_impl(repo_name: str, pr_number: int) -> list:
    try:
        repo = _github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        comments = []
        for c in pr.get_issue_comments():
            comments.append({
                "author": c.user.login if c.user else None,
                "body": c.body,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })
        for c in pr.get_review_comments():
            comments.append({
                "author": c.user.login if c.user else None,
                "body": c.body,
                "path": c.path,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })
        return comments
    except GithubException as e:
        return [{"error": str(e)}]


def get_pr_comments(repo_name: str, pr_number: int) -> list:
    """
    بترجع الـcomments العادية على الـPR (issue comments + review comments).

    Args:
        repo_name: اسم الـrepository بصيغة "owner/repo"
        pr_number: رقم الـPR

    Returns:
        list[dict]
    """
    return _run_bounded(
        _get_pr_comments_impl, repo_name, pr_number,
        default=[{"error": f"Timed out after {GITHUB_CALL_TIMEOUT_SEC}s or GitHub API unreachable."}],
    )


def _get_reviews_impl(repo_name: str, pr_number: int) -> list:
    try:
        repo = _github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        reviews = []
        for r in pr.get_reviews():
            reviews.append({
                "author": r.user.login if r.user else None,
                "state": r.state,
                "body": r.body,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            })
        return reviews
    except GithubException as e:
        return [{"error": str(e)}]


def get_reviews(repo_name: str, pr_number: int) -> list:
    """
    بترجع الـReviews الرسمية على الـPR (approved / changes_requested / commented)
    مع اسم المراجع والحالة والتعليق.

    Args:
        repo_name: اسم الـrepository بصيغة "owner/repo"
        pr_number: رقم الـPR

    Returns:
        list[dict]
    """
    return _run_bounded(
        _get_reviews_impl, repo_name, pr_number,
        default=[{"error": f"Timed out after {GITHUB_CALL_TIMEOUT_SEC}s or GitHub API unreachable."}],
    )


def _get_repository_file_impl(repo_name: str, file_path: str, ref: str = None) -> str:
    try:
        repo = _github_client.get_repo(repo_name)
        content_file = repo.get_contents(file_path, ref=ref) if ref else repo.get_contents(file_path)
        return content_file.decoded_content.decode("utf-8", errors="replace")
    except GithubException as e:
        return f"Error fetching file: {str(e)}"


def get_repository_file(repo_name: str, file_path: str, ref: str = None) -> str:
    """
    بترجع محتوى ملف معين من الـrepository (مش بس الـdiff).
    مفيد لما الـAgent يحتاج يعرف "الـfunction دي بتتستخدم فين" في باقي الكود.

    Args:
        repo_name: اسم الـrepository بصيغة "owner/repo"
        file_path: مسار الملف جوه الـrepo
        ref: اسم الـbranch أو الـcommit sha (اختياري، افتراضيًا default branch)

    Returns:
        str فيه محتوى الملف, أو رسالة خطأ (بما فيها timeout)
    """
    return _run_bounded(
        _get_repository_file_impl, repo_name, file_path, ref=ref,
        default=f"Error fetching file: timed out after {GITHUB_CALL_TIMEOUT_SEC}s.",
    )

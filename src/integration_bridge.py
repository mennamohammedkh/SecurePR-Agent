"""
Person 2 (Integration) — طبقة حماية حوالين أدوات Person 5.

اكتشفنا أثناء الاختبار إن:
  1. src.tools.github_tools بينادي GitHub API من غير GITHUB_TOKEN. لو حصل
     403 (rate limit)، PyGithub بيعمل retry بـbackoff ممكن يوصل لعشرات
     الدقايق (شفنا intentar واحد وصل لـ~31 دقيقة!). ده لو سيبناه من غير
     حماية، الـGraph كله ممكن "يعلّق" لمدة طويلة جدًا على PR واحد بس.
  2. src.tools.rag_search محتاج ملفات حقيقية جوه knowledge/OWASP,
     knowledge/CWE, knowledge/secure_coding (لسه فاضيين غير .gitkeep)
     + embedding provider (LlamaIndex افتراضيًا محتاج OPENAI_API_KEY).
     لحد ما الاتنين يتوفروا، أي نداء بيرمي Exception.

عشان الـGraph يفضل شغال ومايعلقش، كل نداء لأدوات Person 5 هنا بيعدي من خلال
`_with_timeout()` وبيرجع fallback واضح بدل ما يعلق أو يوقع الـGraph كله.
"""
import threading
from typing import Any, Callable, Optional


def _with_timeout(fn: Callable, *args, timeout: float = 6.0, default: Any = None, **kwargs):
    """
    بتنادي fn(*args, **kwargs) بس بحد أقصى `timeout` ثانية. لو عدّى الوقت
    أو حصل أي Exception، بترجع `default` بدل ما توقف أو تعلّق كل الـGraph.

    ملحوظة مهمة اتكشفت بالاختبار الفعلي: أول نسخة من الدالة دي كانت
    مستخدمة concurrent.futures.ThreadPoolExecutor (thread pool ثابت).
    الـtimeout بتاعنا كان شغال صح (الكود بيكمل بعد 6 ثواني زي المتوقع)،
    لكن الـpool نفسه كان بيفضل حي (threads مش daemon) وده كان بيمنع الـ
    process كله من الخروج (hang عند exit) لحد ما الـGitHub retry
    backoff الداخلي (شفنا ~31-49 دقيقة!) يخلص. الحل: نستخدم daemon
    thread مستقل لكل نداء بدل thread pool ثابت، عشان الـprocess يقدر
    يخرج فورًا حتى لو الـthread الأصلي لسه شغال في الخلفية.
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
        return default  # لسه شغال بعد الـtimeout — منستناش، نرجّع fallback
    if "error" in result_box:
        return default
    return result_box.get("value", default)


# ---------------------------------------------------------------------------
# GitHub-backed context (يحتاج شبكة فعلية + مثاليًا GITHUB_TOKEN)
# ---------------------------------------------------------------------------
def safe_get_repository_context(repo_name: str, pr_number: int) -> str:
    from src.tools.repository_tools import get_repository_context

    result = _with_timeout(get_repository_context, repo_name, pr_number, timeout=6.0, default=None)
    if not result:
        return ""

    changed = result.get("changed_files", [])
    if changed and isinstance(changed, list) and "error" not in changed[0]:
        names = ", ".join(f.get("filename", "?") for f in changed[:10])
        return f"Changed files: {names}"
    return ""


# ---------------------------------------------------------------------------
# RAG search (يحتاج ملفات حقيقية في knowledge/ + embedding provider)
# ---------------------------------------------------------------------------
def safe_search_security_knowledge(query_text: str, top_k: int = 3) -> list:
    from src.tools.rag_search import search_security_knowledge

    return _with_timeout(search_security_knowledge, query_text, top_k, timeout=8.0, default=[]) or []


def safe_search_historical_reviews(query_text: str, top_k: int = 3) -> list:
    from src.tools.rag_search import search_historical_reviews

    return _with_timeout(search_historical_reviews, query_text, top_k, timeout=8.0, default=[]) or []


# ---------------------------------------------------------------------------
# GitHub PR fetch (للاستخدام من run_agent_pipeline نفسها)
# ---------------------------------------------------------------------------
def safe_get_pull_request(repo_name: str, pr_number: int) -> Optional[dict]:
    from src.tools.github_tools import get_pull_request

    result = _with_timeout(get_pull_request, repo_name, pr_number, timeout=8.0, default=None)
    if result is None or "error" in result:
        return None
    return result


def safe_get_pr_diff(repo_name: str, pr_number: int) -> str:
    from src.tools.github_tools import get_pr_diff

    return _with_timeout(get_pr_diff, repo_name, pr_number, timeout=8.0, default="") or ""


def safe_get_commit_history(repo_name: str, pr_number: int) -> list:
    from src.tools.github_tools import get_commit_history

    result = _with_timeout(get_commit_history, repo_name, pr_number, timeout=8.0, default=[])
    return [] if not result or (result and "error" in result[0]) else result


def safe_get_pr_comments(repo_name: str, pr_number: int) -> list:
    from src.tools.github_tools import get_pr_comments

    result = _with_timeout(get_pr_comments, repo_name, pr_number, timeout=8.0, default=[])
    return [] if not result or (result and "error" in result[0]) else result


def safe_get_reviews(repo_name: str, pr_number: int) -> list:
    from src.tools.github_tools import get_reviews

    result = _with_timeout(get_reviews, repo_name, pr_number, timeout=8.0, default=[])
    return [] if not result or (result and "error" in result[0]) else result


# ---------------------------------------------------------------------------
# Incident logging (Person 5: src/tools/incident_logger.py)
# ---------------------------------------------------------------------------
def safe_log_incident(attack_type: str, severity: str, risk_score: float, decision: str) -> None:
    from src.tools.incident_logger import log_incident

    _with_timeout(log_incident, attack_type, severity, risk_score, decision, timeout=3.0, default=None)

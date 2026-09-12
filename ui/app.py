"""
app.py
=======
Person 5 - RAG / Tools / UI Owner
UI - Dashboard (Streamlit)

المستخدم يدخل Repository + PR Number ويضغط "Analyze PR" ويشوف:
    - Pull Request Header
    - Merge Probability / Security Risk / Issues Found / Prompt Injection
    - Review Comments
    - Agent Trace: Supervisor -> Security Agent -> RAG -> Code Review Agent
                   -> Reflection -> Final Review

الـDashboard بيعتمد على:
    1) src.tools.github_tools  : بيانات الـPR الحقيقية من GitHub
    2) src.tools.static_analysis: نتائج Static Analysis (Semgrep/Bandit)
    3) src.tools.rag_search    : Semantic Search على الـKnowledge Base
    4) src.tools.incident_logger: تسجيل أي incident أمني ظهر
    5) الـAgent Pipeline (Supervisor -> ... -> Final Review) بتاع باقي الفريق،
       لو موجودة (src.agents.supervisor.run_agent_pipeline). لو لسه مش جاهزة،
       الـDashboard بيوريك نتيجة demo عشان تقدر تجرب شكل الـUI بدري.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

from src.tools.github_tools import get_pull_request
from src.tools.static_analysis import run_static_analysis
from src.tools.rag_search import search_historical_reviews
from src.tools.incident_logger import log_incident, get_all_incidents

st.set_page_config(page_title="Secure Agentic Code Review", layout="wide")


def run_agent_pipeline(repo_name: str, pr_number: int) -> dict:
    """
    بتنادي الـAgent Pipeline الكامل بتاع الفريق (Supervisor -> Security Agent
    -> RAG -> Code Review Agent -> Reflection -> Final Review) لو موجودة.
    لو الـpipeline لسه ماتبنتش من باقي الفريق، بترجع نتيجة demo بنفس الشكل
    عشان الـUI يفضل شغال ومتربوط صح مع باقي المشروع.
    """
    try:
        from src.agents.supervisor import run_agent_pipeline as _real_pipeline
        return _real_pipeline(repo_name, pr_number)
    except ImportError:
        return {
            "merge_probability": 78,
            "security_risk": "HIGH",
            "issues_found": 4,
            "prompt_injection": "Not Found",
            "review_comments": [
                {"severity": "HIGH", "message": "SQL Injection"},
                {"severity": "MEDIUM", "message": "Missing validation"},
                {"severity": "LOW", "message": "Code duplication"},
            ],
            "agent_trace": [
                "Supervisor", "Security Agent", "RAG",
                "Code Review Agent", "Reflection", "Final Review",
            ],
        }


def render_header(pr_number: int, result: dict):
    """بتعرض الـheader بتاع نتيجة تحليل الـPR."""
    st.markdown(f"### Pull Request #{pr_number}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Merge Probability", f"{result['merge_probability']}%")
    col2.metric("Security Risk", result["security_risk"])
    col3.metric("Issues Found", result["issues_found"])
    col4.metric("Prompt Injection", result["prompt_injection"])


def render_review_comments(review_comments: list):
    """بتعرض لستة الـReview Comments مرتبة حسب الخطورة."""
    st.markdown("#### Review Comments")
    for i, comment in enumerate(review_comments, start=1):
        st.write(f"{i}. **{comment['severity']}** — {comment['message']}")


def render_agent_trace(agent_trace: list):
    """بتعرض مسار الـAgents اللي اشتغلوا على الـPR (Supervisor -> ... -> Final Review)."""
    st.markdown("#### Agent Trace")
    st.write(" → ".join(agent_trace))


def render_incidents():
    """بتعرض الـSecurity Incidents المسجلة (log_incident) لو موجودة."""
    incidents = get_all_incidents()
    if not incidents:
        return
    st.markdown("#### Security Incidents")
    st.table(incidents)


def main():
    st.title("🏢 Secure Agentic Code Review")
    st.caption("Person 5 — RAG + Tools + GitHub Integration + UI")

    with st.form("analyze_pr_form"):
        repo_name = st.text_input("Repository (owner/repo)", placeholder="e.g. octocat/Hello-World")
        pr_number = st.number_input("PR Number", min_value=1, step=1, value=1)
        submitted = st.form_submit_button("Analyze PR")

    if not submitted:
        return

    if not repo_name:
        st.error("من فضلك دخّل اسم الـrepository.")
        return

    with st.spinner("جاري تحليل الـPull Request..."):
        pr_data = get_pull_request(repo_name, int(pr_number))

        if "error" in pr_data:
            st.error(f"مقدرناش نجيب بيانات الـPR: {pr_data['error']}")
            return

        result = run_agent_pipeline(repo_name, int(pr_number))

        if result.get("prompt_injection") not in (None, "Not Found"):
            log_incident(
                attack_type="prompt_injection",
                severity=result.get("security_risk", "unknown").lower(),
                risk_score=0.0,
                decision="flagged",
            )

    render_header(int(pr_number), result)
    render_review_comments(result["review_comments"])
    render_agent_trace(result["agent_trace"])
    render_incidents()

    with st.expander("Historical Reviews (RAG)"):
        similar_reviews = search_historical_reviews(pr_data.get("title", ""))
        if similar_reviews:
            for review in similar_reviews:
                st.write(review.get("text", ""))
        else:
            st.write("مفيش historical reviews شبيهة لسه.")

    with st.expander("Static Analysis (Semgrep)"):
        findings = run_static_analysis(code=pr_data.get("body") or "", tool="semgrep")
        st.json(findings)


if __name__ == "__main__":
    main()

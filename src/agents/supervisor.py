"""
run_agent_pipeline(repo_name, pr_number) — دي بالظبط النقطة اللي ui/app.py
بتاع Person 5 مستنياها (شوفي app.py: `from src.agents.supervisor import
run_agent_pipeline`). لما الملف ده موجود، الـDashboard بيشتغل بالـpipeline
الحقيقي بتاعنا تلقائيًا بدل نتيجة الـdemo الوهمية.

الشكل اللي لازم نرجعه (زي ما app.py متوقع بالظبط):
{
    "merge_probability": float (0-100, نسبة مئوية),
    "security_risk": str ("HIGH"/"MEDIUM"/"LOW"/...),
    "issues_found": int,
    "prompt_injection": "Not Found" أو نص الوصف لو اتكشف حاجة,
    "review_comments": [{"severity": str, "message": str}, ...],
    "agent_trace": [str, ...],
}
"""
from typing import Any, Dict

from src.workflow import app
from src.integration_bridge import safe_get_pull_request, safe_get_pr_diff


def _build_agent_trace(result: Dict[str, Any]) -> list:
    if result.get("input_guardrail_result", {}).get("is_blocked"):
        return ["Input Guardrail (BLOCKED)"]

    trace = ["Input Guardrail", "Supervisor"]
    agents = result.get("agents_required", []) or []
    if "code_review" in agents:
        trace.append("Code Review Agent")
    if "security" in agents:
        trace += ["Security Agent", "Reflection"]
    if "context" in agents:
        trace.append("Context / RAG Agent")
    trace += ["Risk / Merge"]
    if result.get("decision") == "MANUAL_REVIEW_REQUIRED":
        trace.append("Manual Review (Tool Failure)")
    trace.append("Output Guardrail")
    return trace


def run_agent_pipeline(repo_name: str, pr_number: int) -> Dict[str, Any]:
    pr_data = safe_get_pull_request(repo_name, pr_number)
    pr_diff = safe_get_pr_diff(repo_name, pr_number)

    initial_state = {
        "pr_url": f"github.com/{repo_name}/pull/{pr_number}",
        "pr_repo": repo_name,
        "pr_number": pr_number,
        "pr_title": (pr_data or {}).get("title", ""),
        "pr_description": (pr_data or {}).get("body", "") or "",
        "pr_diff": pr_diff or "",
        "pr_metadata": pr_data or {},
        "errors": [],
    }

    result = app.invoke(initial_state)

    review_comments = [
        {"severity": i.get("severity", "?").upper(), "message": i.get("description", "")}
        for i in result.get("code_review_result", {}).get("issues", [])
    ] + [
        {"severity": v.get("severity", "?"), "message": v.get("threat_type", "")}
        for v in result.get("confirmed_vulnerabilities", [])
    ]

    input_blocked = result.get("input_guardrail_result", {}).get("is_blocked")
    prompt_injection = (
        f"Found: {result['input_guardrail_result'].get('threats')}" if input_blocked else "Not Found"
    )

    merge_prob = result.get("ml_merge_prediction", {}).get("merge_probability")
    merge_pct = round(merge_prob * 100, 1) if merge_prob is not None else 0

    return {
        "merge_probability": merge_pct,
        "security_risk": result.get("severity", "UNKNOWN"),
        "issues_found": len(review_comments),
        "prompt_injection": prompt_injection,
        "review_comments": review_comments,
        "agent_trace": _build_agent_trace(result),
        "rag_sources": result.get("final_response", {}).get("rag_sources", []) if isinstance(result.get("final_response"), dict) else [],
        # extra fields (not required by the current UI, but useful for
        # anyone who wants to render more detail later)
        "decision": result.get("decision"),
        "ml_merge_probability": merge_prob,
        "llm_merge_probability": result.get("llm_merge_prediction", {}).get("merge_probability"),
        "ml_features_source": result.get("ml_features_source"),
        "final_response": result.get("final_response"),
    }

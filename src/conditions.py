from typing import List
from langgraph.types import Send

from src.state import AgentState
from src.nodes import _is_blocked


# ---------------- بعد Input Guardrail ----------------
def route_after_input_guardrail(state: AgentState) -> str:
    return "blocked" if _is_blocked(state) else "continue"


# ---------------- بعد Supervisor (الـ Routing الحقيقي، Send-based) ----------------
_AGENT_NODE_MAP = {
    "code_review": "code_review",
    "security": "security",
    "context": "context",
}


def route_supervisor(state: AgentState) -> List[Send]:
    agents = state.get("agents_required", []) or []
    sends = [Send(_AGENT_NODE_MAP[a], state) for a in agents if a in _AGENT_NODE_MAP]
    return sends if sends else [Send("risk_merge", state)]


# ---------------- بعد Risk/Merge ----------------
def route_after_risk(state: AgentState) -> str:
    """
    Edge Case 2 (Tool Failure): لو الـSecurity Agent فشل فعليًا (scan_code
    رفع Exception)، منسيبش الـPR يعدي عادي على Output Guardrail وكأن حاجة
    مفيهاش. بنوجهه على manual_review أولاً (log صريح) قبل ما يوصل للنتيجة
    النهائية — بالظبط Edge Case 2 اللي Person 4 عمله test له
    (test_tool_failure.py).
    """
    if state.get("decision") == "MANUAL_REVIEW_REQUIRED":
        return "tool_failure"
    return "normal"

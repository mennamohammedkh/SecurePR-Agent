"""
Supervisor — بيقرر أي Agents مطلوبة، ويحط قراره في agents_required.

Phase B (بعد ما كان heuristic بس): دلوقتي بينادي LLM حقيقي عشان يقرر
(مش if/else ثابت) — باستخدام نفس الـLLM client بتاع Person 3
(src/review/llm_client.py) عشان:
  1. مانكررش منطق "استدعاء Anthropic + MOCK_MODE" مرتين في المشروع.
  2. لما الفريق يحط ANTHROPIC_API_KEY، الاتنين (Code Review + Supervisor)
     يشتغلوا بـLLM حقيقي مرة واحدة، من غير أي تعديل تاني.

لو مفيش API key (MOCK_MODE) أو الـLLM رجّع حاجة مش قابلة للـparsing بالشكل
المتوقع، بنرجع تلقائيًا للـheuristic (decide_heuristic) — فشل آمن، مش
توقف. ده بالظبط نفس فلسفة "fail closed" اللي طبقناها في باقي الـIntegration
(security_node, integration_bridge).
"""
from typing import Dict
from src.state import AgentState
from src.review.llm_client import call_llm, extract_json


# ---------------------------------------------------------------------------
# Heuristic fallback (كان هو الأساسي قبل كده — دلوقتي fallback بس)
# ---------------------------------------------------------------------------
def decide_heuristic(state: AgentState) -> Dict:
    diff = (state.get("pr_diff") or "").lower()

    agents_required = ["code_review"]  # بيشتغل دايمًا
    if any(k in diff for k in ["auth", "password", "token", "sql", "execute(", "eval("]):
        agents_required.append("security")
    if any(k in diff for k in ["import ", "from ", "database", "config"]):
        agents_required.append("context")

    reason = f"[heuristic] PR analysis → agents required: {agents_required}"
    return {"agents_required": agents_required, "supervisor_decision": reason}


# ---------------------------------------------------------------------------
# LLM-based decision (Phase B)
# ---------------------------------------------------------------------------
_ROUTING_PROMPT = """You are the supervisor node of a secure code-review agent \
pipeline. Given a pull request's diff and description, decide which \
specialist agents are needed for this specific PR.

Available agents:
- "security": scans for vulnerabilities (SQL injection, hardcoded secrets, \
auth bypass, command injection, etc.). Needed whenever the diff touches \
authentication, authorization, raw queries, external commands, secrets, \
or otherwise looks security-sensitive.
- "context": fetches related repository files/history for extra context. \
Needed when the change depends on understanding surrounding code (e.g. \
touches shared config, imports from other modules, or database schema).

The "code_review" agent always runs regardless of your decision, so do not \
include it.

PR title: {title}
PR description: {description}
PR diff:
{diff}

Respond with ONLY a JSON object, no other text:
{{"security": true or false, "context": true or false, "reasoning": "one short sentence"}}
"""


def decide_llm(state: AgentState) -> Dict:
    prompt = _ROUTING_PROMPT.format(
        title=state.get("pr_title", ""),
        description=state.get("pr_description", ""),
        diff=(state.get("pr_diff") or "")[:4000],  # قص لأي diff ضخم عشان نتحكم في الـtoken cost
    )
    response = call_llm(prompt, max_tokens=200)
    parsed = extract_json(response["text"])

    if not parsed or "security" not in parsed or "context" not in parsed:
        # الـLLM رجّع حاجة مش بالشكل المتوقع (أو إحنا في MOCK_MODE ورجعلنا
        # شكل تاني خالص زي {"issues": ...}) — نرجع للـheuristic بدل ما نوقع.
        fallback = decide_heuristic(state)
        fallback["supervisor_decision"] += " (LLM parse failed, used heuristic fallback)"
        return fallback

    agents_required = ["code_review"]
    if parsed.get("security"):
        agents_required.append("security")
    if parsed.get("context"):
        agents_required.append("context")

    reason = f"[LLM] {parsed.get('reasoning', 'no reasoning given')} → agents required: {agents_required}"
    return {"agents_required": agents_required, "supervisor_decision": reason}


# ---------------------------------------------------------------------------
# نقطة الدخول اللي nodes.py بينادي عليها
# ---------------------------------------------------------------------------
def decide(state: AgentState) -> Dict:
    try:
        return decide_llm(state)
    except Exception as exc:
        fallback = decide_heuristic(state)
        fallback["supervisor_decision"] += f" (LLM call raised {type(exc).__name__}, used heuristic fallback)"
        return fallback

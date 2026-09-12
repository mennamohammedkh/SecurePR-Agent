"""
كل node بتاخد AgentState وترجع dict فيه بس المفاتيح اللي غيّرتها.

بعد الـ Integration: بدل الـstubs، دلوقتي بننادي كود الفريق الحقيقي:
  - Person 1 (src/ml/predict.py)              -> ML merge prediction
  - Person 3 (src/review/*.py)                 -> LLM code review + LLM merge prediction
  - Person 4 (src/guardrails, src/security,
              src/reflection)                  -> Input/Output guardrails, security scan, reflection, risk
  - Person 5 (src/tools, src/rag)              -> GitHub context, RAG search, incident logging
    (عن طريق src/integration_bridge.py اللي بيحط timeout + fallback حوالين
    كل نداء شبكة/RAG عشان الـGraph مايعلقش لو الأداة بطيئة أو مش جاهزة).
"""
from src.state import AgentState
from src.supervisor import decide as supervisor_decide
from src.feature_bridge import build_features
from src import integration_bridge

# ---- Person 1 ----
from src.ml.predict import predict_merge as ml_predict_merge

# ---- Person 3 ----
from src.review.code_review_agent import review_code as llm_review_code
from src.review.merge_predictor import predict_merge_llm

# ---- Person 4 ----
from src.guardrails.input_guardrail import InputGuardrail
from src.guardrails.output_guardrail import OutputGuardrail
from src.security.security_agent import SecurityAgent
from src.reflection.reflection_agent import ReflectionAgent
from src.security.risk_engine import RiskEngine

_input_guardrail = InputGuardrail()
_output_guardrail = OutputGuardrail()
_security_agent = SecurityAgent()
_reflection_agent = ReflectionAgent()
_risk_engine = RiskEngine()


def _is_blocked(state: AgentState) -> bool:
    return bool(state.get("input_guardrail_result", {}).get("is_blocked"))


# ---------------- Input Guardrail (Person 4: InputGuardrail) ----------------
def input_guardrail_node(state: AgentState) -> dict:
    result = _input_guardrail.inspect_input({
        "description": state.get("pr_description", ""),
        "code_diff": state.get("pr_diff", ""),
    })
    errors = list(state.get("errors", []))
    if result["is_blocked"]:
        errors.append(f"input_guardrail: blocked ({result['threats']})")
    return {"input_guardrail_result": result, "errors": errors}


# ---------------- Blocked terminal path (Edge Case 1) ----------------
def blocked_end_node(state: AgentState) -> dict:
    g = state.get("input_guardrail_result", {})
    integration_bridge.safe_log_incident(
        attack_type="prompt_injection",
        severity="high",
        risk_score=g.get("risk_score", 1.0),
        decision="blocked",
    )
    return {
        "decision": "BLOCK",
        "severity": "HIGH",
        "risk_score": g.get("risk_score", 1.0),
        "final_response": f"Decision: BLOCK | Reason: input guardrail — {g.get('threats')} | Comments: none",
    }


# ---------------- Supervisor ----------------
def supervisor_node(state: AgentState) -> dict:
    return supervisor_decide(state)


# ---------------- Code Review (Person 3: review_code) ----------------
def code_review_node(state: AgentState) -> dict:
    context = {
        "diff": state.get("pr_diff", ""),
        "pr_description": state.get("pr_description", ""),
        "commit_message": "",  # TODO (Person 5): commit message حقيقي لما GitHub tools تجهز
        "repository_context": state.get("repository_context", ""),
    }
    try:
        result = llm_review_code(context)
    except Exception as exc:
        # مكنش فيه أي حماية هنا قبل كده — أي فشل حقيقي في الـLLM call
        # (rate limit, network, انقطاع الخدمة) كان هيوقّع الـGraph كله.
        # دلوقتي fail-closed زي security_node بالظبط: مش "تنضيف تلقائي".
        result = {
            "issues": [],
            "summary": "",
            "confidence": 0.0,
            "tool_error": True,
            "error_message": f"{type(exc).__name__}: {exc}",
        }
    return {"code_review_result": result}


# ---------------- Security (Person 4: SecurityAgent + Person 5: RAG guidance) ----------------
def security_node(state: AgentState) -> dict:
    """
    ملحوظة Integration: SecurityAgent.scan_code() الأصلي عنده try/except
    داخلي بيرجّع tool_error=True لو الـclassifier نفسه فشل. لكن كـSupervisor
    integration owner، بنحط طبقة حماية تانية هنا كمان — لو أي حاجة غير
    متوقعة حصلت (مثلاً الـSecurityAgent نفسه اتعطل/رمى exception مش متوقع
    جوه scan_code)، الـGraph لازم يفشل closed (TOOL_FAILURE) مش يوقع
    بالكامل أو يفترض إن الكود نضيف.
    """
    try:
        result = _security_agent.scan_code(state.get("pr_diff", ""))
    except Exception as exc:
        result = {
            "vulnerabilities": [],
            "security_status": "TOOL_FAILURE",
            "total_findings": 0,
            "tool_error": True,
            "error_message": f"{type(exc).__name__}: {exc}",
        }

    # Person 5 RAG: نضيف مراجع خارجية إضافية (OWASP/CWE) فوق guidance
    # Person 4 المحلي، لو الـKnowledge Base والـembedding provider جاهزين.
    # (دلوقتي بترجع [] لأن knowledge/ لسه فاضي — شوفي الـREADME.)
    if result.get("vulnerabilities"):
        # threat_type بيجي بصيغة "SQL_INJECTION" (underscore)، لكن مستندات
        # المعرفة مكتوبة بلغة طبيعية "SQL Injection" (مسافة). لو سبناها
        # underscore، الـembedding المحلي (hashing-based) مش هيلاقي تطابق
        # خالص لأن "sql_injection" و"sql injection" tokens مختلفة تمامًا.
        query = ", ".join(
            v.get("threat_type", "").replace("_", " ").lower() for v in result["vulnerabilities"]
        )
        result["external_references"] = integration_bridge.safe_search_security_knowledge(query)

    return {"security_result": result}


# ---------------- Context (Person 5: repository_tools + RAG historical reviews) ----------------
def context_node(state: AgentState) -> dict:
    repo = state.get("pr_repo", "")
    pr_number = state.get("pr_number")

    repository_context = ""
    if repo and pr_number:
        repository_context = integration_bridge.safe_get_repository_context(repo, pr_number)

    query = state.get("pr_title", "") or state.get("pr_description", "")
    historical = integration_bridge.safe_search_historical_reviews(query) if query else []

    return {
        "repository_context": repository_context,
        "retrieved_context": historical,
    }


# ---------------- Reflection (Person 4: ReflectionAgent + RiskEngine) ----------------
def reflection_node(state: AgentState) -> dict:
    """
    بتتنادى فورًا بعد security_node (مش بعد risk_merge زي أول تصميم) —
    ده تصحيح بعد المراجعة: تصميم Person 4 الأصلي بيخلي الـReflection يفلتر
    الـfindings قبل ما يتحسب الـRisk، مش بعده.

    Edge Case 2 (Tool Failure): لو security_agent فشل (tool_error=True)،
    منكملش نعمل Reflection/Risk عادي — ده كان هيبقى false negative خطير.
    بدل كده نرجّع severity="UNKNOWN_NEEDS_MANUAL_REVIEW" صراحة.
    """
    security_result = state.get("security_result", {})
    if not security_result:
        return {}  # الـSecurity Agent أصلاً ما اتنداش للـPR ده

    if security_result.get("tool_error"):
        return {
            "confirmed_vulnerabilities": [],
            "security_risk_score": None,
            "security_severity": "UNKNOWN_NEEDS_MANUAL_REVIEW",
        }

    confirmed = _reflection_agent.reflect_on_findings(security_result.get("vulnerabilities", []))
    risk = _risk_engine.calculate_overall_risk(confirmed)
    return {
        "confirmed_vulnerabilities": confirmed,
        "security_risk_score": risk["risk_score"],
        "security_severity": risk["severity_label"],
    }


# ---------------- Risk / Merge (fan-in) ----------------
def risk_merge_node(state: AgentState) -> dict:
    # --- Merge prediction: ML (Person 1) + LLM (Person 3), للمقارنة في العرض ---
    features, features_source = build_features(
        pr_diff=state.get("pr_diff", ""),
        pr_description=state.get("pr_description", ""),
        pr_repo=state.get("pr_repo", ""),
        pr_number=state.get("pr_number"),
        pr_metadata=state.get("pr_metadata"),
    )
    try:
        ml_pred = ml_predict_merge(features)
    except Exception as exc:
        ml_pred = {"merge_probability": None, "model": None, "error": f"{type(exc).__name__}: {exc}"}

    llm_context = {
        "diff": state.get("pr_diff", ""),
        "pr_description": state.get("pr_description", ""),
        "commit_message": "",
        "repository_context": state.get("repository_context", ""),
    }
    try:
        llm_pred = predict_merge_llm(llm_context)
    except Exception as exc:
        llm_pred = {"merge_probability": None, "error": f"{type(exc).__name__}: {exc}"}

    # --- Security severity: لو الـSecurity Agent ما اتناداش أصلاً (PR بسيط) ---
    security_severity = state.get("security_severity")
    security_risk_score = state.get("security_risk_score")

    # لو الـCode Review Agent نفسه فشل (LLM tool failure)، منسيبش الـPR
    # يعدي كأن حاجة مفيهاش — نفس فلسفة "fail closed" بتاعة الـSecurity Agent.
    code_review_failed = state.get("code_review_result", {}).get("tool_error", False)

    if code_review_failed:
        severity = "UNKNOWN_NEEDS_MANUAL_REVIEW"
        risk_score = None
        decision = "MANUAL_REVIEW_REQUIRED"
    elif security_severity == "UNKNOWN_NEEDS_MANUAL_REVIEW":
        severity = "UNKNOWN_NEEDS_MANUAL_REVIEW"
        risk_score = None
        decision = "MANUAL_REVIEW_REQUIRED"
    elif security_severity is None:
        # الـSecurity Agent مش مطلوب لـPR ده أصلاً (Supervisor قرر كده)
        severity = "LOW"
        risk_score = 0.0
        decision = "APPROVE"
    else:
        severity = security_severity
        risk_score = security_risk_score
        decision = (
            "BLOCK" if severity == "HIGH"
            else "REQUEST_CHANGES" if severity == "MEDIUM"
            else "APPROVE"
        )

    return {
        "risk_score": risk_score,
        "severity": severity,
        "decision": decision,
        "merge_probability": ml_pred.get("merge_probability"),
        "ml_merge_prediction": ml_pred,
        "llm_merge_prediction": llm_pred,
        "ml_features_source": features_source,
    }


# ---------------- Manual review terminal (Edge Case 2: Tool Failure) ----------------
def manual_review_node(state: AgentState) -> dict:
    errors = list(state.get("errors", []))
    if state.get("code_review_result", {}).get("tool_error"):
        errors.append("code_review_agent (LLM): tool_error — routed to manual review, NOT auto-approved.")
    if state.get("security_result", {}).get("tool_error"):
        errors.append("security_agent: tool_error — routed to manual review, NOT auto-approved.")
    return {"errors": errors}


# ---------------- Output Guardrail (Person 4: OutputGuardrail) ----------------
def output_guardrail_node(state: AgentState) -> dict:
    comments = [
        f"[{i.get('severity', '?').upper()}] {i.get('file', '?')}:{i.get('line', '?')} — {i.get('description', '')}"
        for i in state.get("code_review_result", {}).get("issues", [])
    ]

    # RAG evidence: كانت بتتحسب في security_node (external_references) لكن
    # ما كانتش بتوصل للـfinal_response خالص — المستخدم النهائي كان مش
    # شايفها. (بند 23 في المراجعة: "الـsource ظهر في النتيجة؟")
    rag_evidence = state.get("security_result", {}).get("external_references", [])
    rag_sources = [
        {"source": ref.get("metadata", {}).get("file_name"), "relevance_score": round(ref.get("score", 0), 3)}
        for ref in rag_evidence
    ]

    draft_response = {
        "decision": state.get("decision"),
        "severity": state.get("severity"),
        "risk_score": state.get("risk_score"),
        "ml_merge_probability": state.get("ml_merge_prediction", {}).get("merge_probability"),
        "llm_merge_probability": state.get("llm_merge_prediction", {}).get("merge_probability"),
        "ml_features_source": state.get("ml_features_source"),
        "review_comments": comments,
        "confirmed_vulnerabilities": state.get("confirmed_vulnerabilities", []),
        "rag_sources": rag_sources,
    }

    guard_result = _output_guardrail.inspect_output(draft_response)
    final = guard_result["sanitized_output"] if guard_result["is_blocked"] else draft_response

    return {
        "review_comments": comments,
        "final_response": final,
        "output_guardrail_result": guard_result,
    }

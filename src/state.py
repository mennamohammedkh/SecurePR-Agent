from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict):

    # =========================
    # PR INPUT
    # =========================

    pr_url: str
    pr_title: str
    pr_description: str
    pr_diff: str
    pr_repo: str          # "owner/repo" — Person 5 GitHub tools تحتاجها منفصلة عن pr_url
    pr_number: int        # رقم الـPR — لنفس السبب

    # =========================
    # SUPERVISOR
    # =========================

    supervisor_decision: Optional[str]
    agents_required: List[str]

    # =========================
    # CONTEXT / RAG
    # =========================

    repository_context: str
    retrieved_context: List[str]

    # =========================
    # AGENT RESULTS
    # =========================

    code_review_result: Dict[str, Any]
    security_result: Dict[str, Any]

    # =========================
    # RISK / MERGE
    # =========================

    risk_score: float
    severity: str
    merge_probability: float
    decision: str

    # =========================
    # INTEGRATION EXTENSIONS (Person 2 — added while wiring real team code)
    # =========================
    # هذول اتضافوا فوق الـ schema الأصلي عشان نقدر نستوعب مخرجات
    # Person 1/3/4 الحقيقية من غير ما نفقد أي معلومة مفيدة للـ presentation.

    input_guardrail_result: Dict[str, Any]      # Person 4: InputGuardrail.inspect_input()
    output_guardrail_result: Dict[str, Any]     # Person 4: OutputGuardrail.inspect_output()

    ml_merge_prediction: Dict[str, Any]         # Person 1: predict_merge() -> {merge_probability, model}
    llm_merge_prediction: Dict[str, Any]        # Person 3: predict_merge_llm() -> {merge_probability, confidence, reasoning}

    pr_metadata: Dict[str, Any]                 # Person 5: get_pull_request() الخام (additions/deletions/changed_files/...)
    ml_features_source: str                      # "github_real" أو "diff_approximation" — للشفافية في التقرير

    security_risk_score: Optional[float]        # Person 4: RiskEngine.calculate_overall_risk()["risk_score"]
    security_severity: str                      # HIGH / MEDIUM / LOW / UNKNOWN_NEEDS_MANUAL_REVIEW
    confirmed_vulnerabilities: List[Dict[str, Any]]  # Person 4: ReflectionAgent.reflect_on_findings()

    # =========================
    # REVIEW
    # =========================

    review_comments: List[str]

    # =========================
    # REFLECTION
    # =========================

    reflection_result: Dict[str, Any]

    # =========================
    # FINAL OUTPUT
    # =========================

    final_response: str

    # =========================
    # SYSTEM
    # =========================

    errors: List[str]

"""
Integration build — كل الـnodes دلوقتي بتنادي كود الفريق الحقيقي (Person 1/3/4).

الفرق عن الـSkeleton قبل الـIntegration:
  1. security → reflection بقت edge ثابتة (مش بعد risk_merge) لأن تصميم
     Person 4 الحقيقي بيخلي الـReflection يفلتر الـfindings قبل ما يتحسب
     الـRisk، مش بعده.
  2. أضفنا conditional edge جديدة بعد risk_merge لحالة tool_failure
     (Edge Case 2 بتاع Person 4) → manual_review قبل ما يوصل لـOutput.

PR Input → Input Guardrail
    → [blocked]  → Blocked End → END
    → [continue] → Supervisor
                      → Send(...) بس للـagents المطلوبة فعليًا
                      → code_review ────────────┐
                      → security → reflection ──┼─→ Risk / Merge
                      → context ─────────────────┘
                                                       → [tool_failure] → Manual Review → Output Guardrail → END
                                                       → [normal]       → Output Guardrail → END
"""
from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from src.nodes import (
    input_guardrail_node,
    blocked_end_node,
    supervisor_node,
    code_review_node,
    security_node,
    context_node,
    reflection_node,
    risk_merge_node,
    manual_review_node,
    output_guardrail_node,
)
from src.conditions import route_after_input_guardrail, route_supervisor, route_after_risk


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("blocked_end", blocked_end_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("code_review", code_review_node)
    graph.add_node("security", security_node)
    graph.add_node("context", context_node)
    graph.add_node("reflection", reflection_node)
    graph.add_node("risk_merge", risk_merge_node)
    graph.add_node("manual_review", manual_review_node)
    graph.add_node("output_guardrail", output_guardrail_node)

    graph.add_edge(START, "input_guardrail")

    graph.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {"blocked": "blocked_end", "continue": "supervisor"},
    )
    graph.add_edge("blocked_end", END)

    # Routing حقيقي: الـSupervisor نفسه (عن طريق Send) بيحدد مين يتنادى فعلاً
    graph.add_conditional_edges("supervisor", route_supervisor)

    # security → reflection (فلترة الـfindings قبل الـRisk)، مش مباشرة لـrisk_merge
    graph.add_edge("security", "reflection")
    graph.add_edge("reflection", "risk_merge")

    # code_review و context بيوصلوا risk_merge مباشرة
    graph.add_edge("code_review", "risk_merge")
    graph.add_edge("context", "risk_merge")

    # Conditional: تعامل مع Tool Failure (Edge Case 2) قبل الـOutput
    graph.add_conditional_edges(
        "risk_merge",
        route_after_risk,
        {
            "tool_failure": "manual_review",
            "normal": "output_guardrail",
        },
    )
    graph.add_edge("manual_review", "output_guardrail")
    graph.add_edge("output_guardrail", END)

    return graph.compile()


app = build_graph()

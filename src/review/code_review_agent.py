"""
code_review_agent.py
-----------------------
Person 3 — LLM / Review Owner
Secure Agentic Code Review — Code Review Agent

This is the "brain" that reads code and writes a review. Exposes
review_code(context), the exact integration point Person 2 calls as a
LangGraph node.

Inputs (via `context` dict): PR Description + Commit Message + Code Diff +
Repository Context.
Output (dict): {"issues": [...], "summary": "...", "confidence": 0.86}
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompts import build_context, build_prompt
from llm_client import call_llm, extract_json


DEFAULT_EXPERIMENT = "D"      # diff + full repository context (richest signal)
DEFAULT_PATTERN = "role_based"  # best-performing pattern -- see results/prompt_comparison.csv


def review_code(context: dict, experiment: str = DEFAULT_EXPERIMENT, pattern: str = DEFAULT_PATTERN) -> dict:
    """
    Person 2's integration point. Called as a LangGraph node.

    Args:
        context: {
            "diff": str,                    # required
            "pr_description": str,          # optional
            "commit_message": str,          # optional
            "repository_context": str,      # optional
        }
        experiment: "A" | "B" | "C" | "D" -- which context-construction
            strategy to use (see prompts.py). Defaults to "D" (full context),
            the best-performing experiment per results/prompt_comparison.csv.
        pattern: "zero_shot" | "few_shot" | "role_based" | "reflection".
            Defaults to "role_based", the best-performing pattern per the
            same comparison. Override either argument to reproduce a
            specific experiment during evaluation.

    Returns:
        {"issues": [ {severity, file, line, category, description,
                       suggestion}, ... ],
         "summary": str,
         "confidence": float}
    """
    built_context = build_context(context, experiment)
    prompt = build_prompt(built_context, pattern)

    llm_result = call_llm(prompt)
    parsed = extract_json(llm_result["text"])

    if parsed is None or "issues" not in parsed:
        # graceful fallback so a malformed LLM response never crashes
        # Person 2's graph -- surface a low-confidence empty review instead
        return {
            "issues": [],
            "summary": "Could not parse a structured review from the model response.",
            "confidence": 0.0,
            "_raw_response": llm_result["text"],
            "_inference_time_sec": llm_result["inference_time_sec"],
        }

    parsed.setdefault("summary", "")
    parsed.setdefault("confidence", 0.5)
    parsed["_inference_time_sec"] = llm_result["inference_time_sec"]
    return parsed


def format_review_comment(issue: dict) -> str:
    """
    Formats a single issue dict into the human-readable comment shape
    required by the spec (Issue, Severity, Evidence, Location, Explanation,
    Suggested Fix).
    """
    return (
        f"{issue.get('severity', 'unknown').upper()}\n"
        f"File: {issue.get('file', 'unknown')}\n"
        f"Line: {issue.get('line', '?')}\n"
        f"Issue: {issue.get('category', 'unknown').title()} — {issue.get('description', '')}\n"
        f"Evidence: {issue.get('description', '')}\n"
        f"Recommendation: {issue.get('suggestion', '')}"
    )


if __name__ == "__main__":
    demo_context = {
        "diff": (
            "--- a/database.py\n+++ b/database.py\n"
            "@@ -10,3 +10,3 @@\n"
            "- query = build_safe_query(user_id)\n"
            "+ query = \"SELECT * FROM users WHERE id = \" + user_id\n"
            "  cursor.execute(query)\n"
        ),
        "pr_description": "Simplify user lookup query construction.",
        "commit_message": "refactor: simplify query building",
        "repository_context": "Flask-based internal admin dashboard, PostgreSQL backend.",
    }

    result = review_code(demo_context)
    print("=== review_code() output ===")
    import json
    print(json.dumps(result, indent=2))

    print("\n=== Formatted comments ===")
    for issue in result["issues"]:
        print(format_review_comment(issue))
        print("-" * 40)

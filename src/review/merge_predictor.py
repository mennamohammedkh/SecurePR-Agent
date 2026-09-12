"""
merge_predictor.py
---------------------
Person 3 — LLM / Review Owner
Secure Agentic Code Review — LLM-Based Merge Prediction

Provides an LLM-based counterpart to Person 1's traditional-ML merge
prediction, so the two can be compared side by side in the presentation:

    Traditional ML (Person 1): Random Forest -> 78%
    LLM (Person 3):            Based on PR context -> 81%

Unlike Person 1's model, this makes no use of engineered numeric features --
it reasons directly over the PR's textual/code context, the same way a
human reviewer would.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompts import build_context
from llm_client import call_llm, extract_json

MERGE_PROMPT_TEMPLATE = """You are predicting whether a GitHub Pull Request will be merged.

Based on the context below, assess code quality, risk, and how well the
change matches its stated intent, then predict the outcome.

Respond ONLY with JSON in this exact shape:
{{
  "merge_prediction": "LIKELY_MERGED" or "LIKELY_REJECTED",
  "confidence": <float between 0 and 1>,
  "reasoning": "<one or two sentence justification>"
}}

Context:
{context}
"""


def predict_merge_llm(pr: dict, experiment: str = "D") -> dict:
    """
    Args:
        pr: same shape as code_review_agent.review_code's context dict
            (diff, pr_description, commit_message, repository_context).
        experiment: which context-construction strategy to use (A-D).

    Returns:
        {"merge_prediction": "LIKELY_MERGED"|"LIKELY_REJECTED",
         "confidence": float, "reasoning": str,
         "merge_probability": float}   # confidence re-expressed as a
                                        # probability of the "merged" class,
                                        # for direct comparison with
                                        # Person 1's predict_merge() output
    """
    context = build_context(pr, experiment)
    prompt = MERGE_PROMPT_TEMPLATE.format(context=context)

    llm_result = call_llm(prompt, max_tokens=300)
    parsed = extract_json(llm_result["text"])

    if parsed is None:
        return {
            "merge_prediction": "UNKNOWN",
            "confidence": 0.0,
            "reasoning": "Could not parse LLM response.",
            "merge_probability": 0.5,
            "_inference_time_sec": llm_result["inference_time_sec"],
        }

    confidence = float(parsed.get("confidence", 0.5))
    is_merged_pred = parsed.get("merge_prediction") == "LIKELY_MERGED"
    # convert (prediction, confidence) into a single 0-1 "merge probability",
    # matching the shape of Person 1's predict_merge() output
    merge_probability = confidence if is_merged_pred else 1 - confidence

    parsed["merge_probability"] = round(merge_probability, 4)
    parsed["_inference_time_sec"] = llm_result["inference_time_sec"]
    return parsed


if __name__ == "__main__":
    demo_pr = {
        "diff": "+ def clamp(x, lo, hi):\n+     return max(lo, min(x, hi))",
        "pr_description": "Add a small utility function for clamping values.",
        "commit_message": "feat: add clamp utility",
        "repository_context": "Shared utilities library used across services.",
    }
    result = predict_merge_llm(demo_pr)
    import json
    print(json.dumps(result, indent=2))

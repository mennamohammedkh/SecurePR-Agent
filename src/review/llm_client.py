"""
llm_client.py
---------------
Person 3 — LLM / Review Owner
Secure Agentic Code Review — LLM Client

Model choice: Claude (Anthropic), model "claude-sonnet-4-6".
-------------------------------------------------------------
Why Claude over GPT or a local Llama/Mistral:
  1. Strong, consistently structured JSON output on long technical prompts,
     which this agent depends on heavily (every review must parse as JSON).
  2. Large context window comfortably fits Diff + PR description + commit
     message + repository context together (Experiment D) without truncation.
  3. Available via a simple hosted API -- no GPU/hardware requirement on the
     team's laptops, which matters since Person 1 and Person 2's parts also
     need to run on modest hardware.
  4. Good instruction-following for role-based and self-reflection prompt
     patterns (Section d of the spec) without heavy prompt-tuning.
If your team has GPT-4/GPT-4o API access instead, swap the call_llm()
implementation for the OpenAI SDK -- the rest of the pipeline (prompts.py,
code_review_agent.py, merge_predictor.py, evaluator.py) is provider-agnostic
and only depends on call_llm(prompt) -> str.

MOCK MODE:
  This module also supports MOCK_MODE (no API key required), which
  generates realistic-looking structured review output locally. This lets
  the rest of the team's code (Person 2's LangGraph node, evaluator.py)
  be developed and tested before an API key/billing is set up. Switch to
  real calls by setting the ANTHROPIC_API_KEY environment variable --
  MOCK_MODE auto-disables the moment a key is present, or set
  llm_client.MOCK_MODE = False / True explicitly to override.
"""

import os
import re
import time
import random

MODEL_NAME = "claude-sonnet-4-6"

MOCK_MODE = os.environ.get("ANTHROPIC_API_KEY") is None

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


# ---------------------------------------------------------------------------
# Mock generator -- used only when MOCK_MODE is True. Produces plausible,
# schema-correct JSON so downstream code (parsing, evaluation, LangGraph
# integration) can be built and tested without an API key.
# ---------------------------------------------------------------------------
_MOCK_CATEGORIES = ["security", "performance", "style", "correctness", "maintainability"]
_MOCK_SEVERITIES = ["low", "medium", "high", "critical"]
_MOCK_ISSUE_TEMPLATES = [
    ("security", "critical", "User-controlled input is concatenated directly into a SQL query.",
     "Use parameterized queries or an ORM query builder instead of string concatenation."),
    ("security", "high", "Secret or API key appears to be hardcoded in source.",
     "Move the credential to an environment variable or secrets manager."),
    ("correctness", "medium", "Off-by-one error possible in the loop boundary condition.",
     "Double-check the loop bound against the intended inclusive/exclusive range."),
    ("performance", "medium", "This operation runs inside a loop and re-computes a value that is loop-invariant.",
     "Hoist the invariant computation outside the loop."),
    ("style", "low", "Function name does not follow the project's snake_case convention.",
     "Rename to match the surrounding code style."),
    ("maintainability", "low", "Function has no docstring explaining its purpose or parameters.",
     "Add a short docstring describing inputs, outputs, and side effects."),
    ("correctness", "high", "Return value of a call that can fail is not checked before use.",
     "Add error handling / a None-check before using the result."),
]


def _mock_call(prompt: str) -> str:
    """Deterministic-ish mock response based on a hash of the prompt, so the
    same input tends to produce the same mock output during testing."""
    time.sleep(0.05)  # simulate a tiny bit of latency so inference-time metrics are non-zero
    rnd = random.Random(hash(prompt) % (2**32))
    n_issues = rnd.randint(1, 3)
    issues = []
    chosen = rnd.sample(_MOCK_ISSUE_TEMPLATES, k=n_issues)
    for cat, sev, desc, sug in chosen:
        issues.append({
            "severity": sev,
            "file": rnd.choice(["auth.py", "database.py", "utils.py", "api/routes.py"]),
            "line": rnd.randint(5, 200),
            "category": cat,
            "description": desc,
            "suggestion": sug,
        })

    # If the prompt is asking for a merge-prediction-style answer, return that shape instead
    if '"merge_prediction"' in prompt or "MERGE_PREDICTION" in prompt.upper():
        pred = rnd.choice(["LIKELY_MERGED", "LIKELY_REJECTED"])
        conf = round(rnd.uniform(0.55, 0.95), 2)
        return f'{{"merge_prediction": "{pred}", "confidence": {conf}, "reasoning": "Mocked reasoning for offline testing."}}'

    summary = f"Found {n_issues} issue(s), most significant: {chosen[0][2]}"
    confidence = round(rnd.uniform(0.6, 0.95), 2)
    # NOTE (Person 2 integration fix): the previous implementation built this
    # JSON with str(issues).replace("'", '"'), which corrupts the output any
    # time a description/suggestion contains a real apostrophe (e.g.
    # "project's convention") -- that apostrophe also gets swapped to a
    # double-quote and breaks json.loads() downstream in extract_json().
    # Using json.dumps() is correct regardless of quote characters inside
    # the text. This only affects MOCK_MODE (no ANTHROPIC_API_KEY set); the
    # real API path was never affected. Please carry this fix back into the
    # source of truth in Person 3's repo.
    import json as _json
    return _json.dumps({"issues": issues, "summary": summary, "confidence": confidence})


def call_llm(prompt: str, max_tokens: int = 800) -> dict:
    """
    Sends `prompt` to the configured LLM and returns:
      {"text": <raw response text>, "inference_time_sec": <float>}
    Callers (code_review_agent.py, merge_predictor.py) are responsible for
    parsing the JSON out of `text`.
    """
    start = time.time()

    if MOCK_MODE:
        text = _mock_call(prompt)
    else:
        client = _get_client()
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")

    elapsed = time.time() - start
    return {"text": text, "inference_time_sec": elapsed}


def extract_json(text: str):
    """Best-effort extraction of the first {...} JSON object from an LLM response."""
    import json
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx == -1 or end_idx == -1:
        return None
    try:
        return json.loads(text[start_idx:end_idx + 1])
    except json.JSONDecodeError:
        return None

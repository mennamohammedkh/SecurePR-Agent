"""
prompts.py
------------
Person 3 — LLM / Review Owner
Secure Agentic Code Review — Context Construction & Prompt Engineering

Implements:
  - The 4 context experiments (A: diff only, B: diff+description,
    C: diff+commit message, D: diff+repository context)
  - The 4 prompt patterns (zero-shot, few-shot, role-based, self-reflection)

The actual prompt text for each pattern also lives in prompts/*.txt so
non-engineers on the team (and the report) can read the exact wording
without opening Python source. build_prompt() loads those files and fills
in the {context} / {task} placeholders.
"""

import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(_THIS_DIR, "..", "..", "prompts")

TASK_INSTRUCTION = """You are performing an automated code review on a Pull Request.
Analyze the provided context and identify concrete issues in the code change.

Respond ONLY with a JSON object in exactly this shape (no prose outside the JSON):
{{
  "issues": [
    {{
      "severity": "low|medium|high|critical",
      "file": "<filename>",
      "line": <line number as an integer, best estimate from the diff>,
      "category": "security|performance|style|correctness|maintainability",
      "description": "<what the issue is>",
      "suggestion": "<concrete fix>"
    }}
  ],
  "summary": "<one-sentence overall assessment>",
  "confidence": <float between 0 and 1>
}}

If you find no issues, return an empty "issues" list, not a fabricated one.
"""

# ---------------------------------------------------------------------------
# CONTEXT EXPERIMENTS A-D
# ---------------------------------------------------------------------------

def build_context(pr: dict, experiment: str) -> str:
    """
    pr is a dict with keys: diff, pr_description, commit_message,
    repository_context (any of which may be empty strings).

    experiment: "A" (diff only) | "B" (diff+description) |
                "C" (diff+commit message) | "D" (diff+repository context)
    """
    diff = pr.get("diff", "")

    if experiment == "A":
        return f"Code Diff:\n{diff}"

    elif experiment == "B":
        return f"PR Description:\n{pr.get('pr_description', '')}\n\nCode Diff:\n{diff}"

    elif experiment == "C":
        return f"Commit Message:\n{pr.get('commit_message', '')}\n\nCode Diff:\n{diff}"

    elif experiment == "D":
        return (
            f"Repository Context:\n{pr.get('repository_context', '')}\n\n"
            f"PR Description:\n{pr.get('pr_description', '')}\n\n"
            f"Commit Message:\n{pr.get('commit_message', '')}\n\n"
            f"Code Diff:\n{diff}"
        )
    else:
        raise ValueError(f"Unknown experiment: {experiment} (expected A, B, C, or D)")


# ---------------------------------------------------------------------------
# PROMPT PATTERNS
# ---------------------------------------------------------------------------

_PATTERN_FILES = {
    "zero_shot": "zero_shot.txt",
    "few_shot": "few_shot.txt",
    "role_based": "role_based.txt",
    "reflection": "reflection.txt",
}


def _load_pattern_template(pattern: str) -> str:
    path = os.path.join(PROMPTS_DIR, _PATTERN_FILES[pattern])
    with open(path) as f:
        return f.read()


def build_prompt(context: str, pattern: str) -> str:
    """
    pattern: "zero_shot" | "few_shot" | "role_based" | "reflection"
    """
    template = _load_pattern_template(pattern)
    return template.format(task=TASK_INSTRUCTION, context=context)

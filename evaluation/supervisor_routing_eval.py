"""
Supervisor Routing Accuracy Evaluation (بند 21)
=================================================
Test dataset: PR Type -> Expected Agents -> Actual Agents، وحساب الـrouting
accuracy. الديفولت هنا بيشغّل `decide_heuristic` (لأن مفيش
`ANTHROPIC_API_KEY` في هذه البيئة)، لكن نفس الـharness يشتغل حرفيًا على
`decide_llm`/`decide` (اللي بيختار تلقائي) لما الـkey يتوفر — استبدلي
`DECISION_FN` تحت بس.

تشغيل:
    PYTHONPATH=. python evaluation/supervisor_routing_eval.py
"""
from src.supervisor import decide_heuristic, decide

# غيّريها لـ `decide` لو عايزة تقيّمي مسار LLM الحقيقي (يحتاج ANTHROPIC_API_KEY)
DECISION_FN = decide_heuristic

TEST_CASES = [
    {
        "label": "Docs-only PR",
        "pr": {
            "pr_title": "Fix typo in README",
            "pr_description": "Just a documentation fix.",
            "pr_diff": "- Instal\n+ Install",
        },
        "expected_agents": {"code_review"},
    },
    {
        "label": "SQL query PR",
        "pr": {
            "pr_title": "Add login endpoint",
            "pr_description": "Adds a new /login route using raw SQL query.",
            "pr_diff": 'query = "SELECT * FROM users WHERE username = \'" + username + "\'"\ncursor.execute(query)',
        },
        "expected_agents": {"code_review", "security"},
    },
    {
        "label": "Auth/token PR",
        "pr": {
            "pr_title": "Add JWT auth",
            "pr_description": "Adds token-based authentication.",
            "pr_diff": "def check_token(token):\n    return verify(token)",
        },
        "expected_agents": {"code_review", "security"},
    },
    {
        "label": "Command execution PR",
        "pr": {
            "pr_title": "Add CLI wrapper",
            "pr_description": "Wraps a shell command.",
            "pr_diff": "os.system(cmd)\neval(user_input)",
        },
        "expected_agents": {"code_review", "security"},
    },
    {
        "label": "Config/database import PR",
        "pr": {
            "pr_title": "Refactor DB config loading",
            "pr_description": "Splits database config into its own module.",
            "pr_diff": "import database\nfrom config import settings",
        },
        "expected_agents": {"code_review", "context"},
    },
    {
        "label": "Pure logic change (no auth/db keywords)",
        "pr": {
            "pr_title": "Speed up sorting function",
            "pr_description": "Uses a faster sort algorithm.",
            "pr_diff": "def sort_items(items):\n    return sorted(items, key=lambda x: x.value)",
        },
        "expected_agents": {"code_review"},
    },
]


def run_evaluation():
    correct = 0
    rows = []
    for case in TEST_CASES:
        result = DECISION_FN(case["pr"])
        actual = set(result.get("agents_required", []))
        expected = case["expected_agents"]
        match = actual == expected
        correct += int(match)
        rows.append((case["label"], expected, actual, match))

    print(f"{'PR Type':35} {'Expected':30} {'Actual':30} {'Match'}")
    print("-" * 110)
    for label, expected, actual, match in rows:
        print(f"{label:35} {str(sorted(expected)):30} {str(sorted(actual)):30} {'✓' if match else '✗'}")

    accuracy = correct / len(TEST_CASES)
    print("-" * 110)
    print(f"Routing accuracy: {correct}/{len(TEST_CASES)} = {accuracy:.1%}")
    return accuracy


if __name__ == "__main__":
    run_evaluation()

"""
Unit Tests for Edge Case 3: Distinguishing Security Discussions from Actual Attacks
"""

import unittest
from src.guardrails.input_guardrail import InputGuardrail

class TestFalsePositiveDifferentiation(unittest.TestCase):
    """Test suite ensuring security discussions (e.g., bug fixes descriptions) are NOT blocked."""

    def setUp(self) -> None:
        self.guardrail = InputGuardrail()

    def test_edge_case_3_security_discussion_allowed(self) -> None:
        """Edge Case 3: A PR discussing a fix for an injection must NOT be blocked as an attack."""
        payload = {
            "description": "This PR fixes a prompt injection vulnerability in the input parser.",
            "code_diff": "sanitized_input = escape_html(user_input)"
        }
        result = self.guardrail.inspect_input(payload)
        self.assertFalse(result["is_blocked"])

if __name__ == "__main__":
    unittest.main()
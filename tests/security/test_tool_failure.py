"""
Unit Tests for Edge Case 2: Tool Failure & Safe Fallback Mechanics
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure the repository root is importable when this test is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.security.security_agent import SecurityAgent
from src.main_security_scan import security_scan  # pyright: ignore[reportMissingImports]


class TestToolFailureFallback(unittest.TestCase):
    """Test suite for graceful degradation and safe fallback when security tools fail."""

    def test_empty_diff_returns_clean_not_a_tool_failure(self) -> None:
        """An empty code_diff is a legitimate CLEAN result (nothing to scan) --
        distinct from an actual scanner crash. Confirms the two cases aren't conflated."""
        agent = SecurityAgent()
        result = agent.scan_code("")

        self.assertEqual(result["security_status"], "CLEAN")
        self.assertEqual(result["total_findings"], 0)
        self.assertFalse(result["tool_error"])
        self.assertIn("vulnerabilities", result)

    def test_edge_case_2_real_scanner_crash_fails_closed(self) -> None:
        """Edge Case 2 (real failure): the classifier itself raises an unexpected
        exception (simulating e.g. a Semgrep/Bandit process crash). The agent must
        NOT silently report CLEAN (a dangerous false negative) or fabricate
        findings (hallucination) -- it must fail closed with an explicit
        TOOL_FAILURE status."""
        agent = SecurityAgent()

        with patch.object(
            agent.classifier,
            "classify_code_snippet",
            side_effect=RuntimeError("Simulated static analyzer crash"),
        ):
            result = agent.scan_code("some_code = 'diff content here'")

        self.assertEqual(result["security_status"], "TOOL_FAILURE")
        self.assertTrue(result["tool_error"])
        self.assertEqual(result["vulnerabilities"], [])
        self.assertEqual(result["total_findings"], 0)
        self.assertIn("Simulated static analyzer crash", result["error_message"])

    def test_edge_case_2_end_to_end_pipeline_routes_to_manual_review(self) -> None:
        """The full security_scan(pr) pipeline must surface a scanner crash as
        TOOL_FAILURE (routing to manual review), not as a false SUCCESS/clean
        result with a fabricated risk score."""
        with patch(
            "src.security.threat_classifier.ThreatClassifier.classify_code_snippet",
            side_effect=RuntimeError("Simulated static analyzer crash"),
        ):
            result = security_scan({
                "description": "Refactor payment handling",
                "code_diff": "def charge(amount): return process(amount)",
            })

        self.assertEqual(result["status"], "TOOL_FAILURE")
        self.assertEqual(result["threats"], [])
        self.assertIsNone(result["risk_score"])
        self.assertEqual(result["severity"], "UNKNOWN_NEEDS_MANUAL_REVIEW")


if __name__ == "__main__":
    unittest.main()
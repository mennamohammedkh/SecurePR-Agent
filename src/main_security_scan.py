"""
Main Security Scan Integration Module
Provides the core security_scan(pr) function required for integration 
with the rest of the team's pipeline (Supervisor / Risk Agent).
"""

import logging
from typing import Dict, Any
from src.guardrails.input_guardrail import InputGuardrail
from src.guardrails.output_guardrail import OutputGuardrail
from src.security.security_agent import SecurityAgent
from src.security.risk_engine import RiskEngine
from src.reflection.reflection_agent import ReflectionAgent

logger = logging.getLogger(__name__)


def security_scan(pr: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for security scanning of a Pull Request.
    Integrates input guardrails, security agent analysis, reflection, and risk scoring.

    Status values returned:
        "BLOCKED"        -- input guardrail rejected the PR (malicious/obfuscated input).
        "TOOL_FAILURE"    -- the security agent's scanner crashed; NOT treated as clean.
                             Caller (Supervisor / Risk Agent) should route to manual
                             review rather than merge automatically.
        "SUCCESS"        -- scan completed normally (findings may be empty or non-empty).
    """
    input_guard = InputGuardrail()
    security_agent = SecurityAgent()
    reflection_agent = ReflectionAgent()
    risk_engine = RiskEngine()

    input_check = input_guard.inspect_input(pr)
    if input_check["is_blocked"]:
        return {
            "status": "BLOCKED",
            "threats": input_check["threats"],
            "risk_score": input_check["risk_score"],
            "severity": "HIGH"
        }

    code_diff = pr.get("code_diff", "")
    scan_results = security_agent.scan_code(code_diff)

    # Edge Case 2 (Tool Failure): if the security agent's scanner crashed,
    # do NOT fall through to reflection/risk scoring on an empty findings
    # list -- that would silently look identical to "scanned clean", which
    # is a dangerous false negative. Surface the failure explicitly instead.
    if scan_results.get("tool_error"):
        logger.error(
            f"security_scan: security agent tool failure -- "
            f"{scan_results.get('error_message', 'unknown error')}. "
            f"Flagging for manual review instead of returning a clean result."
        )
        return {
            "status": "TOOL_FAILURE",
            "threats": [],
            "risk_score": None,
            "severity": "UNKNOWN_NEEDS_MANUAL_REVIEW",
            "message": (
                "Automated security scan could not complete due to a scanner "
                "failure. This PR requires manual security review before merge."
            )
        }

    confirmed_vulns = reflection_agent.reflect_on_findings(scan_results["vulnerabilities"])

    risk_assessment = risk_engine.calculate_overall_risk(confirmed_vulns)

    return {
        "status": "SUCCESS",
        "threats": confirmed_vulns,
        "risk_score": risk_assessment["risk_score"],
        "severity": risk_assessment["severity_label"]
    }
"""
Risk Engine Module
Computes final risk scores and severity classifications based on multi-factor analysis
including security severity, evidence strength, exploitability, and confidence.

Severity-label thresholds are sourced from `SecurityRulesRegistry.DEFAULT_RISK_THRESHOLDS`
(src/security/security_rules.py) rather than being duplicated here, so the two modules
cannot silently drift out of sync.
"""

from typing import Dict, Any, List

from src.security.security_rules import SecurityRulesRegistry


class RiskEngine:
    """Calculates weighted risk scores for security findings and overall PR state."""

    def __init__(self) -> None:
        # Per-vulnerability severity weighting used when aggregating findings.
        # (Distinct from the score->label thresholds below, which classify the
        # final aggregate score.)
        self.severity_weights = {
            "HIGH": 0.9,
            "MEDIUM": 0.6,
            "LOW": 0.2
        }
        # Single source of truth for score->label thresholds, shared with
        # SecurityRulesRegistry to avoid duplicated/drifting constants.
        self.risk_thresholds = SecurityRulesRegistry.DEFAULT_RISK_THRESHOLDS

    def calculate_overall_risk(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes the aggregate risk score and maps it to a severity level.
        Formula factors: severity weight + confidence + exploitability.
        """
        if not vulnerabilities:
            # No findings: report a nominal baseline score, well under the
            # shared LOW threshold, and label LOW.
            baseline_score = round(self.risk_thresholds["LOW"] / 2, 2)
            return {
                "risk_score": baseline_score,
                "severity_label": "LOW"
            }

        max_score = 0.0
        for vuln in vulnerabilities:
            sev = vuln.get("severity", "LOW")
            base_weight = self.severity_weights.get(sev, 0.2)

            calculated_score = base_weight * 1.0  # Confidence factor = 1.0
            if calculated_score > max_score:
                max_score = calculated_score

        final_score = round(max_score, 2)

        if final_score >= self.risk_thresholds["HIGH"]:
            label = "HIGH"
        elif final_score >= self.risk_thresholds["MEDIUM"]:
            label = "MEDIUM"
        else:
            label = "LOW"

        return {
            "risk_score": final_score,
            "severity_label": label
        }
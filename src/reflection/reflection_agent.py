"""
Reflection Agent Module

Applies a structured filter/validation check to raw security findings before
they are treated as confirmed. A finding is CONFIRMED only if it has an
actionable severity (HIGH or MEDIUM) AND carries a supporting reference
(e.g. an OWASP/CWE citation); otherwise it is marked REJECTED_AS_AMBIGUOUS.

This is a deterministic, rule-based filter -- it does NOT perform deep
context cross-correlation against the surrounding code, autonomous
self-re-analysis, or any kind of iterative reasoning loop. It should be
understood as a validation/confidence gate on top of the raw classifier
output, not an independent second-opinion reviewer.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ReflectionAgent:
    """Applies a severity + reference validation filter to raw security findings."""

    def reflect_on_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters findings to those with actionable severity (HIGH/MEDIUM) and a
        supporting reference. Findings that fail this check are rejected as
        ambiguous rather than silently dropped -- they are logged (including
        the reason) for audit visibility, so reviewers can see what the
        pipeline discarded and why, even though only confirmed findings are
        returned to the caller.
        """
        refined_findings: List[Dict[str, Any]] = []
        rejected_findings: List[Dict[str, Any]] = []

        for finding in findings:
            has_actionable_severity = finding.get("severity") in ["HIGH", "MEDIUM"]
            has_reference = bool(finding.get("reference"))

            if has_actionable_severity and has_reference:
                finding["reflection_status"] = "CONFIRMED"
                refined_findings.append(finding)
            else:
                finding["reflection_status"] = "REJECTED_AS_AMBIGUOUS"
                reasons = []
                if not has_actionable_severity:
                    reasons.append(f"severity '{finding.get('severity')}' not actionable")
                if not has_reference:
                    reasons.append("missing supporting reference")
                finding["rejection_reason"] = "; ".join(reasons)
                rejected_findings.append(finding)

        if rejected_findings:
            logger.info(
                f"ReflectionAgent rejected {len(rejected_findings)} finding(s) as ambiguous: "
                + "; ".join(
                    f"{f.get('threat_type', 'UNKNOWN')} ({f.get('rejection_reason')})"
                    for f in rejected_findings
                )
            )

        return refined_findings
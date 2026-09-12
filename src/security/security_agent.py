"""
Security Agent Module
Performs static-signature vulnerability analysis on source code diffs,
integrating threat classification and OWASP/CWE guidance lookups for
detected findings.

Note on "guidance retrieval": the OWASP/CWE recommendations returned here
come from a small local lookup dictionary (see `_get_security_rag_guidance`
below), not from a dynamic retrieval-augmented-generation (RAG) system or
any external knowledge base. The method name is kept for backward
compatibility with existing callers, but it performs a static dict lookup.
"""

import logging
from typing import Dict, Any, List
from src.security.threat_classifier import ThreatClassifier

logger = logging.getLogger(__name__)


class SecurityAgent:
    """Core Security Agent responsible for automated code vulnerability detection and remediation guidance."""

    def __init__(self) -> None:
        self.classifier = ThreatClassifier()

    def scan_code(self, code_diff: str) -> Dict[str, Any]:
        """
        Scans the provided code diff for security vulnerabilities using
        `ThreatClassifier`'s static regex signatures, attaches OWASP/CWE
        guidance from the local lookup table, and compiles findings.

        Safe-fallback behavior (Edge Case 2): if the classifier or guidance
        lookup raises an unexpected exception (simulating a scanner/tool
        crash), this method does NOT fabricate findings or silently report
        "CLEAN" -- silently reporting clean on a tool crash would be a
        dangerous false negative (vulnerable code could pass through
        unreviewed). Instead it fails closed: it returns an explicit
        `security_status="TOOL_FAILURE"` with `tool_error=True` so the
        caller (see `security_scan` in main_security_scan.py) can route the
        PR to manual review / elevate risk rather than treating it as a
        clean pass.
        """
        if not code_diff or not code_diff.strip():
            logger.info("scan_code called with empty diff -- returning CLEAN with 0 findings.")
            return {
                "vulnerabilities": [],
                "security_status": "CLEAN",
                "total_findings": 0,
                "tool_error": False
            }

        try:
            raw_threats = self.classifier.classify_code_snippet(code_diff)

            enhanced_findings: List[Dict[str, Any]] = []
            for threat in raw_threats:
                evidence_rec = self._get_security_rag_guidance(threat["threat_type"])

                finding = {
                    "threat_type": threat["threat_type"],
                    "severity": threat["severity"],
                    "matched_pattern": threat["matched_pattern"],
                    "matched_text": threat.get("matched_text"),
                    "span": threat.get("span"),
                    "recommendation": evidence_rec["recommendation"],
                    "reference": evidence_rec["reference"]
                }
                enhanced_findings.append(finding)

        except Exception as exc:
            # Tool failure fallback: log the real error for on-call/audit
            # visibility, and return a safe, explicit "we don't know" result
            # instead of guessing or hallucinating findings.
            logger.error(
                f"SecurityAgent.scan_code: scanner failure during analysis "
                f"({type(exc).__name__}: {exc}). Failing closed with TOOL_FAILURE.",
                exc_info=True
            )
            return {
                "vulnerabilities": [],
                "security_status": "TOOL_FAILURE",
                "total_findings": 0,
                "tool_error": True,
                "error_message": f"{type(exc).__name__}: {exc}"
            }

        status = "HIGH_RISK" if any(f["severity"] == "HIGH" for f in enhanced_findings) else ("MEDIUM_RISK" if enhanced_findings else "CLEAN")

        logger.info(
            f"scan_code completed: status={status}, total_findings={len(enhanced_findings)}"
        )

        return {
            "vulnerabilities": enhanced_findings,
            "security_status": status,
            "total_findings": len(enhanced_findings),
            "tool_error": False
        }

    def _get_security_rag_guidance(self, threat_type: str) -> Dict[str, str]:
        """Looks up OWASP/CWE guidance from a static local dictionary.

        This is a plain dict lookup, not a retrieval-augmented-generation
        (RAG) call against a live knowledge base or vector store. The
        "_rag_" naming is retained only for interface stability with
        existing callers.
        """
        guidelines = {
            "SQL_INJECTION": {
                "recommendation": "Use parameterized queries or ORM to prevent malicious SQL input execution.",
                "reference": "OWASP A03:2021 - Injection / CWE-89"
            },
            "HARDCODED_SECRET": {
                "recommendation": "Move secrets/keys to environment variables or a secure vault service.",
                "reference": "OWASP A07:2021 - Identification and Authentication Failures / CWE-798"
            },
            "COMMAND_INJECTION": {
                "recommendation": "Avoid shell=True in subprocess and avoid evaluating raw inputs via os.system.",
                "reference": "OWASP A03:2021 - Injection / CWE-78"
            },
            "XSS": {
                "recommendation": "Sanitize and encode all dynamic user input rendered in UI elements.",
                "reference": "OWASP A03:2021 - Injection / CWE-79"
            }
        }
        return guidelines.get(threat_type, {
            "recommendation": "Review code against secure coding guidelines and follow principle of least privilege.",
            "reference": "OWASP Secure Coding Practices"
        })
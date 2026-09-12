"""
Security Rules Module
Contains centralized security rules, OWASP/CWE category mappings,
and standard thresholds for code vulnerability assessments.
"""

from typing import Dict, Any

class SecurityRulesRegistry:
    """Registry for centralized security standards and rule definitions."""

    # معايير التصنيف والسياسات العامة للنظام
    DEFAULT_RISK_THRESHOLDS = {
        "HIGH": 0.8,
        "MEDIUM": 0.4,
        "LOW": 0.1
    }

    # خريطة مرجعية لقواعد OWASP و CWE للمشروع
    OWASP_MAPPINGS: Dict[str, Dict[str, str]] = {
        "SQL_INJECTION": {
            "owasp": "A03:2021 - Injection",
            "cwe": "CWE-89",
            "description": "Improper neutralization of special elements used in an SQL command."
        },
        "HARDCODED_SECRET": {
            "owasp": "A07:2021 - Identification and Authentication Failures",
            "cwe": "CWE-798",
            "description": "Use of hard-coded credentials or API keys."
        },
        "COMMAND_INJECTION": {
            "owasp": "A03:2021 - Injection",
            "cwe": "CWE-78",
            "description": "Improper neutralization of special elements used in an OS command."
        },
        "XSS": {
            "owasp": "A03:2021 - Injection",
            "cwe": "CWE-79",
            "description": "Improper neutralization of input during web page generation."
        }
    }

    @classmethod
    def get_rule_metadata(cls, threat_type: str) -> Dict[str, str]:
        """Retrieves rule metadata and standards reference for a specific threat."""
        return cls.OWASP_MAPPINGS.get(threat_type, {
            "owasp": "A04:2021 - Insecure Design",
            "cwe": "CWE-693",
            "description": "General security guideline violation."
        })
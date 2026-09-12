"""
Threat Classifier Module
Responsible for classifying threat types, normalizing threat categories,
and structuring identified vulnerabilities from the code review stream.

Detection method: static regex signature matching against known vulnerable
code patterns. This is NOT semantic/AST-based analysis -- it will miss
variants that don't match the listed patterns (e.g. paraphrased or
structurally different code) and can be evaded by sufficiently different
formatting. Treat this as a first-pass, high-precision signature scan, not
a comprehensive vulnerability detector.
"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ThreatClassifier:
    """Classifies and standardizes detected security vulnerabilities via regex signatures."""

    def __init__(self) -> None:
        self.vulnerability_signatures = {
            "SQL_INJECTION": [
                r"execute\s*\(\s*['\"].*?%s.*?['\"]",
                r"cursor\.execute\s*\(\s*f['\"].*?\{.*?\}",
                r"SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*=\s*['\"].*?\+"
            ],
            "HARDCODED_SECRET": [
                r"api[_-]?key\s*=\s*['\"'][a-zA-Z0-9_\-]{16,}['\"]",
                r"password\s*=\s*['\"].*?['\"]",
                r"secret\s*=\s*['\"].*?['\"]"
            ],
            "COMMAND_INJECTION": [
                r"os\.system\s*\(",
                r"subprocess\.run\s*\(.*?shell\s*=\s*True",
                r"eval\s*\("
            ],
            "XSS": [
                r"innerHTML\s*=",
                r"document\.write\s*\("
            ]
        }

    def classify_code_snippet(self, code_snippet: str) -> List[Dict[str, Any]]:
        """Scans code text against known vulnerability signatures and returns structured threats.

        Every pattern match is reported individually -- including multiple
        matches of the same threat_type and/or the same pattern -- so that a
        diff containing several distinct instances of the same vulnerability
        class (e.g. three separate SQL injection sites) surfaces as three
        findings rather than being collapsed into one.
        """
        identified_threats: List[Dict[str, Any]] = []

        for threat_type, patterns in self.vulnerability_signatures.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, code_snippet, re.IGNORECASE))
                for match in matches:
                    identified_threats.append({
                        "threat_type": threat_type,
                        "matched_pattern": pattern,
                        "matched_text": match.group(0),
                        "span": match.span(),
                        "severity": "HIGH" if threat_type in ["SQL_INJECTION", "COMMAND_INJECTION"] else "MEDIUM"
                    })

        if identified_threats:
            logger.info(
                f"ThreatClassifier found {len(identified_threats)} signature match(es): "
                f"{[t['threat_type'] for t in identified_threats]}"
            )

        return identified_threats
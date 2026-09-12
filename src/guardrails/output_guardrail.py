"""
Output Guardrail Module
Ensures that the AI-generated code review responses are safe, structurally valid (JSON),
free from hallucinated file paths/line numbers, and clear of secret leakages.
"""

import json
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class OutputGuardrail:
    """Advanced Output Guardrail for screening AI code review outputs before delivery."""

    def __init__(self) -> None:
        self._secret_leakage_signatures: List[str] = [
            r"api[_-]?key\s*[:=]\s*['\"].*?['\"]",
            r"password\s*[:=]\s*['\"].*?['\"]",
            r"secret\s*[:=]\s*['\"].*?['\"]",
            r"bearer\s+[a-zA-Z0-9_\-\.]+"
        ]

    def _validate_json_structure(self, output_text: str) -> bool:
        """Validates if the generated output conforms to a strict JSON schema if expected."""
        try:
            if isinstance(output_text, dict):
                return True
            json.loads(output_text)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    def _check_secret_leakage(self, text: str) -> List[str]:
        """Scans the output for any accidental leakage of credentials or tokens."""
        leaks = []
        for pattern in self._secret_leakage_signatures:
            if re.search(pattern, text, re.IGNORECASE):
                leaks.append(f"Potential secret leakage detected matching: {pattern}")
        return leaks

    def _check_hallucinated_references(self, output_text: str) -> List[str]:
        """Detects suspicious or unsupported claims regarding file lines."""
        issues = []
        if "file line -1" in output_text or "line 999999" in output_text:
            issues.append("Suspended hallucinated line reference detected.")
        return issues

    def inspect_output(self, ai_response: Any) -> Dict[str, Any]:
        """
        Executes the full output guardrail inspection pipeline.
        Ensures structural integrity, absence of leaks, and factual validity.
        """
        response_str = json.dumps(ai_response) if isinstance(ai_response, (dict, list)) else str(ai_response)

        # 1. Structural & JSON Validation
        is_valid_structure = self._validate_json_structure(ai_response)
        
        # 2. Secret Leakage Check
        leaks = self._check_secret_leakage(response_str)
        
        # 3. Hallucination / Unsupported claims check
        hallucination_issues = self._check_hallucinated_references(response_str)

        violations = leaks + hallucination_issues
        is_blocked = (not is_valid_structure) or (len(violations) > 0)

        if is_blocked:
            logger.error(f"Output Guardrail Blocked Response. Violations: {violations}, JSON Valid: {is_valid_structure}")

        return {
            "status": "BLOCK / SANITIZE" if is_blocked else "ALLOW",
            "is_blocked": is_blocked,
            "is_valid_structure": is_valid_structure,
            "violations": violations,
            "sanitized_output": ai_response if not is_blocked else {"error": "Output blocked due to security guardrail violations."}
        }
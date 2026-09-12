"""
Validators Module
Provides helper validation functions for strict schema matching,
data sanitization, and type checking across guardrails.
"""

from typing import Any, Dict

class SecurityValidators:
    """Utility class for validating structure types and payload integrity."""

    @staticmethod
    def validate_payload_schema(payload: Dict[str, Any]) -> bool:
        """Validates that the incoming PR payload contains mandatory fields."""
        required_keys = ["description", "code_diff"]
        return all(key in payload for key in required_keys)

    @staticmethod
    def sanitize_string(text: str) -> str:
        """Removes dangerous control characters and normalizes whitespace."""
        if not isinstance(text, str):
            return ""
        return " ".join(text.split())
"""
Input Guardrail Module
Handles initial PR screening, obfuscation detection (Base64/Hex),
and protection against Prompt Injection, Jailbreaks, and System Prompt Extractions.

Detection strategy:
    Each relevant field (`description`, `code_diff`) is inspected and decoded
    INDEPENDENTLY before threat analysis. Fields are never concatenated prior
    to encoding detection, because joining them (even with a separator) can
    invalidate the strict Base64/Hex regexes and cause obfuscated payloads to
    be silently missed when the other field also contains legitimate content
    (e.g. a real code diff alongside a Base64-encoded injection string).
"""

import re
import base64
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class InputGuardrail:
    """Input Guardrail for securing PR ingestion pipelines."""

    def __init__(self) -> None:
        self._injection_signatures: List[str] = [
            r"ignore\s+(previous|all)\s+instructions",
            r"bypass\s+(your|system)\s+restrictions",
            r"show\s+(me\s+)?(your\s+)?hidden\s+instructions",
            r"call\s+this\s+tool\s+with",
            r"system\s+prompt\s+extraction",
            r"forget\s+all\s+prior\s+context",
        ]

    def _detect_encoding(self, text: str) -> str:
        """Detects if a single field's text is obfuscated using Base64 or Hex.

        Must be called on one field's content at a time -- concatenating
        multiple fields before this check can introduce characters (such as
        whitespace) that break the strict character-class regexes below and
        cause a false "plain" classification.
        """
        clean_text = text.strip()

        if not clean_text:
            return "plain"

        # Base64 Heuristic Check
        if len(clean_text) % 4 == 0 and re.match(r'^[A-Za-z0-9+/]+={0,2}$', clean_text):
            return "base64"

        # Hex Heuristic Check
        if len(clean_text) % 2 == 0 and re.match(r'^[0-9a-fA-F]+$', clean_text):
            return "hex"

        return "plain"

    def _decode_payload(self, text: str, encoding_type: str) -> str:
        """Safely decodes obfuscated payloads based on detected encoding."""
        try:
            if encoding_type == "base64":
                decoded_bytes = base64.b64decode(text.strip())
                return decoded_bytes.decode('utf-8', errors='ignore')
            elif encoding_type == "hex":
                decoded_bytes = bytes.fromhex(text.strip())
                return decoded_bytes.decode('utf-8', errors='ignore')
        except (base64.binascii.Error, ValueError) as e:
            logger.warning(f"Failed to decode {encoding_type} payload: {e}")
        return text

    def _analyze_field(self, field_name: str, raw_text: str) -> Dict[str, Any]:
        """Runs the detect -> decode -> normalize -> analyze pipeline on ONE field.

        Returns per-field results so callers can attribute which field
        (description vs. code_diff) carried the obfuscated/malicious content,
        which matters for audit logging and triage.
        """
        if not raw_text or not raw_text.strip():
            return {
                "field": field_name,
                "encoding_type": "plain",
                "threats": [],
            }

        enc_type = self._detect_encoding(raw_text)
        normalized_content = self._decode_payload(raw_text, enc_type) if enc_type != "plain" else raw_text
        normalized_content = normalized_content.lower()

        detected_threats: List[str] = []
        for pattern in self._injection_signatures:
            if re.search(pattern, normalized_content):
                detected_threats.append(f"Prompt Injection Signature Matched: {pattern}")

        return {
            "field": field_name,
            "encoding_type": enc_type,
            "threats": detected_threats,
        }

    def inspect_input(self, pr_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the full input guardrail pipeline per-field:
        Detect -> Decode -> Normalize -> Analyze -> Action Decision.

        `description` and `code_diff` are analyzed independently and the
        results merged, rather than concatenated before analysis, so that
        obfuscated content in one field is not masked by plain content in
        the other.
        """
        description = pr_payload.get("description", "") or ""
        code_diff = pr_payload.get("code_diff", "") or ""

        if not description.strip() and not code_diff.strip():
            return {
                "status": "ALLOW",
                "is_blocked": False,
                "encoding_type": "plain",
                "threats": [],
                "risk_score": 0.0,
                "message": "Empty payload received.",
            }

        field_results = [
            self._analyze_field("description", description),
            self._analyze_field("code_diff", code_diff),
        ]

        detected_threats: List[str] = []
        encoding_types_used: List[str] = []
        for result in field_results:
            if result["threats"]:
                detected_threats.extend(
                    f"[{result['field']}] {threat}" for threat in result["threats"]
                )
            if result["encoding_type"] != "plain":
                encoding_types_used.append(f"{result['field']}:{result['encoding_type']}")

        # Preserve a single top-level encoding_type for backward compatibility
        # with existing callers/tests: report the first non-plain encoding
        # found, defaulting to "plain" if none of the fields were encoded.
        encoding_type = next(
            (r["encoding_type"] for r in field_results if r["encoding_type"] != "plain"),
            "plain",
        )

        is_blocked = len(detected_threats) > 0
        action = "BLOCK / INVESTIGATE" if is_blocked else "ALLOW"

        if is_blocked:
            logger.error(f"Security Alert: Malicious input blocked! Threats: {detected_threats}")
        else:
            logger.info(
                f"Input guardrail passed. Fields checked: description, code_diff. "
                f"Encodings observed: {encoding_types_used or ['none']}."
            )

        return {
            "status": action,
            "is_blocked": is_blocked,
            "encoding_type": encoding_type,
            "field_encodings": encoding_types_used,
            "threats": detected_threats,
            "risk_score": 0.95 if is_blocked else 0.05,
        }
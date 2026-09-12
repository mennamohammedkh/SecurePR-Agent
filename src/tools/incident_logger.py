"""
incident_logger.py
====================
Person 5 - RAG / Tools / UI Owner
Incident Logger.

كل Security incident (زي محاولة prompt injection) لازم يتسجل بشكل منظم عشان
يبقى فيه سجل واضح للأحداث الأمنية، وممكن يتراجع فيه لاحقًا أو يتعرض في الـDashboard.

صيغة الـincident (زي ما هي في المستند):
{
  "incident_id": "INC-102",
  "timestamp": "...",
  "attack_type": "prompt_injection",
  "severity": "high",
  "risk_score": 0.91,
  "decision": "blocked"
}
"""

import json
import os
import uuid
from datetime import datetime, timezone

INCIDENT_LOG_PATH = os.environ.get("INCIDENT_LOG_PATH", "incidents.jsonl")

_incident_counter = 0


def _generate_incident_id() -> str:
    """بتولّد incident_id بصيغة INC-<رقم تسلسلي>."""
    global _incident_counter
    _incident_counter += 1
    return f"INC-{100 + _incident_counter}"


def log_incident(attack_type: str, severity: str, risk_score: float, decision: str, incident_id: str = None) -> dict:
    """
    بتسجل incident أمني جديد في الملف (JSON Lines) وترجع الـincident اللي اتسجل.

    Args:
        attack_type: نوع الهجوم، مثلاً "prompt_injection"
        severity: مستوى الخطورة، مثلاً "low" / "medium" / "high" / "critical"
        risk_score: رقم من 0 إلى 1 بيعبر عن مستوى الخطورة المحسوب
        decision: القرار اللي اتاخد، مثلاً "blocked" / "allowed" / "flagged"
        incident_id: اختياري، لو مش موجود بيتولّد تلقائيًا

    Returns:
        dict فيه الـincident كامل زي ما اتسجل
    """
    incident = {
        "incident_id": incident_id or _generate_incident_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attack_type": attack_type,
        "severity": severity,
        "risk_score": risk_score,
        "decision": decision,
    }

    with open(INCIDENT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(incident, ensure_ascii=False) + "\n")

    return incident


def get_all_incidents() -> list:
    """بترجع كل الـincidents المسجلة من الملف (JSON Lines) كـلستة."""
    if not os.path.exists(INCIDENT_LOG_PATH):
        return []

    incidents = []
    with open(INCIDENT_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    incidents.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return incidents

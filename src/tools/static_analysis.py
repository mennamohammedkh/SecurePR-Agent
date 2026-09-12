"""
static_analysis.py
===================
Person 5 - RAG / Tools / UI Owner
Static Analysis Tool.

run_static_analysis() بتشغّل Semgrep أو Bandit على الكود، والـSecurity Agent
(Person 4) يناديها وقت الحاجة عشان ياخد نتائج فحص ثابت (Static Analysis)
بدل ما يعتمد على الـLLM بس.

بتدعم:
    - semgrep : عام (Python, JS, ...) - محتاج semgrep متثبت (`pip install semgrep`)
    - bandit  : مخصص للـPython فقط - محتاج bandit متثبت (`pip install bandit`)
"""

import json
import subprocess
import tempfile
import os


def _run_command(command: list) -> tuple:
    """بتشغّل command في subprocess وترجع (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", f"Command not found: {command[0]}", -1
    except subprocess.TimeoutExpired:
        return "", "Static analysis timed out", -1


def _run_semgrep(target_path: str) -> list:
    """بتشغّل Semgrep على مسار معين وترجع لستة بالـfindings بصيغة موحدة."""
    stdout, stderr, code = _run_command(
        ["semgrep", "--config=auto", "--json", "--quiet", target_path]
    )
    if not stdout:
        return [{"error": stderr or "No output from semgrep"}]

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return [{"error": "Failed to parse semgrep output", "raw": stdout}]

    findings = []
    for result in data.get("results", []):
        findings.append({
            "tool": "semgrep",
            "rule_id": result.get("check_id"),
            "severity": result.get("extra", {}).get("severity", "INFO"),
            "message": result.get("extra", {}).get("message"),
            "path": result.get("path"),
            "start_line": result.get("start", {}).get("line"),
            "end_line": result.get("end", {}).get("line"),
        })
    return findings


def _run_bandit(target_path: str) -> list:
    """بتشغّل Bandit على مسار معين وترجع لستة بالـfindings بصيغة موحدة."""
    stdout, stderr, code = _run_command(
        ["bandit", "-r", target_path, "-f", "json"]
    )
    if not stdout:
        return [{"error": stderr or "No output from bandit"}]

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return [{"error": "Failed to parse bandit output", "raw": stdout}]

    findings = []
    for result in data.get("results", []):
        findings.append({
            "tool": "bandit",
            "rule_id": result.get("test_id"),
            "severity": result.get("issue_severity"),
            "message": result.get("issue_text"),
            "path": result.get("filename"),
            "start_line": result.get("line_number"),
            "end_line": result.get("line_number"),
        })
    return findings


def run_static_analysis(code: str = None, target_path: str = None, tool: str = "semgrep") -> list:
    """
    بتشغّل static analysis باستخدام Semgrep أو Bandit.

    ينفع تستدعيها بطريقتين:
        1) بتديها كود كـstring (code) فتحفظه في ملف مؤقت وتفحصه.
        2) بتديها مسار مباشر (target_path) لملف أو مجلد على الـdisk.

    Args:
        code: كود Python كـstring (اختياري لو معندكش target_path)
        target_path: مسار ملف/مجلد على الـdisk (اختياري لو معندكش code)
        tool: "semgrep" أو "bandit"

    Returns:
        list[dict] فيها الـfindings (كل finding فيه severity, message, path, line, ...)
    """
    if tool not in ("semgrep", "bandit"):
        return [{"error": f"Unsupported tool '{tool}'. Use 'semgrep' or 'bandit'."}]

    cleanup_path = None
    if code is not None and target_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w")
        tmp.write(code)
        tmp.close()
        target_path = tmp.name
        cleanup_path = tmp.name
    elif target_path is None:
        return [{"error": "Either 'code' or 'target_path' must be provided."}]

    try:
        if tool == "semgrep":
            return _run_semgrep(target_path)
        return _run_bandit(target_path)
    finally:
        if cleanup_path and os.path.exists(cleanup_path):
            os.remove(cleanup_path)

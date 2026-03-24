"""
Ouroboros — Cybersecurity & Pentesting tools.

Defensive security, vulnerability scanning, security audits.
"""

from __future__ import annotations
import logging

from ouroboros.tools._adapter import adapt_tools
import json
import subprocess
from typing import Any, Dict, List

log = logging.getLogger(__name__)


def _run(cmd: List[str], timeout: int = 60) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return f"Error: {e}"


def security_scan(target: str, scan_type: str = "basic") -> Dict[str, Any]:
    """Run a security scan on a target (URL, IP, or codebase path)."""
    results = {"target": target, "scan_type": scan_type, "findings": []}

    if scan_type == "basic":
        # Check for common issues
        if target.startswith("http"):
            out = _run(["curl", "-sI", target], timeout=15)
            headers = out.lower()
            if "x-frame-options" not in headers:
                results["findings"].append({"severity": "medium", "issue": "Missing X-Frame-Options header"})
            if "content-security-policy" not in headers:
                results["findings"].append({"severity": "medium", "issue": "Missing Content-Security-Policy header"})
            if "strict-transport-security" not in headers:
                results["findings"].append({"severity": "high", "issue": "Missing HSTS header"})
            if "x-content-type-options" not in headers:
                results["findings"].append({"severity": "low", "issue": "Missing X-Content-Type-Options header"})
            results["raw_headers"] = out
        else:
            # Code scan
            out = _run(["grep", "-rn", "--include=*.py", "--include=*.js",
                        "-E", "(eval\\(|exec\\(|subprocess\\.call|os\\.system|password.*=.*['\"])",
                        target], timeout=30)
            if out:
                for line in out.split("\n")[:20]:
                    results["findings"].append({"severity": "high", "issue": f"Potential vulnerability: {line.strip()}"})

    elif scan_type == "dependencies":
        # Check for known vulnerable dependencies
        out = _run(["pip", "list", "--outdated", "--format=json"], timeout=30)
        try:
            outdated = json.loads(out)
            for pkg in outdated[:20]:
                results["findings"].append({
                    "severity": "medium",
                    "issue": f"Outdated: {pkg['name']} {pkg['version']} -> {pkg['latest_version']}"
                })
        except Exception:
            results["findings"].append({"severity": "info", "issue": f"Dependency check output: {out[:500]}"})

    results["total_findings"] = len(results["findings"])
    return results


def port_scan(target: str, ports: str = "80,443,8080,8443,22,21,3306,5432") -> Dict[str, Any]:
    """Scan common ports on a target host."""
    results = {"target": target, "open_ports": [], "closed_ports": []}
    for port in ports.split(","):
        port = port.strip()
        out = _run(["nc", "-z", "-w2", target, port], timeout=5)
        if "succeeded" in out.lower() or "open" in out.lower():
            results["open_ports"].append(int(port))
        else:
            results["closed_ports"].append(int(port))
    return results


def code_audit(path: str) -> Dict[str, Any]:
    """Audit code for security issues."""
    results = {"path": path, "issues": []}

    patterns = {
        "SQL Injection": r"(execute|cursor\.execute|raw_sql).*(%s|format|f[\"\'])",
        "XSS": r"(innerHTML|document\.write|\.html\()",
        "Hardcoded Secrets": r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
        "Insecure Deserialization": r"(pickle\.loads|yaml\.load\((?!.*Loader))",
        "Command Injection": r"(os\.system|subprocess\.call\(.*shell=True)",
        "Path Traversal": r"(\.\.\/|\.\.\\\\)",
    }

    for name, pattern in patterns.items():
        out = _run(["grep", "-rn", "--include=*.py", "--include=*.js",
                    "--include=*.ts", "-E", pattern, path], timeout=30)
        if out and "No such file" not in out:
            for line in out.split("\n")[:5]:
                if line.strip():
                    results["issues"].append({"type": name, "location": line.strip()})

    results["total_issues"] = len(results["issues"])
    return results


def _raw_tools() -> list:
    return [
        {
            "name": "security_scan",
            "description": "Run a security scan on a URL or codebase path. scan_type: 'basic' (headers/code patterns) or 'dependencies' (outdated packages).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "URL or filesystem path to scan"},
                    "scan_type": {"type": "string", "enum": ["basic", "dependencies"], "default": "basic"},
                },
                "required": ["target"],
            },
            "function": security_scan,
        },
        {
            "name": "port_scan",
            "description": "Scan ports on a target host to find open services.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Hostname or IP to scan"},
                    "ports": {"type": "string", "description": "Comma-separated port list", "default": "80,443,8080,8443,22,21,3306,5432"},
                },
                "required": ["target"],
            },
            "function": port_scan,
        },
        {
            "name": "code_audit",
            "description": "Audit a codebase for security vulnerabilities (SQL injection, XSS, hardcoded secrets, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to codebase directory"},
                },
                "required": ["path"],
            },
            "function": code_audit,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

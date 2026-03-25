"""
Ouroboros — Web tools.

Site health checker, DNS/WHOIS lookup, screenshot, SEO analyzer.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)


def _curl(url: str, timeout: int = 15, extra_args: List[str] = None) -> subprocess.CompletedProcess:
    cmd = [
        "curl", "-s", "-L", "--max-time", str(timeout),
        "-H", "User-Agent: Mozilla/5.0 (compatible; Ouroboros/1.0)",
    ]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)


# ── Site Health Checker ───────────────────────────────────────────────────

def site_health_check(url: str, check_ssl: bool = True,
                      check_headers: bool = True) -> Dict[str, Any]:
    """Check website health: HTTP status, response time, SSL, headers, redirects."""
    if not url.startswith("http"):
        url = f"https://{url}"

    parsed = urlparse(url)
    domain = parsed.hostname

    result = {
        "url": url,
        "domain": domain,
        "checked_at": datetime.now().isoformat(),
    }

    # HTTP check with timing
    try:
        start = time.time()
        r = _curl(url, extra_args=[
            "-o", "/dev/null",
            "-w", json.dumps({
                "status_code": "%{http_code}",
                "time_total": "%{time_total}",
                "time_connect": "%{time_connect}",
                "time_starttransfer": "%{time_starttransfer}",
                "time_namelookup": "%{time_namelookup}",
                "redirect_count": "%{num_redirects}",
                "redirect_url": "%{redirect_url}",
                "size_download": "%{size_download}",
                "ssl_verify_result": "%{ssl_verify_result}",
            }),
        ])
        elapsed = time.time() - start
        metrics = json.loads(r.stdout)
        result["http"] = {
            "status_code": int(metrics["status_code"]),
            "response_time_ms": round(float(metrics["time_total"]) * 1000, 1),
            "connect_time_ms": round(float(metrics["time_connect"]) * 1000, 1),
            "ttfb_ms": round(float(metrics["time_starttransfer"]) * 1000, 1),
            "dns_time_ms": round(float(metrics["time_namelookup"]) * 1000, 1),
            "redirects": int(metrics["redirect_count"]),
            "page_size_bytes": int(metrics["size_download"]),
        }

        status = int(metrics["status_code"])
        if status >= 500:
            result["http"]["health"] = "CRITICAL"
        elif status >= 400:
            result["http"]["health"] = "ERROR"
        elif status >= 300:
            result["http"]["health"] = "REDIRECT"
        else:
            result["http"]["health"] = "OK"

        # Performance rating
        ttfb = float(metrics["time_starttransfer"]) * 1000
        if ttfb < 200:
            result["http"]["performance"] = "excellent"
        elif ttfb < 500:
            result["http"]["performance"] = "good"
        elif ttfb < 1000:
            result["http"]["performance"] = "fair"
        else:
            result["http"]["performance"] = "poor"

    except Exception as e:
        result["http"] = {"error": str(e)}

    # SSL check
    if check_ssl and url.startswith("https"):
        try:
            r = subprocess.run(
                ["curl", "-vI", "--max-time", "10", url],
                capture_output=True, text=True, timeout=15,
            )
            stderr = r.stderr
            # Extract SSL info
            cert_info = {}
            expire_match = re.search(r'expire date: (.+)', stderr, re.IGNORECASE)
            if expire_match:
                cert_info["expires"] = expire_match.group(1).strip()
            issuer_match = re.search(r'issuer: (.+)', stderr, re.IGNORECASE)
            if issuer_match:
                cert_info["issuer"] = issuer_match.group(1).strip()
            subject_match = re.search(r'subject: (.+)', stderr, re.IGNORECASE)
            if subject_match:
                cert_info["subject"] = subject_match.group(1).strip()

            ssl_verify = metrics.get("ssl_verify_result", "0") if "metrics" in dir() else "0"
            cert_info["valid"] = ssl_verify == "0"

            result["ssl"] = cert_info
        except Exception as e:
            result["ssl"] = {"error": str(e)}

    # Security headers check
    if check_headers:
        try:
            r = _curl(url, extra_args=["-I"])
            headers_raw = r.stdout
            security_headers = {}
            important_headers = [
                "strict-transport-security", "content-security-policy",
                "x-content-type-options", "x-frame-options",
                "x-xss-protection", "referrer-policy",
                "permissions-policy", "server",
            ]
            for header_name in important_headers:
                match = re.search(rf'^{header_name}:\s*(.+)$', headers_raw, re.IGNORECASE | re.MULTILINE)
                if match:
                    security_headers[header_name] = match.group(1).strip()
                else:
                    security_headers[header_name] = "MISSING"

            missing_count = sum(1 for v in security_headers.values() if v == "MISSING")
            security_score = max(0, 100 - missing_count * 15)
            result["security_headers"] = security_headers
            result["security_score"] = security_score
        except Exception as e:
            result["security_headers"] = {"error": str(e)}

    return result


# ── DNS/WHOIS Lookup ──────────────────────────────────────────────────────

def dns_lookup(domain: str, record_types: List[str] = None) -> Dict[str, Any]:
    """Perform DNS lookups for a domain."""
    if not record_types:
        record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    result = {"domain": domain, "records": {}, "timestamp": datetime.now().isoformat()}

    for rtype in record_types:
        try:
            r = subprocess.run(
                ["nslookup", f"-type={rtype}", domain],
                capture_output=True, text=True, timeout=10,
            )
            output = r.stdout
            records = []

            if rtype == "A":
                records = re.findall(r'Address:\s*([\d.]+)', output)
                # Remove DNS server address (first match usually)
                if len(records) > 1:
                    records = records[1:]
            elif rtype == "AAAA":
                records = re.findall(r'Address:\s*([0-9a-fA-F:]+)', output)
                if len(records) > 1:
                    records = records[1:]
            elif rtype == "MX":
                records = re.findall(r'mail exchanger = (\d+)\s+(.+)', output)
                records = [{"priority": int(p), "server": s.strip().rstrip(".")} for p, s in records]
            elif rtype == "NS":
                records = re.findall(r'nameserver = (.+)', output)
                records = [s.strip().rstrip(".") for s in records]
            elif rtype == "TXT":
                records = re.findall(r'text = "(.+?)"', output)
            elif rtype == "CNAME":
                records = re.findall(r'canonical name = (.+)', output)
                records = [s.strip().rstrip(".") for s in records]
            elif rtype == "SOA":
                soa = re.search(r'origin = (.+?)(?:\n|\r)', output)
                if soa:
                    records = [soa.group(1).strip()]

            if records:
                result["records"][rtype] = records
        except Exception as e:
            result["records"][rtype] = {"error": str(e)}

    # Email provider detection from MX
    mx_records = result["records"].get("MX", [])
    if mx_records and isinstance(mx_records[0], dict):
        mx_text = " ".join(r.get("server", "") for r in mx_records).lower()
        if "google" in mx_text:
            result["email_provider"] = "Google Workspace"
        elif "outlook" in mx_text or "microsoft" in mx_text:
            result["email_provider"] = "Microsoft 365"
        elif "zoho" in mx_text:
            result["email_provider"] = "Zoho Mail"
        elif "protonmail" in mx_text or "proton" in mx_text:
            result["email_provider"] = "ProtonMail"
        else:
            result["email_provider"] = "Other"

    return result


def whois_lookup(domain: str) -> Dict[str, Any]:
    """Perform WHOIS lookup for a domain."""
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        r = subprocess.run(
            ["whois", domain], capture_output=True, text=True, timeout=15,
        )
        output = r.stdout

        info = {"domain": domain, "raw_length": len(output)}

        # Parse common WHOIS fields
        patterns = {
            "registrar": r'Registrar:\s*(.+)',
            "creation_date": r'Creat(?:ion|ed) Date:\s*(.+)',
            "expiration_date": r'(?:Registry Expiry|Expir(?:ation|y)) Date:\s*(.+)',
            "updated_date": r'Updated Date:\s*(.+)',
            "registrant_org": r'Registrant Organi[sz]ation:\s*(.+)',
            "registrant_country": r'Registrant Country:\s*(.+)',
            "name_servers": r'Name Server:\s*(.+)',
            "status": r'(?:Domain )?Status:\s*(.+)',
            "dnssec": r'DNSSEC:\s*(.+)',
        }

        for key, pattern in patterns.items():
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                if key in ("name_servers", "status"):
                    info[key] = [m.strip() for m in matches]
                else:
                    info[key] = matches[0].strip()

        return info
    except FileNotFoundError:
        return {"domain": domain, "error": "whois command not found. Install with: brew install whois (macOS) or apt install whois (Linux)"}
    except Exception as e:
        return {"domain": domain, "error": str(e)}


# ── SEO Analyzer ──────────────────────────────────────────────────────────

def seo_analyzer(url: str) -> Dict[str, Any]:
    """Analyze on-page SEO factors for a URL."""
    if not url.startswith("http"):
        url = f"https://{url}"

    result = {
        "url": url,
        "analyzed_at": datetime.now().isoformat(),
        "scores": {},
        "issues": [],
        "recommendations": [],
    }

    try:
        r = _curl(url)
        html = r.stdout
        if not html:
            return {"url": url, "error": "Could not fetch page"}

        # Title tag
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        result["title"] = {
            "text": title[:200],
            "length": len(title),
            "optimal": 30 <= len(title) <= 60,
        }
        if not title:
            result["issues"].append("Missing title tag")
        elif len(title) > 60:
            result["issues"].append(f"Title too long ({len(title)} chars, max 60)")
        elif len(title) < 30:
            result["issues"].append(f"Title too short ({len(title)} chars, min 30)")

        # Meta description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else ""
        result["meta_description"] = {
            "text": description[:300],
            "length": len(description),
            "optimal": 120 <= len(description) <= 160,
        }
        if not description:
            result["issues"].append("Missing meta description")
        elif len(description) > 160:
            result["issues"].append(f"Meta description too long ({len(description)} chars, max 160)")

        # Headings
        h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE | re.DOTALL)
        h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.IGNORECASE | re.DOTALL)

        h1_texts = [re.sub(r'<[^>]+>', '', h).strip() for h in h1s]
        result["headings"] = {
            "h1_count": len(h1s),
            "h2_count": len(h2s),
            "h3_count": len(h3s),
            "h1_texts": h1_texts[:5],
        }
        if len(h1s) == 0:
            result["issues"].append("Missing H1 tag")
        elif len(h1s) > 1:
            result["issues"].append(f"Multiple H1 tags ({len(h1s)}) — should be exactly 1")

        # Images without alt text
        images = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
        images_no_alt = [img for img in images if 'alt=' not in img.lower() or 'alt=""' in img.lower() or "alt=''" in img.lower()]
        result["images"] = {
            "total": len(images),
            "missing_alt": len(images_no_alt),
        }
        if images_no_alt:
            result["issues"].append(f"{len(images_no_alt)} images missing alt text")

        # Links
        internal_links = re.findall(r'href=["\'](/[^"\']*)["\']', html)
        external_links = re.findall(r'href=["\'](https?://[^"\']*)["\']', html)
        parsed_url = urlparse(url)
        own_domain = parsed_url.hostname
        truly_external = [l for l in external_links if own_domain not in l]

        result["links"] = {
            "internal": len(internal_links),
            "external": len(truly_external),
            "total": len(internal_links) + len(truly_external),
        }

        # Meta robots
        robots_match = re.search(r'<meta[^>]*name=["\']robots["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        if robots_match:
            result["robots"] = robots_match.group(1)
            if "noindex" in robots_match.group(1).lower():
                result["issues"].append("Page has noindex directive — will not be indexed")

        # Canonical
        canonical_match = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']', html, re.IGNORECASE)
        result["canonical"] = canonical_match.group(1) if canonical_match else "MISSING"
        if not canonical_match:
            result["issues"].append("Missing canonical tag")

        # Open Graph
        og_tags = re.findall(r'<meta[^>]*property=["\']og:(\w+)["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        result["open_graph"] = {k: v for k, v in og_tags}
        if not og_tags:
            result["issues"].append("Missing Open Graph tags (og:title, og:description, og:image)")

        # Mobile viewport
        viewport = re.search(r'<meta[^>]*name=["\']viewport["\']', html, re.IGNORECASE)
        if not viewport:
            result["issues"].append("Missing viewport meta tag — not mobile-friendly")

        # Schema.org / structured data
        has_schema = 'application/ld+json' in html.lower() or 'itemtype' in html.lower()
        result["structured_data"] = has_schema
        if not has_schema:
            result["recommendations"].append("Add structured data (JSON-LD) for rich search results")

        # Score calculation
        total_checks = 10
        passed = total_checks - len(result["issues"])
        result["seo_score"] = max(0, round(passed / total_checks * 100))

        # Recommendations
        if result["seo_score"] < 50:
            result["recommendations"].insert(0, "Critical SEO issues found — address the issues listed above")
        if len(truly_external) == 0:
            result["recommendations"].append("Add relevant external links to authoritative sources")
        if len(internal_links) < 5:
            result["recommendations"].append("Increase internal linking for better crawlability")

    except Exception as e:
        result["error"] = str(e)

    return result


# ── Screenshot ─────────────────────────────────────────────────────────────

def web_screenshot(url: str, width: int = 1280, height: int = 720,
                   full_page: bool = False) -> Dict[str, Any]:
    """Take a screenshot of a web page using playwright if available."""
    if not url.startswith("http"):
        url = f"https://{url}"

    _ws = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_web")
    os.makedirs(_ws, exist_ok=True)
    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(_ws, filename)

    # Try playwright first
    try:
        script = f"""
import asyncio
from playwright.async_api import async_playwright

async def screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={{"width": {width}, "height": {height}}})
        await page.goto("{url}", wait_until="networkidle", timeout=30000)
        await page.screenshot(path="{filepath}", full_page={str(full_page)})
        title = await page.title()
        await browser.close()
        return title

title = asyncio.run(screenshot())
print(title)
"""
        r = subprocess.run(
            ["python3", "-c", script],
            capture_output=True, text=True, timeout=45,
        )
        if r.returncode == 0 and os.path.exists(filepath):
            return {
                "url": url,
                "screenshot_path": filepath,
                "title": r.stdout.strip(),
                "dimensions": f"{width}x{height}",
                "full_page": full_page,
            }
        # If playwright fails, fall through
    except Exception:
        pass

    # Fallback: try wkhtmltoimage
    try:
        r = subprocess.run(
            ["wkhtmltoimage", "--width", str(width), url, filepath],
            capture_output=True, text=True, timeout=30,
        )
        if os.path.exists(filepath):
            return {
                "url": url,
                "screenshot_path": filepath,
                "method": "wkhtmltoimage",
                "dimensions": f"{width}x{height}",
            }
    except FileNotFoundError:
        pass

    return {
        "url": url,
        "error": "Screenshot tools not available. Install playwright (pip install playwright && playwright install) or wkhtmltoimage.",
    }


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "site_health_check",
            "description": "Check website health: HTTP status, response time, SSL cert, security headers, performance rating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL or domain to check"},
                    "check_ssl": {"type": "boolean", "default": True},
                    "check_headers": {"type": "boolean", "default": True},
                },
                "required": ["url"],
            },
            "function": site_health_check,
        },
        {
            "name": "dns_lookup",
            "description": "DNS lookup: A, AAAA, MX, NS, TXT, CNAME, SOA records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "record_types": {"type": "array", "items": {"type": "string"},
                                     "description": "Record types to query (default: all common types)"},
                },
                "required": ["domain"],
            },
            "function": dns_lookup,
        },
        {
            "name": "whois_lookup",
            "description": "WHOIS lookup: registrar, dates, registrant info, name servers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                },
                "required": ["domain"],
            },
            "function": whois_lookup,
        },
        {
            "name": "seo_analyzer",
            "description": "Analyze on-page SEO: title, meta, headings, images, links, structured data, score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                },
                "required": ["url"],
            },
            "function": seo_analyzer,
        },
        {
            "name": "web_screenshot",
            "description": "Take a screenshot of a web page (requires playwright or wkhtmltoimage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "width": {"type": "integer", "default": 1280},
                    "height": {"type": "integer", "default": 720},
                    "full_page": {"type": "boolean", "default": False},
                },
                "required": ["url"],
            },
            "function": web_screenshot,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

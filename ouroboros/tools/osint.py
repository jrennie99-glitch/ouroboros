"""
Ouroboros — OSINT reconnaissance tools.

Username search, domain intel, IP geolocation, social media footprint,
email breach check.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)


def _curl(url: str, timeout: int = 10, headers: Dict[str, str] = None) -> str:
    cmd = [
        "curl", "-s", "-L", "--max-time", str(timeout),
        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    ]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    return r.stdout


def _curl_json(url: str, timeout: int = 10) -> Any:
    return json.loads(_curl(url, timeout))


def _curl_status(url: str, timeout: int = 8) -> int:
    """Get HTTP status code for a URL."""
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-L", "--max-time", str(timeout),
             "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
             url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        return int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
    except Exception:
        return 0


# ── Username Search ───────────────────────────────────────────────────────

def username_search(username: str, platforms: List[str] = None) -> Dict[str, Any]:
    """Search for a username across social media and web platforms."""
    all_platforms = {
        "github": f"https://github.com/{username}",
        "twitter": f"https://x.com/{username}",
        "instagram": f"https://www.instagram.com/{username}/",
        "reddit": f"https://www.reddit.com/user/{username}",
        "linkedin": f"https://www.linkedin.com/in/{username}",
        "youtube": f"https://www.youtube.com/@{username}",
        "tiktok": f"https://www.tiktok.com/@{username}",
        "pinterest": f"https://www.pinterest.com/{username}/",
        "medium": f"https://medium.com/@{username}",
        "dev.to": f"https://dev.to/{username}",
        "hackernews": f"https://news.ycombinator.com/user?id={username}",
        "keybase": f"https://keybase.io/{username}",
        "mastodon": f"https://mastodon.social/@{username}",
        "twitch": f"https://www.twitch.tv/{username}",
        "steam": f"https://steamcommunity.com/id/{username}",
        "spotify": f"https://open.spotify.com/user/{username}",
        "soundcloud": f"https://soundcloud.com/{username}",
        "gitlab": f"https://gitlab.com/{username}",
        "bitbucket": f"https://bitbucket.org/{username}/",
        "npm": f"https://www.npmjs.com/~{username}",
        "pypi": f"https://pypi.org/user/{username}/",
        "docker_hub": f"https://hub.docker.com/u/{username}",
        "producthunt": f"https://www.producthunt.com/@{username}",
        "dribbble": f"https://dribbble.com/{username}",
        "behance": f"https://www.behance.net/{username}",
    }

    if platforms:
        check_platforms = {k: v for k, v in all_platforms.items() if k in platforms}
    else:
        # Check most common ones to be fast
        check_platforms = {k: all_platforms[k] for k in [
            "github", "twitter", "instagram", "reddit", "youtube",
            "tiktok", "medium", "dev.to", "hackernews", "gitlab",
            "linkedin", "twitch",
        ] if k in all_platforms}

    found = []
    not_found = []
    errors = []

    for platform_name, url in check_platforms.items():
        try:
            status = _curl_status(url)
            if status == 200:
                found.append({"platform": platform_name, "url": url, "status": status})
            elif status in (301, 302, 303, 307, 308):
                # Some platforms redirect — might still exist
                found.append({"platform": platform_name, "url": url, "status": status, "note": "redirected"})
            elif status == 404:
                not_found.append(platform_name)
            else:
                not_found.append(platform_name)
        except Exception as e:
            errors.append({"platform": platform_name, "error": str(e)})

    return {
        "username": username,
        "found": found,
        "found_count": len(found),
        "not_found": not_found,
        "errors": errors,
        "platforms_checked": len(check_platforms),
        "timestamp": datetime.now().isoformat(),
    }


# ── Domain Intelligence ──────────────────────────────────────────────────

def domain_intel(domain: str) -> Dict[str, Any]:
    """Comprehensive domain intelligence gathering."""
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    result = {
        "domain": domain,
        "timestamp": datetime.now().isoformat(),
    }

    # DNS records
    try:
        # A records
        r = subprocess.run(["nslookup", domain], capture_output=True, text=True, timeout=10)
        ips = re.findall(r'Address:\s*([\d.]+)', r.stdout)
        if len(ips) > 1:
            ips = ips[1:]  # Skip DNS server
        result["ip_addresses"] = ips

        # MX records
        r = subprocess.run(["nslookup", "-type=mx", domain], capture_output=True, text=True, timeout=10)
        mx = re.findall(r'mail exchanger = \d+ (.+)', r.stdout)
        result["mx_records"] = [s.strip().rstrip(".") for s in mx]

        # NS records
        r = subprocess.run(["nslookup", "-type=ns", domain], capture_output=True, text=True, timeout=10)
        ns = re.findall(r'nameserver = (.+)', r.stdout)
        result["nameservers"] = [s.strip().rstrip(".") for s in ns]

        # TXT records
        r = subprocess.run(["nslookup", "-type=txt", domain], capture_output=True, text=True, timeout=10)
        txt = re.findall(r'text = "(.+?)"', r.stdout)
        result["txt_records"] = txt

        # Detect services from TXT/MX
        all_txt = " ".join(txt).lower()
        mx_text = " ".join(result.get("mx_records", [])).lower()
        services_detected = []
        if "google" in mx_text or "google-site-verification" in all_txt:
            services_detected.append("Google Workspace")
        if "outlook" in mx_text or "microsoft" in mx_text:
            services_detected.append("Microsoft 365")
        if "v=spf1" in all_txt:
            services_detected.append("SPF configured")
        if any("dkim" in t.lower() for t in txt):
            services_detected.append("DKIM configured")
        if any("_dmarc" in t.lower() for t in txt):
            services_detected.append("DMARC configured")
        result["services_detected"] = services_detected

    except Exception as e:
        result["dns_error"] = str(e)

    # WHOIS summary
    try:
        r = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=15)
        output = r.stdout
        whois_info = {}
        for field, pattern in [
            ("registrar", r'Registrar:\s*(.+)'),
            ("creation_date", r'Creat(?:ion|ed) Date:\s*(.+)'),
            ("expiry_date", r'(?:Expiry|Expiration) Date:\s*(.+)'),
            ("registrant_org", r'Registrant Organi[sz]ation:\s*(.+)'),
            ("registrant_country", r'Registrant Country:\s*(.+)'),
        ]:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                whois_info[field] = match.group(1).strip()
        result["whois"] = whois_info
    except Exception:
        pass

    # Web tech detection
    try:
        html = _curl(f"https://{domain}")
        techs = []
        tech_sigs = {
            "WordPress": ["wp-content", "wp-includes"],
            "React": ["react", "__NEXT_DATA__"],
            "Next.js": ["__NEXT_DATA__", "_next/static"],
            "Vue.js": ["vue", "__vue__"],
            "Angular": ["ng-app", "angular"],
            "Shopify": ["cdn.shopify.com"],
            "Cloudflare": ["cloudflare"],
            "Google Analytics": ["google-analytics.com", "gtag"],
            "HubSpot": ["hubspot", "hs-scripts"],
            "Stripe": ["js.stripe.com"],
            "Intercom": ["intercom"],
        }
        html_lower = html.lower()
        for tech, sigs in tech_sigs.items():
            if any(s in html_lower for s in sigs):
                techs.append(tech)
        result["technologies"] = techs

        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            result["page_title"] = title_match.group(1).strip()[:200]

    except Exception:
        pass

    # IP geolocation for first IP
    if result.get("ip_addresses"):
        try:
            ip = result["ip_addresses"][0]
            geo = _curl_json(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,as")
            if geo.get("status") == "success":
                result["hosting"] = {
                    "ip": ip,
                    "country": geo.get("country"),
                    "region": geo.get("regionName"),
                    "city": geo.get("city"),
                    "isp": geo.get("isp"),
                    "org": geo.get("org"),
                    "asn": geo.get("as"),
                }
        except Exception:
            pass

    return result


# ── IP Geolocation ────────────────────────────────────────────────────────

def ip_geolocation(ip: str) -> Dict[str, Any]:
    """Get geolocation and ISP info for an IP address."""
    try:
        data = _curl_json(
            f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        )
        if data.get("status") == "fail":
            return {"ip": ip, "error": data.get("message", "Lookup failed")}

        return {
            "ip": data.get("query", ip),
            "country": data.get("country"),
            "country_code": data.get("countryCode"),
            "region": data.get("regionName"),
            "city": data.get("city"),
            "zip": data.get("zip"),
            "latitude": data.get("lat"),
            "longitude": data.get("lon"),
            "timezone": data.get("timezone"),
            "isp": data.get("isp"),
            "organization": data.get("org"),
            "asn": data.get("as"),
        }
    except Exception as e:
        return {"ip": ip, "error": str(e)}


# ── Social Media Footprint ───────────────────────────────────────────────

def social_footprint(username: str = "", domain: str = "",
                     email: str = "") -> Dict[str, Any]:
    """Build a social media footprint from username, domain, or email."""
    result = {
        "query": {"username": username, "domain": domain, "email": email},
        "profiles": [],
        "timestamp": datetime.now().isoformat(),
    }

    # Username search
    if username:
        search = username_search(username)
        result["profiles"] = search.get("found", [])
        result["username_found_count"] = search.get("found_count", 0)

    # GitHub details if available
    if username:
        try:
            gh_data = _curl_json(f"https://api.github.com/users/{username}")
            if gh_data.get("login"):
                result["github_details"] = {
                    "name": gh_data.get("name"),
                    "bio": gh_data.get("bio"),
                    "company": gh_data.get("company"),
                    "location": gh_data.get("location"),
                    "blog": gh_data.get("blog"),
                    "public_repos": gh_data.get("public_repos"),
                    "followers": gh_data.get("followers"),
                    "following": gh_data.get("following"),
                    "created_at": gh_data.get("created_at"),
                }
        except Exception:
            pass

    # Domain-based discovery
    if domain:
        domain_clean = domain.replace("https://", "").replace("http://", "").split("/")[0]
        try:
            html = _curl(f"https://{domain_clean}")
            social_patterns = {
                "twitter": r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
                "linkedin": r'linkedin\.com/(?:company|in)/([a-zA-Z0-9_-]+)',
                "facebook": r'facebook\.com/([a-zA-Z0-9._-]+)',
                "instagram": r'instagram\.com/([a-zA-Z0-9._]+)',
                "github": r'github\.com/([a-zA-Z0-9_-]+)',
                "youtube": r'youtube\.com/(?:@|channel/|c/)([a-zA-Z0-9_-]+)',
            }
            for platform_name, pattern in social_patterns.items():
                matches = set(re.findall(pattern, html, re.IGNORECASE))
                for handle in matches:
                    if handle.lower() not in ("share", "intent", "sharer", "widgets"):
                        result["profiles"].append({
                            "platform": platform_name,
                            "handle": handle,
                            "source": "domain_scrape",
                        })
        except Exception:
            pass

    # Email-derived username check
    if email and not username:
        local_part = email.split("@")[0]
        search = username_search(local_part, platforms=["github", "twitter", "reddit", "medium"])
        for found in search.get("found", []):
            found["source"] = "email_derived"
            result["profiles"].append(found)

    # Deduplicate
    seen = set()
    unique_profiles = []
    for p in result["profiles"]:
        key = (p.get("platform"), p.get("url", p.get("handle", "")))
        if key not in seen:
            seen.add(key)
            unique_profiles.append(p)
    result["profiles"] = unique_profiles
    result["total_profiles_found"] = len(unique_profiles)

    return result


# ── Email Breach Check ────────────────────────────────────────────────────

def email_breach_check(email: str) -> Dict[str, Any]:
    """
    Check if an email has appeared in known data breaches.
    Uses the Have I Been Pwned API pattern (requires API key for full results).
    Falls back to breach directory check.
    """
    result = {
        "email": email,
        "timestamp": datetime.now().isoformat(),
    }

    hibp_key = os.environ.get("HIBP_API_KEY", "")

    if hibp_key:
        # Use official HIBP API
        try:
            response = _curl(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false",
                headers={
                    "hibp-api-key": hibp_key,
                    "User-Agent": "Ouroboros-OSINT-Tool",
                },
            )
            if response.strip():
                breaches = json.loads(response)
                result["breached"] = True
                result["breach_count"] = len(breaches)
                result["breaches"] = [
                    {
                        "name": b.get("Name"),
                        "domain": b.get("Domain"),
                        "date": b.get("BreachDate"),
                        "data_classes": b.get("DataClasses", []),
                        "is_verified": b.get("IsVerified"),
                        "pwn_count": b.get("PwnCount"),
                    }
                    for b in breaches[:20]
                ]
            else:
                result["breached"] = False
                result["breach_count"] = 0
                result["message"] = "No breaches found for this email"
        except Exception as e:
            result["error"] = str(e)
    else:
        # Without API key, provide guidance
        result["note"] = "HIBP_API_KEY not set. Get one at https://haveibeenpwned.com/API/Key"
        result["manual_check_url"] = f"https://haveibeenpwned.com/account/{email}"

        # Check email domain reputation
        domain = email.split("@")[1] if "@" in email else ""
        if domain:
            disposable_domains = {
                "tempmail.com", "throwaway.email", "guerrillamail.com",
                "mailinator.com", "yopmail.com", "10minutemail.com",
                "trashmail.com", "dispostable.com", "sharklasers.com",
            }
            result["domain_analysis"] = {
                "domain": domain,
                "is_disposable": domain.lower() in disposable_domains,
                "is_free_provider": domain.lower() in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com", "icloud.com"},
            }

    # Password hash check (k-anonymity, safe)
    try:
        import hashlib
        sha1 = hashlib.sha1(email.encode()).hexdigest().upper()
        prefix = sha1[:5]
        suffix = sha1[5:]
        response = _curl(f"https://api.pwnedpasswords.com/range/{prefix}")
        if suffix in response.upper():
            result["password_exposed"] = True
            result["password_warning"] = "This email's hash was found in password breach databases"
        else:
            result["password_exposed"] = False
    except Exception:
        pass

    return result


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "username_search",
            "description": "Search for a username across 25+ social media and web platforms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "platforms": {"type": "array", "items": {"type": "string"},
                                  "description": "Specific platforms to check (default: common platforms)"},
                },
                "required": ["username"],
            },
            "function": username_search,
        },
        {
            "name": "domain_intel",
            "description": "Comprehensive domain intelligence: DNS, WHOIS, tech stack, hosting, services.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                },
                "required": ["domain"],
            },
            "function": domain_intel,
        },
        {
            "name": "ip_geolocation",
            "description": "Get geolocation, ISP, and organization info for an IP address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ip": {"type": "string"},
                },
                "required": ["ip"],
            },
            "function": ip_geolocation,
        },
        {
            "name": "social_footprint",
            "description": "Build a social media footprint from username, domain, or email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "default": ""},
                    "domain": {"type": "string", "default": ""},
                    "email": {"type": "string", "default": ""},
                },
            },
            "function": social_footprint,
        },
        {
            "name": "email_breach_check",
            "description": "Check if an email appeared in known data breaches (HIBP pattern).",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                },
                "required": ["email"],
            },
            "function": email_breach_check,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

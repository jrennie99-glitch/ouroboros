"""
Ouroboros — Lead generation tools.

Lead scraper, email finder, cold outreach templates, CRM pipeline,
competitive analysis.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_leadgen")
CRM_PATH = os.path.join(WORKSPACE, "crm.json")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


def _curl(url: str, timeout: int = 15) -> str:
    r = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(timeout),
         "-H", "User-Agent: Mozilla/5.0 (compatible; Ouroboros/1.0)", url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    return r.stdout


def _curl_json(url: str, timeout: int = 15) -> Any:
    return json.loads(_curl(url, timeout))


def _load_crm() -> Dict[str, Any]:
    _ensure_workspace()
    if os.path.exists(CRM_PATH):
        with open(CRM_PATH) as f:
            return json.load(f)
    return {
        "leads": [],
        "pipeline": {"new": [], "contacted": [], "qualified": [], "proposal": [], "closed_won": [], "closed_lost": []},
        "created": datetime.now().isoformat(),
    }


def _save_crm(crm: Dict[str, Any]):
    _ensure_workspace()
    with open(CRM_PATH, "w") as f:
        json.dump(crm, f, indent=2)


# ── Lead Scraper ──────────────────────────────────────────────────────────

def lead_scraper(domain: str, depth: str = "basic") -> Dict[str, Any]:
    """Scrape publicly available information about a company from its domain."""
    result = {
        "domain": domain,
        "scraped_at": datetime.now().isoformat(),
        "company_info": {},
        "contacts": [],
        "social_links": [],
        "tech_stack": [],
    }

    # Fetch homepage
    try:
        html = _curl(f"https://{domain}")

        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            result["company_info"]["title"] = title_match.group(1).strip()[:200]

        # Extract meta description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        if desc_match:
            result["company_info"]["description"] = desc_match.group(1).strip()[:500]

        # Extract emails from page
        emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html))
        # Filter out common non-personal emails
        for email in emails:
            if not any(x in email.lower() for x in ['example.com', 'sentry.io', 'webpack']):
                result["contacts"].append({"email": email, "source": "website"})

        # Extract social links
        social_patterns = {
            "linkedin": r'linkedin\.com/(?:company|in)/[a-zA-Z0-9_-]+',
            "twitter": r'(?:twitter|x)\.com/[a-zA-Z0-9_]+',
            "facebook": r'facebook\.com/[a-zA-Z0-9._-]+',
            "instagram": r'instagram\.com/[a-zA-Z0-9._]+',
            "github": r'github\.com/[a-zA-Z0-9_-]+',
            "youtube": r'youtube\.com/(?:@|channel/|c/)[a-zA-Z0-9_-]+',
        }
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, html, re.IGNORECASE)
            for m in set(matches):
                result["social_links"].append({"platform": platform, "url": f"https://{m}"})

        # Detect tech stack from HTML
        tech_indicators = {
            "React": ["react", "__NEXT_DATA__", "reactroot"],
            "Next.js": ["__NEXT_DATA__", "_next/static"],
            "Vue.js": ["vue", "__vue__"],
            "Angular": ["ng-", "angular"],
            "WordPress": ["wp-content", "wp-includes"],
            "Shopify": ["cdn.shopify.com", "Shopify.theme"],
            "Squarespace": ["squarespace"],
            "Wix": ["wix.com", "_wixCIDRequired"],
            "Google Analytics": ["google-analytics.com", "gtag"],
            "Google Tag Manager": ["googletagmanager.com"],
            "Stripe": ["js.stripe.com"],
            "Intercom": ["intercom", "intercomSettings"],
            "HubSpot": ["hubspot", "hs-scripts"],
            "Cloudflare": ["cloudflare"],
            "Tailwind CSS": ["tailwind"],
            "Bootstrap": ["bootstrap"],
        }
        html_lower = html.lower()
        for tech, indicators in tech_indicators.items():
            if any(ind.lower() in html_lower for ind in indicators):
                result["tech_stack"].append(tech)

    except Exception as e:
        result["error"] = f"Failed to scrape: {e}"

    # DNS lookup for more info
    try:
        dns = subprocess.run(
            ["nslookup", domain], capture_output=True, text=True, timeout=10,
        )
        mx = subprocess.run(
            ["nslookup", "-type=mx", domain], capture_output=True, text=True, timeout=10,
        )
        mx_records = re.findall(r'mail exchanger = \d+ (.+)', mx.stdout)
        if mx_records:
            result["company_info"]["email_provider"] = _detect_email_provider(mx_records)
    except Exception:
        pass

    return result


def _detect_email_provider(mx_records: List[str]) -> str:
    mx_text = " ".join(mx_records).lower()
    if "google" in mx_text or "gmail" in mx_text:
        return "Google Workspace"
    elif "outlook" in mx_text or "microsoft" in mx_text:
        return "Microsoft 365"
    elif "zoho" in mx_text:
        return "Zoho Mail"
    elif "protonmail" in mx_text:
        return "ProtonMail"
    elif "mimecast" in mx_text:
        return "Mimecast"
    return mx_records[0] if mx_records else "Unknown"


# ── Email Finder ──────────────────────────────────────────────────────────

def email_finder(first_name: str, last_name: str, domain: str) -> Dict[str, Any]:
    """Generate likely email addresses using common patterns (hunter.io style)."""
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    fi = first[0] if first else ""
    li = last[0] if last else ""

    patterns = [
        f"{first}.{last}@{domain}",
        f"{first}{last}@{domain}",
        f"{fi}{last}@{domain}",
        f"{first}_{last}@{domain}",
        f"{first}-{last}@{domain}",
        f"{first}@{domain}",
        f"{last}.{first}@{domain}",
        f"{fi}.{last}@{domain}",
        f"{first}{li}@{domain}",
    ]

    # Try to detect which pattern the domain uses via MX
    provider = "Unknown"
    try:
        mx = subprocess.run(
            ["nslookup", "-type=mx", domain], capture_output=True, text=True, timeout=10,
        )
        mx_records = re.findall(r'mail exchanger = \d+ (.+)', mx.stdout)
        provider = _detect_email_provider(mx_records)
    except Exception:
        pass

    # Most common patterns by provider
    if provider == "Google Workspace":
        most_likely = [f"{first}.{last}@{domain}", f"{first}@{domain}", f"{fi}{last}@{domain}"]
    elif provider == "Microsoft 365":
        most_likely = [f"{first}.{last}@{domain}", f"{fi}{last}@{domain}", f"{first}{last}@{domain}"]
    else:
        most_likely = [f"{first}.{last}@{domain}", f"{first}@{domain}"]

    return {
        "name": f"{first_name} {last_name}",
        "domain": domain,
        "email_provider": provider,
        "most_likely": most_likely,
        "all_patterns": patterns,
        "verification_tip": "Verify emails before sending. Use SMTP verification or send a test.",
    }


# ── Cold Outreach Templates ──────────────────────────────────────────────

def outreach_template(template_type: str = "cold_email",
                      industry: str = "saas",
                      offering: str = "",
                      tone: str = "professional") -> Dict[str, Any]:
    """Generate cold outreach templates for email, LinkedIn, etc."""
    templates = {
        "cold_email": {
            "professional": {
                "subject_lines": [
                    "Quick question about {{company_name}}",
                    "{{first_name}}, idea for {{company_name}}",
                    "Saw {{recent_trigger}} — thought of this",
                    "{{mutual_connection}} suggested I reach out",
                ],
                "body": textwrap.dedent("""
                    Hi {{first_name}},

                    I noticed {{company_name}} is {{observation_about_company}}.

                    We help companies like yours {{value_proposition}}.

                    {{social_proof_one_liner}}

                    Would it make sense to chat for 15 minutes this week?

                    Best,
                    {{your_name}}
                """).strip(),
                "follow_ups": [
                    {"days_after": 3, "subject": "Re: Quick question", "body": "Just bumping this up — I know things get buried. {{one_line_value_prop}}. Worth a quick call?"},
                    {"days_after": 7, "subject": "Re: Quick question", "body": "Hey {{first_name}}, last follow up. {{case_study_result}}. If timing isn't right, no worries at all."},
                ],
            },
            "casual": {
                "subject_lines": [
                    "Hey {{first_name}} — quick thought",
                    "This might be useful for {{company_name}}",
                    "No pitch, just an idea",
                ],
                "body": textwrap.dedent("""
                    Hey {{first_name}},

                    Came across {{company_name}} and had a thought.

                    {{observation_or_compliment}}

                    We've been helping similar companies {{specific_result}}.

                    No pressure at all — but if you're curious, happy to share more.

                    Cheers,
                    {{your_name}}
                """).strip(),
            },
        },
        "linkedin_connect": {
            "professional": {
                "message": "Hi {{first_name}}, I came across your profile and was impressed by {{specific_detail}}. I work in {{your_industry}} and thought it'd be great to connect. Looking forward to learning from your experience.",
            },
        },
        "linkedin_inmail": {
            "professional": {
                "subject": "{{first_name}}, thought of {{company_name}}",
                "body": "Hi {{first_name}},\n\n{{observation}}.\n\nWe help {{target_audience}} achieve {{result}}. {{social_proof}}.\n\nWould love to connect if you're open to it.\n\nBest,\n{{your_name}}",
            },
        },
    }

    template = templates.get(template_type, templates["cold_email"])
    tone_template = template.get(tone, template.get("professional", {}))

    return {
        "type": template_type,
        "tone": tone,
        "industry": industry,
        "template": tone_template,
        "best_practices": [
            "Personalize the first line — reference something specific",
            "Keep subject lines under 6 words",
            "Body should be under 100 words",
            "Include one clear CTA",
            "Follow up 2-3 times max",
            "Best send times: Tue-Thu, 8-10am or 3-5pm recipient's timezone",
        ],
        "variables_to_fill": [
            "{{first_name}}", "{{company_name}}", "{{your_name}}",
            "{{observation_about_company}}", "{{value_proposition}}",
            "{{social_proof_one_liner}}",
        ],
    }


# ── CRM Pipeline ─────────────────────────────────────────────────────────

def crm_manage(action: str, lead_name: str = "", email: str = "",
               company: str = "", stage: str = "new",
               notes: str = "", deal_value: float = 0) -> Dict[str, Any]:
    """Manage CRM pipeline: add leads, move stages, view pipeline."""
    crm = _load_crm()

    if action == "add":
        lead = {
            "id": len(crm["leads"]) + 1,
            "name": lead_name,
            "email": email,
            "company": company,
            "stage": stage,
            "notes": notes,
            "deal_value": deal_value,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }
        crm["leads"].append(lead)
        if stage in crm["pipeline"]:
            crm["pipeline"][stage].append(lead["id"])
        _save_crm(crm)
        return {"action": "added", "lead": lead}

    elif action == "move":
        for lead in crm["leads"]:
            if lead["name"].lower() == lead_name.lower() or lead.get("email", "").lower() == email.lower():
                old_stage = lead["stage"]
                lead["stage"] = stage
                lead["updated"] = datetime.now().isoformat()
                # Update pipeline
                if old_stage in crm["pipeline"] and lead["id"] in crm["pipeline"][old_stage]:
                    crm["pipeline"][old_stage].remove(lead["id"])
                if stage in crm["pipeline"]:
                    crm["pipeline"][stage].append(lead["id"])
                _save_crm(crm)
                return {"action": "moved", "lead": lead, "from": old_stage, "to": stage}
        return {"error": f"Lead not found: {lead_name or email}"}

    elif action == "view":
        pipeline_summary = {}
        for stage_name, ids in crm["pipeline"].items():
            leads_in_stage = [l for l in crm["leads"] if l["id"] in ids]
            pipeline_summary[stage_name] = {
                "count": len(leads_in_stage),
                "total_value": sum(l.get("deal_value", 0) for l in leads_in_stage),
                "leads": [{"name": l["name"], "company": l.get("company", ""), "value": l.get("deal_value", 0)} for l in leads_in_stage],
            }
        total_pipeline_value = sum(l.get("deal_value", 0) for l in crm["leads"] if l["stage"] not in ("closed_lost",))
        return {
            "pipeline": pipeline_summary,
            "total_leads": len(crm["leads"]),
            "total_pipeline_value": total_pipeline_value,
        }

    elif action == "search":
        query = (lead_name or email or company).lower()
        matches = [l for l in crm["leads"] if query in json.dumps(l).lower()]
        return {"matches": matches, "count": len(matches)}

    return {"error": f"Unknown action: {action}"}


# ── Competitive Analysis ─────────────────────────────────────────────────

def competitive_analysis(domain: str, competitors: List[str] = None) -> Dict[str, Any]:
    """Analyze a company and its competitive landscape."""
    result = {
        "target": domain,
        "analysis": {},
        "timestamp": datetime.now().isoformat(),
    }

    # Scrape target
    target_info = lead_scraper(domain)
    result["analysis"]["target"] = {
        "domain": domain,
        "title": target_info.get("company_info", {}).get("title", ""),
        "description": target_info.get("company_info", {}).get("description", ""),
        "tech_stack": target_info.get("tech_stack", []),
        "social_presence": [s["platform"] for s in target_info.get("social_links", [])],
    }

    # Analyze competitors
    if competitors:
        result["analysis"]["competitors"] = []
        for comp in competitors[:5]:  # Limit to 5 competitors
            try:
                comp_info = lead_scraper(comp)
                result["analysis"]["competitors"].append({
                    "domain": comp,
                    "title": comp_info.get("company_info", {}).get("title", ""),
                    "description": comp_info.get("company_info", {}).get("description", ""),
                    "tech_stack": comp_info.get("tech_stack", []),
                    "social_presence": [s["platform"] for s in comp_info.get("social_links", [])],
                })
            except Exception:
                result["analysis"]["competitors"].append({"domain": comp, "error": "Scrape failed"})

    # Generate competitive comparison
    all_tech = set(target_info.get("tech_stack", []))
    if competitors:
        for comp in result["analysis"].get("competitors", []):
            all_tech.update(comp.get("tech_stack", []))

    result["analysis"]["comparison"] = {
        "all_technologies_used": sorted(all_tech),
        "recommendation": "Analyze pricing pages, feature sets, and customer reviews for deeper competitive intelligence.",
    }

    return result


# ── Raw tools ──────────────────────────────────────────────────────────────

import textwrap

def _raw_tools() -> list:
    return [
        {
            "name": "lead_scraper",
            "description": "Scrape company info, contacts, social links, and tech stack from a domain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Company domain (e.g. acme.com)"},
                    "depth": {"type": "string", "default": "basic"},
                },
                "required": ["domain"],
            },
            "function": lead_scraper,
        },
        {
            "name": "email_finder",
            "description": "Generate likely email addresses for a person at a company using common patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "domain": {"type": "string"},
                },
                "required": ["first_name", "last_name", "domain"],
            },
            "function": email_finder,
        },
        {
            "name": "outreach_template",
            "description": "Generate cold outreach templates for email, LinkedIn, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "template_type": {"type": "string", "enum": ["cold_email", "linkedin_connect", "linkedin_inmail"], "default": "cold_email"},
                    "industry": {"type": "string", "default": "saas"},
                    "offering": {"type": "string", "default": ""},
                    "tone": {"type": "string", "enum": ["professional", "casual"], "default": "professional"},
                },
            },
            "function": outreach_template,
        },
        {
            "name": "crm_manage",
            "description": "Manage CRM pipeline: add leads, move stages, view pipeline, search leads.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "move", "view", "search"]},
                    "lead_name": {"type": "string", "default": ""},
                    "email": {"type": "string", "default": ""},
                    "company": {"type": "string", "default": ""},
                    "stage": {"type": "string", "enum": ["new", "contacted", "qualified", "proposal", "closed_won", "closed_lost"], "default": "new"},
                    "notes": {"type": "string", "default": ""},
                    "deal_value": {"type": "number", "default": 0},
                },
                "required": ["action"],
            },
            "function": crm_manage,
        },
        {
            "name": "competitive_analysis",
            "description": "Analyze a company and its competitors: tech stack, social presence, positioning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "competitors": {"type": "array", "items": {"type": "string"}, "description": "List of competitor domains"},
                },
                "required": ["domain"],
            },
            "function": competitive_analysis,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

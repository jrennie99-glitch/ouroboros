"""
Ouroboros — Marketing tools.

Email campaign builder, social media scheduler, ad copy generator,
A/B test designer, landing page copy, SEO keyword research.
"""

from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_marketing")
CAMPAIGNS_PATH = os.path.join(WORKSPACE, "campaigns.json")
SCHEDULE_PATH = os.path.join(WORKSPACE, "social_schedule.json")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


# ── Email Campaign Builder ───────────────────────────────────────────────

def email_campaign(action: str = "create", campaign_name: str = "",
                   subject: str = "", body_type: str = "promotional",
                   audience: str = "general", cta: str = "",
                   product: str = "") -> Dict[str, Any]:
    """Build email campaigns with templates, subject lines, and best practices."""
    if action == "create":
        templates = {
            "promotional": {
                "subject_lines": [
                    f"{{first_name}}, exclusive offer on {product or 'our latest'}",
                    f"Don't miss out: {product or 'Limited time deal'} inside",
                    f"Your {product or 'special'} discount expires soon",
                    f"We picked this just for you, {{first_name}}",
                ],
                "preheader": f"Save big on {product or 'our products'} — limited time only",
                "body_structure": [
                    "Hero image with product/offer",
                    "Headline: Value proposition in one line",
                    "Body: 2-3 sentences on the offer",
                    f"CTA button: '{cta or 'Shop Now'}'",
                    "Social proof / testimonial",
                    "Urgency element (deadline, limited stock)",
                    "Footer with unsubscribe link",
                ],
            },
            "newsletter": {
                "subject_lines": [
                    f"This week: {product or 'Top stories and updates'}",
                    f"{{first_name}}'s weekly digest",
                    f"What you missed + what's coming",
                ],
                "preheader": "Your weekly roundup of what matters",
                "body_structure": [
                    "Header with branding",
                    "Top story / featured article",
                    "3-5 curated content pieces",
                    "Quick tips or insights section",
                    "Community highlights",
                    "CTA: 'Read more on our blog'",
                    "Footer with preferences + unsubscribe",
                ],
            },
            "welcome": {
                "subject_lines": [
                    f"Welcome to the family, {{first_name}}!",
                    f"You're in! Here's what happens next",
                    f"{{first_name}}, let's get started",
                ],
                "preheader": "Everything you need to know to get started",
                "body_structure": [
                    "Warm welcome message",
                    "What to expect (frequency, content type)",
                    "Quick win: Immediate value for the subscriber",
                    "Key resources / getting started guide",
                    f"CTA: '{cta or 'Get Started'}'",
                    "Team photo or personal touch",
                ],
            },
            "re_engagement": {
                "subject_lines": [
                    f"We miss you, {{first_name}}",
                    f"It's been a while — here's what's new",
                    f"{{first_name}}, your account is waiting",
                    f"Come back and get {product or '20% off'}",
                ],
                "preheader": "We've got something special for you",
                "body_structure": [
                    "Acknowledge the absence (friendly tone)",
                    "Highlight what's new/improved",
                    "Exclusive re-engagement offer",
                    f"CTA: '{cta or 'Come Back'}'",
                    "Option to update preferences",
                ],
            },
        }

        template = templates.get(body_type, templates["promotional"])

        return {
            "campaign_name": campaign_name or f"{body_type}_{datetime.now().strftime('%Y%m%d')}",
            "type": body_type,
            "audience": audience,
            "subject_lines": template["subject_lines"],
            "preheader": template["preheader"],
            "body_structure": template["body_structure"],
            "best_practices": {
                "send_time": "Tuesday-Thursday, 10am-2pm recipient timezone",
                "subject_length": "30-50 characters for mobile",
                "preview_text": "40-130 characters",
                "cta_color": "Contrasting color, above the fold",
                "mobile": "60%+ opens on mobile — single column, 14px+ font",
                "personalization": "Use first name, past behavior, location",
            },
            "metrics_to_track": ["open_rate", "click_rate", "conversion_rate", "unsubscribe_rate", "bounce_rate"],
        }

    elif action == "sequence":
        return {
            "sequence_name": campaign_name,
            "emails": [
                {"day": 0, "type": "welcome", "subject": "Welcome! Here's what to expect"},
                {"day": 2, "type": "value", "subject": "Quick tip to get the most out of {{product}}"},
                {"day": 5, "type": "social_proof", "subject": "See what others are saying"},
                {"day": 7, "type": "offer", "subject": "Exclusive offer just for you"},
                {"day": 14, "type": "check_in", "subject": "How's it going, {{first_name}}?"},
                {"day": 21, "type": "advanced", "subject": "Pro tips for power users"},
                {"day": 30, "type": "survey", "subject": "Quick question (takes 30 seconds)"},
            ],
        }

    return {"error": f"Unknown action: {action}"}


# ── Social Media Scheduler ───────────────────────────────────────────────

def social_scheduler(action: str, platform: str = "all",
                     content: str = "", schedule_time: str = "",
                     hashtags: List[str] = None,
                     post_id: int = 0) -> Dict[str, Any]:
    """Plan and schedule social media posts."""
    _ensure_workspace()

    if os.path.exists(SCHEDULE_PATH):
        with open(SCHEDULE_PATH) as f:
            schedule = json.load(f)
    else:
        schedule = {"posts": []}

    if action == "create":
        if not content:
            return {"error": "content is required"}

        optimal_times = {
            "twitter": "9-11am, 1-3pm weekdays",
            "instagram": "11am-1pm, 7-9pm",
            "linkedin": "7-8am, 12pm, 5-6pm Tue-Thu",
            "tiktok": "7-9am, 12-3pm, 7-11pm",
            "facebook": "1-4pm, best on Wed-Fri",
            "youtube": "2-4pm Thu-Fri, 9-11am Sat",
        }

        char_limits = {
            "twitter": 280,
            "instagram": 2200,
            "linkedin": 3000,
            "tiktok": 2200,
            "facebook": 63206,
        }

        post = {
            "id": len(schedule["posts"]) + 1,
            "platform": platform,
            "content": content,
            "hashtags": hashtags or [],
            "scheduled_for": schedule_time or "not scheduled",
            "status": "draft",
            "created": datetime.now().isoformat(),
        }

        # Platform-specific formatting
        if platform in char_limits:
            limit = char_limits[platform]
            full_content = content
            if hashtags:
                full_content += " " + " ".join(f"#{h}" for h in hashtags)
            if len(full_content) > limit:
                post["warning"] = f"Content exceeds {platform} limit ({len(full_content)}/{limit} chars)"

        post["optimal_time"] = optimal_times.get(platform, "Varies by audience")

        schedule["posts"].append(post)
        with open(SCHEDULE_PATH, "w") as f:
            json.dump(schedule, f, indent=2)

        return {"action": "created", "post": post}

    elif action == "list":
        posts = schedule["posts"]
        if platform != "all":
            posts = [p for p in posts if p["platform"] == platform]
        return {"posts": posts, "count": len(posts)}

    elif action == "calendar":
        # Generate a weekly content calendar
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        calendar = {}
        for day in days:
            calendar[day] = {
                "twitter": {"count": 3 if day not in ("Saturday", "Sunday") else 1,
                           "types": ["thread", "engagement", "promotional"]},
                "instagram": {"count": 1, "types": ["feed post" if day in ("Tuesday", "Thursday") else "story"]},
                "linkedin": {"count": 1 if day in ("Tuesday", "Wednesday", "Thursday") else 0,
                            "types": ["thought leadership"]},
                "tiktok": {"count": 1, "types": ["trending audio + niche content"]},
            }
        return {
            "weekly_calendar": calendar,
            "tips": [
                "Batch create content on Mondays",
                "Repurpose long-form content across platforms",
                "Engage with comments within first hour of posting",
                "Track what performs best and double down",
            ],
        }

    elif action == "delete":
        schedule["posts"] = [p for p in schedule["posts"] if p["id"] != post_id]
        with open(SCHEDULE_PATH, "w") as f:
            json.dump(schedule, f, indent=2)
        return {"action": "deleted", "post_id": post_id}

    return {"error": f"Unknown action: {action}"}


# ── Ad Copy Generator ────────────────────────────────────────────────────

def ad_copy_generator(product: str, platform: str = "google",
                      audience: str = "general", tone: str = "professional",
                      usp: str = "") -> Dict[str, Any]:
    """Generate ad copy for Google Ads, Facebook/Meta, LinkedIn, Twitter."""
    usp_text = usp or product

    copies = {}

    if platform in ("google", "all"):
        copies["google_search"] = {
            "headlines": [
                f"{product} — {usp_text}"[:30],
                f"Try {product} Today"[:30],
                f"#1 Rated {product}"[:30],
                f"Save on {product} Now"[:30],
                f"Get {product} — Free Trial"[:30],
            ],
            "descriptions": [
                f"Discover why thousands trust {product}. {usp_text}. Start your free trial today."[:90],
                f"Transform your workflow with {product}. Easy setup, powerful results. Try it free."[:90],
            ],
            "specs": {"headlines": "max 30 chars each, 15 max", "descriptions": "max 90 chars, 4 max"},
        }

    if platform in ("facebook", "meta", "all"):
        copies["facebook"] = {
            "primary_text": f"Struggling with [pain point]? {product} helps you {usp_text}.\n\nJoin 10,000+ users who've already made the switch.\n\n-> Start your free trial today",
            "headline": f"Try {product} Free"[:40],
            "description": f"{usp_text}. No credit card required."[:30],
            "cta_options": ["Learn More", "Sign Up", "Get Offer", "Shop Now"],
            "specs": {"primary_text": "125 chars for mobile", "headline": "40 chars", "image": "1200x628px or 1080x1080px"},
        }

    if platform in ("linkedin", "all"):
        copies["linkedin"] = {
            "intro_text": f"Is your team still doing [manual process]?\n\n{product} automates {usp_text}, saving an average of 10 hours/week.\n\nSee why industry leaders are switching →",
            "headline": f"{product}: The Smarter Way to {usp_text}"[:70],
            "specs": {"intro": "150 chars above fold", "headline": "70 chars", "image": "1200x627px"},
        }

    if platform in ("twitter", "all"):
        copies["twitter"] = {
            "tweets": [
                f"We just launched {product}. {usp_text}.\n\nTry it free → [link]",
                f"Why {product}?\n\n• {usp_text}\n• Easy setup\n• Free to start\n\nLink in bio",
                f"\"I wish I found {product} sooner\" — actual customer feedback\n\nSee why →",
            ],
        }

    return {
        "product": product,
        "platform": platform,
        "audience": audience,
        "tone": tone,
        "copies": copies,
        "best_practices": [
            "Always A/B test headlines",
            "Use numbers and social proof",
            "Match ad copy to landing page messaging",
            "Start with the benefit, not the feature",
            "Include a clear, single CTA",
        ],
    }


# ── A/B Test Designer ────────────────────────────────────────────────────

def ab_test_designer(element: str, variants: List[str] = None,
                     metric: str = "conversion_rate",
                     traffic_per_day: int = 1000,
                     baseline_rate: float = 0.03,
                     mde: float = 0.2) -> Dict[str, Any]:
    """Design an A/B test with sample size calculation and recommendations."""
    import math

    if not variants:
        variants = ["Control (A)", "Variant (B)"]

    n_variants = len(variants)

    # Sample size calculation (simplified)
    # Using approximation: n = (Z_alpha/2 + Z_beta)^2 * 2 * p * (1-p) / delta^2
    z_alpha = 1.96  # 95% confidence
    z_beta = 0.84   # 80% power
    p = baseline_rate
    delta = baseline_rate * mde  # absolute MDE

    if delta > 0:
        sample_per_variant = math.ceil(
            ((z_alpha + z_beta) ** 2 * 2 * p * (1 - p)) / (delta ** 2)
        )
    else:
        sample_per_variant = 10000

    total_sample = sample_per_variant * n_variants
    days_needed = math.ceil(total_sample / traffic_per_day) if traffic_per_day > 0 else 0

    return {
        "test_name": f"A/B Test: {element}",
        "element_tested": element,
        "variants": variants,
        "primary_metric": metric,
        "setup": {
            "baseline_rate": f"{baseline_rate * 100:.1f}%",
            "minimum_detectable_effect": f"{mde * 100:.0f}%",
            "confidence_level": "95%",
            "statistical_power": "80%",
        },
        "sample_size": {
            "per_variant": sample_per_variant,
            "total": total_sample,
            "daily_traffic": traffic_per_day,
            "estimated_days": days_needed,
        },
        "recommendations": [
            "Run the test for at least 1 full week to account for day-of-week effects",
            "Don't peek at results early — wait for full sample size",
            "Only test one variable at a time",
            f"Need {total_sample:,} total visitors ({days_needed} days at {traffic_per_day}/day)",
            "Document hypothesis before starting",
            "Ensure equal traffic split between variants",
        ],
        "hypothesis_template": f"Changing {element} from [A] to [B] will increase {metric} by at least {mde*100:.0f}% because [reason].",
    }


# ── Landing Page Copy ────────────────────────────────────────────────────

def landing_page_copy(product: str, audience: str = "general",
                      page_type: str = "saas", usp: str = "",
                      social_proof: str = "") -> Dict[str, Any]:
    """Generate landing page copy framework."""
    sections = {
        "hero": {
            "headline_options": [
                f"The Easiest Way to {usp or 'Get Results'}",
                f"Stop Wasting Time. Start Using {product}.",
                f"{product}: Built for {audience.title() if audience != 'general' else 'Results'}",
                f"Join 10,000+ Teams Using {product}",
            ],
            "subheadline": f"A brief, clear description of what {product} does and who it's for.",
            "cta": "Start Free Trial",
            "secondary_cta": "Watch Demo",
        },
        "problem": {
            "heading": "The Old Way Doesn't Work",
            "points": [
                "[Pain point 1 your audience faces]",
                "[Pain point 2 — wasted time/money]",
                "[Pain point 3 — frustration/complexity]",
            ],
        },
        "solution": {
            "heading": f"Meet {product}",
            "description": f"{product} solves [problem] by {usp or 'providing a better way'}.",
            "features": [
                {"title": "Feature 1", "description": "How it solves pain point 1", "icon": "lightning"},
                {"title": "Feature 2", "description": "How it saves time/money", "icon": "clock"},
                {"title": "Feature 3", "description": "How it simplifies the process", "icon": "check"},
            ],
        },
        "social_proof": {
            "heading": "Trusted by Industry Leaders",
            "elements": [
                "Customer logos bar",
                f"Testimonial: \"{social_proof or '[Customer quote about results]'}\"",
                "Key metric: '10,000+ users' or '$1M+ saved'",
                "Star rating: 4.9/5 from 500+ reviews",
            ],
        },
        "pricing_cta": {
            "heading": f"Start Using {product} Today",
            "cta": "Start Free Trial — No Credit Card Required",
            "guarantee": "30-day money-back guarantee",
            "urgency": "Limited time: Get 20% off annual plans",
        },
        "faq": {
            "heading": "Frequently Asked Questions",
            "questions": [
                {"q": f"How does {product} work?", "a": "[Brief explanation]"},
                {"q": "Is there a free trial?", "a": "Yes, 14 days free. No credit card required."},
                {"q": "Can I cancel anytime?", "a": "Absolutely. Cancel with one click, no questions asked."},
                {"q": f"What makes {product} different?", "a": f"[{usp or 'Unique differentiator'}]"},
            ],
        },
    }

    return {
        "product": product,
        "audience": audience,
        "page_type": page_type,
        "sections": sections,
        "conversion_tips": [
            "Single clear CTA — avoid choice paralysis",
            "Above-the-fold CTA gets 2-3x more clicks",
            "Social proof near CTA increases conversions 15-20%",
            "Remove navigation to reduce bounce",
            "Mobile-first design (60%+ traffic is mobile)",
            "Page load under 3 seconds or lose 40% of visitors",
        ],
    }


# ── SEO Keyword Research ─────────────────────────────────────────────────

def seo_keywords(seed_keyword: str, intent: str = "all") -> Dict[str, Any]:
    """Generate keyword research data from a seed keyword."""
    # Generate keyword variations
    modifiers = {
        "informational": [
            f"what is {seed_keyword}", f"how to {seed_keyword}",
            f"{seed_keyword} guide", f"{seed_keyword} tutorial",
            f"{seed_keyword} explained", f"best {seed_keyword} practices",
            f"{seed_keyword} tips", f"{seed_keyword} examples",
            f"learn {seed_keyword}", f"{seed_keyword} for beginners",
        ],
        "commercial": [
            f"best {seed_keyword}", f"top {seed_keyword}",
            f"{seed_keyword} comparison", f"{seed_keyword} vs",
            f"{seed_keyword} review", f"{seed_keyword} alternatives",
            f"cheapest {seed_keyword}", f"{seed_keyword} pricing",
            f"{seed_keyword} features", f"{seed_keyword} pros and cons",
        ],
        "transactional": [
            f"buy {seed_keyword}", f"{seed_keyword} discount",
            f"{seed_keyword} coupon", f"{seed_keyword} free trial",
            f"{seed_keyword} pricing plans", f"get {seed_keyword}",
            f"{seed_keyword} sign up", f"{seed_keyword} download",
        ],
        "navigational": [
            f"{seed_keyword} login", f"{seed_keyword} official site",
            f"{seed_keyword} support", f"{seed_keyword} documentation",
        ],
    }

    if intent == "all":
        keywords = {}
        for intent_type, kws in modifiers.items():
            keywords[intent_type] = kws
    else:
        keywords = {intent: modifiers.get(intent, modifiers["informational"])}

    # Long-tail suggestions
    long_tail = [
        f"how to use {seed_keyword} for [specific use case]",
        f"{seed_keyword} for small business",
        f"{seed_keyword} for enterprise",
        f"is {seed_keyword} worth it in {datetime.now().year}",
        f"{seed_keyword} step by step guide",
    ]

    # Content strategy
    content_strategy = {
        "pillar_page": f"The Complete Guide to {seed_keyword.title()}",
        "cluster_topics": [
            f"{seed_keyword} basics",
            f"Advanced {seed_keyword} strategies",
            f"{seed_keyword} tools and resources",
            f"{seed_keyword} case studies",
            f"Common {seed_keyword} mistakes",
        ],
        "content_types": [
            {"type": "Blog post", "keyword": f"how to {seed_keyword}", "intent": "informational"},
            {"type": "Comparison", "keyword": f"best {seed_keyword}", "intent": "commercial"},
            {"type": "Landing page", "keyword": f"buy {seed_keyword}", "intent": "transactional"},
            {"type": "FAQ page", "keyword": f"what is {seed_keyword}", "intent": "informational"},
        ],
    }

    return {
        "seed_keyword": seed_keyword,
        "keywords_by_intent": keywords,
        "long_tail_suggestions": long_tail,
        "content_strategy": content_strategy,
        "on_page_seo_checklist": [
            f"Include '{seed_keyword}' in title tag",
            f"Include '{seed_keyword}' in H1",
            f"Include '{seed_keyword}' in first 100 words",
            f"Use '{seed_keyword}' variations in H2/H3 tags",
            "Optimize meta description with keyword",
            "Add alt text with keyword to images",
            "Internal link to related content",
            "Aim for 1500+ words for informational content",
        ],
    }


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "email_campaign",
            "description": "Build email campaigns with templates, subject lines, and drip sequences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "sequence"], "default": "create"},
                    "campaign_name": {"type": "string", "default": ""},
                    "subject": {"type": "string", "default": ""},
                    "body_type": {"type": "string", "enum": ["promotional", "newsletter", "welcome", "re_engagement"], "default": "promotional"},
                    "audience": {"type": "string", "default": "general"},
                    "cta": {"type": "string", "default": ""},
                    "product": {"type": "string", "default": ""},
                },
            },
            "function": email_campaign,
        },
        {
            "name": "social_scheduler",
            "description": "Plan and schedule social media posts with platform-specific formatting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "list", "calendar", "delete"]},
                    "platform": {"type": "string", "enum": ["twitter", "instagram", "linkedin", "tiktok", "facebook", "all"], "default": "all"},
                    "content": {"type": "string", "default": ""},
                    "schedule_time": {"type": "string", "default": ""},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "post_id": {"type": "integer", "default": 0},
                },
                "required": ["action"],
            },
            "function": social_scheduler,
        },
        {
            "name": "ad_copy_generator",
            "description": "Generate ad copy for Google, Facebook/Meta, LinkedIn, Twitter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string"},
                    "platform": {"type": "string", "enum": ["google", "facebook", "meta", "linkedin", "twitter", "all"], "default": "all"},
                    "audience": {"type": "string", "default": "general"},
                    "tone": {"type": "string", "default": "professional"},
                    "usp": {"type": "string", "default": "", "description": "Unique selling proposition"},
                },
                "required": ["product"],
            },
            "function": ad_copy_generator,
        },
        {
            "name": "ab_test_designer",
            "description": "Design A/B tests with sample size calculation, duration estimation, and best practices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "element": {"type": "string", "description": "What to test (headline, CTA button, pricing, etc)"},
                    "variants": {"type": "array", "items": {"type": "string"}},
                    "metric": {"type": "string", "default": "conversion_rate"},
                    "traffic_per_day": {"type": "integer", "default": 1000},
                    "baseline_rate": {"type": "number", "default": 0.03, "description": "Current conversion rate (0-1)"},
                    "mde": {"type": "number", "default": 0.2, "description": "Minimum detectable effect (0.2 = 20% relative lift)"},
                },
                "required": ["element"],
            },
            "function": ab_test_designer,
        },
        {
            "name": "landing_page_copy",
            "description": "Generate landing page copy framework with hero, features, social proof, CTA, FAQ sections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string"},
                    "audience": {"type": "string", "default": "general"},
                    "page_type": {"type": "string", "default": "saas"},
                    "usp": {"type": "string", "default": ""},
                    "social_proof": {"type": "string", "default": ""},
                },
                "required": ["product"],
            },
            "function": landing_page_copy,
        },
        {
            "name": "seo_keywords",
            "description": "SEO keyword research: generate variations by intent, long-tail suggestions, content strategy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seed_keyword": {"type": "string"},
                    "intent": {"type": "string", "enum": ["all", "informational", "commercial", "transactional", "navigational"], "default": "all"},
                },
                "required": ["seed_keyword"],
            },
            "function": seo_keywords,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

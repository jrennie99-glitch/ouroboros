"""
Ouroboros — Content Creation, Video, Music, Lead Generation tools.

Supreme content engine for all media types.
"""

from __future__ import annotations
import logging

from ouroboros.tools._adapter import adapt_tools
import json
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_content")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)
    os.makedirs(f"{WORKSPACE}/scripts", exist_ok=True)
    os.makedirs(f"{WORKSPACE}/music", exist_ok=True)
    os.makedirs(f"{WORKSPACE}/leads", exist_ok=True)
    os.makedirs(f"{WORKSPACE}/content", exist_ok=True)


def create_content(content_type: str, topic: str, style: str = "professional",
                   length: str = "medium", audience: str = "general") -> Dict[str, Any]:
    """Generate content creation brief and structure."""
    _ensure_workspace()

    brief = {
        "type": content_type,
        "topic": topic,
        "style": style,
        "length": length,
        "audience": audience,
        "created": datetime.now().isoformat(),
        "structure": [],
    }

    if content_type == "blog_post":
        brief["structure"] = [
            "Hook / Opening (grab attention in first 2 sentences)",
            "Problem Statement (what pain point does this solve)",
            "Main Content (3-5 key points with examples)",
            "Actionable Takeaways (what reader should do next)",
            "Call to Action",
        ]
    elif content_type == "social_media":
        brief["structure"] = [
            "Platform-specific format",
            "Hook (first line must stop scrolling)",
            "Value proposition",
            "Engagement prompt (question or CTA)",
            "Hashtags / tags",
        ]
    elif content_type == "marketing_copy":
        brief["structure"] = [
            "Headline (benefit-driven)",
            "Subheadline (clarify the offer)",
            "Pain points (3 max)",
            "Solution presentation",
            "Social proof placeholder",
            "CTA (clear, specific, urgent)",
        ]
    elif content_type == "email_sequence":
        brief["structure"] = [
            "Email 1: Welcome / Introduction",
            "Email 2: Value / Education",
            "Email 3: Social Proof / Case Study",
            "Email 4: Objection Handling",
            "Email 5: Offer / CTA",
        ]

    path = f"{WORKSPACE}/content/{content_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(path, "w") as f:
        json.dump(brief, f, indent=2)

    brief["saved_to"] = path
    return brief


def create_video_script(title: str, duration_minutes: int = 5,
                        style: str = "educational", platform: str = "youtube") -> Dict[str, Any]:
    """Generate a video production script with scenes, dialogue, and directions."""
    _ensure_workspace()

    script = {
        "title": title,
        "duration": f"{duration_minutes} minutes",
        "style": style,
        "platform": platform,
        "created": datetime.now().isoformat(),
        "scenes": [],
    }

    # Generate scene structure based on duration
    num_scenes = max(3, duration_minutes * 2)
    scene_duration = duration_minutes * 60 / num_scenes

    script["scenes"] = [
        {"scene": 1, "duration": f"{int(scene_duration)}s", "type": "hook",
         "direction": "Open with a compelling question or statement. Show energy.",
         "notes": "First 5 seconds determine if viewer stays"},
        {"scene": 2, "duration": f"{int(scene_duration)}s", "type": "intro",
         "direction": "Brief intro. Establish credibility. Preview what's coming.",
         "notes": "Keep under 30 seconds"},
    ]

    for i in range(3, num_scenes):
        script["scenes"].append({
            "scene": i,
            "duration": f"{int(scene_duration)}s",
            "type": "content",
            "direction": f"Main point {i-2}. Use visuals/B-roll. Keep energy up.",
            "notes": "Include specific examples",
        })

    script["scenes"].append({
        "scene": num_scenes,
        "duration": f"{int(scene_duration)}s",
        "type": "cta",
        "direction": "Recap key points. Clear call to action. End strong.",
        "notes": "Tell viewer exactly what to do next",
    })

    path = f"{WORKSPACE}/scripts/{title.replace(' ', '_')[:30]}_{datetime.now().strftime('%Y%m%d')}.json"
    with open(path, "w") as f:
        json.dump(script, f, indent=2)

    script["saved_to"] = path
    return script


def create_music_brief(genre: str, mood: str, duration_seconds: int = 180,
                       instruments: str = "auto", purpose: str = "background") -> Dict[str, Any]:
    """Generate a music production brief."""
    _ensure_workspace()

    brief = {
        "genre": genre,
        "mood": mood,
        "duration": f"{duration_seconds}s ({duration_seconds//60}:{duration_seconds%60:02d})",
        "instruments": instruments,
        "purpose": purpose,
        "created": datetime.now().isoformat(),
        "structure": {
            "intro": f"{int(duration_seconds * 0.1)}s - Build atmosphere",
            "verse_1": f"{int(duration_seconds * 0.2)}s - Establish theme",
            "chorus": f"{int(duration_seconds * 0.15)}s - Main hook / energy peak",
            "verse_2": f"{int(duration_seconds * 0.2)}s - Develop theme",
            "bridge": f"{int(duration_seconds * 0.15)}s - Contrast / tension",
            "final_chorus": f"{int(duration_seconds * 0.1)}s - Resolution",
            "outro": f"{int(duration_seconds * 0.1)}s - Fade / conclude",
        },
        "production_notes": [
            f"Genre: {genre} - follow genre conventions for rhythm and harmony",
            f"Mood: {mood} - use appropriate key, tempo, and dynamics",
            f"Purpose: {purpose} - mix accordingly (e.g., background = less dynamic range)",
        ],
    }

    path = f"{WORKSPACE}/music/{genre}_{mood}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(path, "w") as f:
        json.dump(brief, f, indent=2)

    brief["saved_to"] = path
    return brief


def generate_leads(industry: str, criteria: str = "", count: int = 10,
                   method: str = "research") -> Dict[str, Any]:
    """Generate lead generation strategy and prospect research."""
    _ensure_workspace()

    strategy = {
        "industry": industry,
        "criteria": criteria,
        "target_count": count,
        "method": method,
        "created": datetime.now().isoformat(),
        "channels": [
            {"channel": "LinkedIn", "approach": "Connect + value-first messaging", "priority": "high"},
            {"channel": "Email Outreach", "approach": "Cold email with personalization", "priority": "high"},
            {"channel": "Content Marketing", "approach": "SEO + social content to attract inbound", "priority": "medium"},
            {"channel": "Referrals", "approach": "Ask existing contacts for warm intros", "priority": "high"},
            {"channel": "Communities", "approach": "Engage in relevant forums/groups", "priority": "medium"},
        ],
        "outreach_template": {
            "subject": f"Quick question about [specific thing in {industry}]",
            "opening": "I noticed [specific observation about their business]",
            "value_prop": "We help [industry] companies [specific result]",
            "social_proof": "[Specific result for similar company]",
            "cta": "Would a 15-min call this week make sense?",
        },
        "qualification_criteria": [
            "Company size matches target",
            "Decision maker identified",
            "Budget confirmed or likely",
            "Timeline within 3 months",
            "Clear pain point identified",
        ],
    }

    path = f"{WORKSPACE}/leads/{industry.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(path, "w") as f:
        json.dump(strategy, f, indent=2)

    strategy["saved_to"] = path
    return strategy


def _raw_tools() -> list:
    return [
        {
            "name": "create_content",
            "description": "Generate content creation brief. Types: blog_post, social_media, marketing_copy, email_sequence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content_type": {"type": "string", "enum": ["blog_post", "social_media", "marketing_copy", "email_sequence"]},
                    "topic": {"type": "string"},
                    "style": {"type": "string", "default": "professional"},
                    "length": {"type": "string", "default": "medium"},
                    "audience": {"type": "string", "default": "general"},
                },
                "required": ["content_type", "topic"],
            },
            "function": create_content,
        },
        {
            "name": "create_video_script",
            "description": "Generate a video production script with scenes, timing, and direction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "duration_minutes": {"type": "integer", "default": 5},
                    "style": {"type": "string", "default": "educational"},
                    "platform": {"type": "string", "default": "youtube"},
                },
                "required": ["title"],
            },
            "function": create_video_script,
        },
        {
            "name": "create_music_brief",
            "description": "Generate a music production brief with structure and notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "genre": {"type": "string"},
                    "mood": {"type": "string"},
                    "duration_seconds": {"type": "integer", "default": 180},
                    "instruments": {"type": "string", "default": "auto"},
                    "purpose": {"type": "string", "default": "background"},
                },
                "required": ["genre", "mood"],
            },
            "function": create_music_brief,
        },
        {
            "name": "generate_leads",
            "description": "Generate lead generation strategy with outreach templates and qualification criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {"type": "string"},
                    "criteria": {"type": "string", "default": ""},
                    "count": {"type": "integer", "default": 10},
                    "method": {"type": "string", "default": "research"},
                },
                "required": ["industry"],
            },
            "function": generate_leads,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

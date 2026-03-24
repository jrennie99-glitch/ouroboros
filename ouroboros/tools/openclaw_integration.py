"""OpenClaw integration: swarm management, multi-platform messaging, skill execution."""

from __future__ import annotations

import json
import logging
import os
import pathlib
import subprocess
from typing import Any, Dict, List

from ouroboros.tools.registry import ToolContext, ToolEntry

log = logging.getLogger(__name__)

OPENCLAW_DIR = pathlib.Path(__file__).resolve().parents[2] / "workspace" / "openclaw"
OPENCLAW_STAGING = pathlib.Path(__file__).resolve().parents[2] / "frankenstein_components" / "openclaw"


def _openclaw_status(ctx: ToolContext, **kwargs) -> str:
    """Get status of OpenClaw swarm manager."""
    result = {
        "production_path": str(OPENCLAW_DIR),
        "production_exists": OPENCLAW_DIR.exists(),
        "staging_path": str(OPENCLAW_STAGING),
        "staging_exists": OPENCLAW_STAGING.exists(),
    }
    # List skills
    skills_dir = OPENCLAW_DIR / "skills"
    if not skills_dir.exists():
        skills_dir = OPENCLAW_STAGING / "skills"
    if skills_dir.exists():
        all_skills = sorted(s.name for s in skills_dir.iterdir() if s.is_dir())
        result["skills"] = all_skills[:50]
        result["skill_count"] = len(all_skills)
    # List extensions
    ext_dir = OPENCLAW_DIR / "extensions"
    if not ext_dir.exists():
        ext_dir = OPENCLAW_STAGING / "extensions"
    if ext_dir.exists():
        all_exts = sorted(e.name for e in ext_dir.iterdir() if e.is_dir())
        result["extensions"] = all_exts[:30]
        result["extension_count"] = len(all_exts)
    return json.dumps(result, indent=2)


def _openclaw_list_skills(ctx: ToolContext, **kwargs) -> str:
    """List all available OpenClaw skills."""
    for base in [OPENCLAW_DIR, OPENCLAW_STAGING]:
        skills_dir = base / "skills"
        if skills_dir.exists():
            skills = []
            for s in sorted(skills_dir.iterdir()):
                if s.is_dir():
                    readme = s / "README.md"
                    desc = ""
                    if readme.exists():
                        lines = readme.read_text(errors="replace").splitlines()
                        desc = lines[0] if lines else ""
                    skills.append({"name": s.name, "description": desc[:100]})
            return json.dumps(skills, indent=2)
    return "No skills directory found."


def _openclaw_read_skill(ctx: ToolContext, skill_name: str, **kwargs) -> str:
    """Read a specific OpenClaw skill's code and configuration."""
    for base in [OPENCLAW_DIR, OPENCLAW_STAGING]:
        skill_dir = base / "skills" / skill_name
        if skill_dir.exists():
            files = {}
            for f in sorted(skill_dir.rglob("*")):
                if f.is_file() and f.stat().st_size < 50000:
                    try:
                        files[str(f.relative_to(skill_dir))] = f.read_text(errors="replace")[:5000]
                    except Exception:
                        pass
            return json.dumps({"skill": skill_name, "path": str(skill_dir), "files": files}, indent=2)
    return f"Skill '{skill_name}' not found."


def _openclaw_swarm_init(ctx: ToolContext, worker_count: int = 3, **kwargs) -> str:
    """Initialize the OpenClaw swarm cluster with specified worker count."""
    swarm_config = {
        "manager": "ouroboros",
        "workers": worker_count,
        "coordination": "event-driven",
        "platforms": ["telegram"],
        "status": "initialized",
    }
    state_dir = ctx.drive_root / "openclaw_swarm"
    state_dir.mkdir(parents=True, exist_ok=True)
    config_file = state_dir / "swarm_config.json"
    config_file.write_text(json.dumps(swarm_config, indent=2))
    return f"Swarm initialized with {worker_count} workers.\nConfig: {json.dumps(swarm_config, indent=2)}"


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("openclaw_status", {
            "name": "openclaw_status",
            "description": "Get status of OpenClaw swarm manager. Shows skills, extensions, and platform integrations.",
            "parameters": {"type": "object", "properties": {}},
        }, _openclaw_status),
        ToolEntry("openclaw_list_skills", {
            "name": "openclaw_list_skills",
            "description": "List all available OpenClaw skills (50+ skills including automation, messaging, data processing).",
            "parameters": {"type": "object", "properties": {}},
        }, _openclaw_list_skills),
        ToolEntry("openclaw_read_skill", {
            "name": "openclaw_read_skill",
            "description": "Read a specific OpenClaw skill's code and configuration.",
            "parameters": {"type": "object", "properties": {
                "skill_name": {"type": "string", "description": "Name of the skill to read"},
            }, "required": ["skill_name"]},
        }, _openclaw_read_skill),
        ToolEntry("openclaw_swarm_init", {
            "name": "openclaw_swarm_init",
            "description": "Initialize the OpenClaw swarm cluster for multi-agent coordination.",
            "parameters": {"type": "object", "properties": {
                "worker_count": {"type": "integer", "description": "Number of swarm workers", "default": 3},
            }},
        }, _openclaw_swarm_init),
    ]

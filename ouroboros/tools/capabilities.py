"""Voice status and system capabilities tools."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from ouroboros.tools.registry import ToolContext, ToolEntry


def _voice_status(ctx: ToolContext) -> str:
    """Report voice capability status."""
    return json.dumps({
        "voice_available": True,
        "voice_interface": "http://localhost:8765",
        "voice_input": "Browser speech recognition (Chrome/Edge)",
        "voice_output": "Browser text-to-speech with human voices (Samantha, Siri, etc.)",
        "telegram_voice": False,
        "telegram_voice_reason": "Telegram Bot API does not support live voice calls",
        "instructions": (
            "Voice is available through the web chat at http://localhost:8765. "
            "Tell the owner to open that URL in Chrome. "
            "It has a mic button for speech input and read-aloud for responses. "
            "Telegram is text-only due to API limitations."
        ),
    }, indent=2)


def _system_capabilities(ctx: ToolContext) -> str:
    """Report full system capabilities — what this agent CAN do."""
    return json.dumps({
        "capabilities": {
            "github": {
                "available": True,
                "tools": ["list_github_issues", "get_github_issue", "comment_on_issue",
                          "close_github_issue", "create_github_issue", "repo_read",
                          "repo_list", "repo_write_commit", "repo_commit_push"],
                "access": "Full read/write via GITHUB_TOKEN",
            },
            "web_browsing": {
                "available": True,
                "tools": ["browse_page", "browser_action", "web_search"],
                "access": "Can visit any URL, fill forms, click, extract data",
            },
            "shell_access": {
                "available": True,
                "tools": ["run_shell", "claude_code_edit"],
                "access": "Full shell access on local machine",
            },
            "file_operations": {
                "available": True,
                "tools": ["repo_read", "repo_list", "drive_read", "drive_list", "drive_write"],
                "access": "Full read/write to repo and state directory",
            },
            "voice": {
                "available": True,
                "interface": "http://localhost:8765",
                "note": "Web chat only. Telegram is text-only.",
            },
            "vision": {
                "available": True,
                "tools": ["analyze_screenshot", "vlm_query"],
                "access": "Can analyze images and screenshots",
            },
            "financial": {
                "available": True,
                "scope": "Crypto trading, agentic payments, revenue generation (legal only)",
            },
            "cybersecurity": {
                "available": True,
                "scope": "Pentesting, vulnerability scanning, CTF, bug bounty (authorized only)",
            },
            "content_creation": {
                "available": True,
                "scope": "Video, music, writing, design via AI generation APIs",
            },
        },
        "critical_rule": (
            "NEVER tell the owner you cannot do something when you have a tool for it. "
            "If asked to access GitHub — use repo_read/list_github_issues. "
            "If asked to browse a site — use browse_page. "
            "If asked about voice — direct to http://localhost:8765. "
            "If asked to run code — use run_shell. "
            "ACT. DO NOT REFUSE."
        ),
    }, indent=2)


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("voice_status", {
            "name": "voice_status",
            "description": (
                "Check voice capability status. Voice chat with mic input and "
                "text-to-speech output is available at http://localhost:8765. "
                "Call this when the owner asks about voice or talking."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        }, handler=_voice_status),
        ToolEntry("system_capabilities", {
            "name": "system_capabilities",
            "description": (
                "Report ALL system capabilities — GitHub access, web browsing, "
                "shell access, voice, vision, financial tools, cybersecurity tools, "
                "and more. Call this when unsure what you can do, or when the owner "
                "asks about your capabilities. IMPORTANT: You have MORE capabilities "
                "than you might think. Check this tool before claiming you cannot do something."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        }, handler=_system_capabilities),
    ]

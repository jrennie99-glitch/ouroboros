"""Paperclip integration: agent creation, spawning, and management."""

from __future__ import annotations

import json
import logging
import os
import pathlib
import subprocess
from typing import Any, Dict, List

from ouroboros.tools.registry import ToolContext, ToolEntry

log = logging.getLogger(__name__)

PAPERCLIP_DIR = pathlib.Path(__file__).resolve().parents[2] / "workspace" / "paperclip"


def _paperclip_status(ctx: ToolContext, **kwargs) -> str:
    """Get status of the Paperclip agent orchestration framework."""
    if not PAPERCLIP_DIR.exists():
        return "ERROR: Paperclip not found at " + str(PAPERCLIP_DIR)
    # List packages and agents
    result = {"path": str(PAPERCLIP_DIR), "exists": True, "packages": []}
    packages_dir = PAPERCLIP_DIR / "packages"
    if packages_dir.exists():
        result["packages"] = sorted(p.name for p in packages_dir.iterdir() if p.is_dir())
    # Check if node_modules exist
    result["dependencies_installed"] = (PAPERCLIP_DIR / "node_modules").exists()
    return json.dumps(result, indent=2)


def _paperclip_create_agent(ctx: ToolContext, agent_name: str, agent_role: str = "worker",
                             agent_prompt: str = "", **kwargs) -> str:
    """Create a new agent definition in the Paperclip framework."""
    agents_dir = PAPERCLIP_DIR / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    agent_config = {
        "name": agent_name,
        "role": agent_role,
        "prompt": agent_prompt or f"You are {agent_name}, a {agent_role} agent in the Ouroboros swarm.",
        "model": os.environ.get("OUROBOROS_MODEL", "qwen3.5:9b"),
        "tools": ["run_shell", "repo_read", "repo_write_commit", "web_search"],
        "autonomous": True,
        "created_by": "ouroboros",
    }

    agent_file = agents_dir / f"{agent_name}.json"
    try:
        agent_file.write_text(json.dumps(agent_config, indent=2))
    except Exception as e:
        return f"ERROR writing agent config: {e}"
    return f"Agent '{agent_name}' created at {agent_file}\nConfig: {json.dumps(agent_config, indent=2)}"


def _paperclip_list_agents(ctx: ToolContext, **kwargs) -> str:
    """List all agents in the Paperclip framework."""
    agents_dir = PAPERCLIP_DIR / "agents"
    if not agents_dir.exists():
        return "No agents directory found. Create agents first."
    agents = []
    for f in sorted(agents_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            agents.append({"name": data.get("name", f.stem), "role": data.get("role", "unknown"), "file": str(f)})
        except Exception:
            agents.append({"name": f.stem, "role": "error", "file": str(f)})
    return json.dumps(agents, indent=2) if agents else "No agents found."


def _paperclip_spawn_agent(ctx: ToolContext, agent_name: str, task: str = "", **kwargs) -> str:
    """Spawn an agent to execute a task by enqueuing it in the real supervisor queue."""
    agents_dir = PAPERCLIP_DIR / "agents"
    agent_file = agents_dir / f"{agent_name}.json"
    if not agent_file.exists():
        return f"ERROR: Agent '{agent_name}' not found. Create it first with paperclip_create_agent."

    config = json.loads(agent_file.read_text())
    agent_prompt = config.get("prompt", "")
    full_text = f"[Agent: {agent_name} | Role: {config.get('role', 'worker')}]\n{agent_prompt}"
    if task:
        full_text += f"\n\nTask: {task}"

    # Enqueue as a real task in the supervisor queue
    try:
        from supervisor.queue import enqueue_task, persist_queue_snapshot
        from supervisor.state import load_state
        import uuid

        st = load_state()
        chat_id = int(st.get("owner_chat_id") or ctx.current_chat_id or 0)
        if not chat_id:
            return "ERROR: No chat_id. Send a message to the bot first."

        task_id = f"agent_{agent_name}_{uuid.uuid4().hex[:6]}"
        enqueue_task({
            "id": task_id,
            "type": "task",
            "chat_id": chat_id,
            "text": full_text,
            "_spawned_by": "paperclip",
            "_agent_name": agent_name,
            "_agent_role": config.get("role", "worker"),
        })
        persist_queue_snapshot(reason="paperclip_spawn")
        return json.dumps({
            "status": "spawned",
            "task_id": task_id,
            "agent": agent_name,
            "role": config.get("role", "worker"),
            "task": task or "default",
            "message": f"Agent '{agent_name}' spawned as task {task_id}. It will be picked up by the next idle worker.",
        }, indent=2)
    except Exception as e:
        return f"ERROR spawning agent: {e}"


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("paperclip_status", {
            "name": "paperclip_status",
            "description": "Get status of the Paperclip agent orchestration framework. Shows packages, agents, and dependencies.",
            "parameters": {"type": "object", "properties": {}},
        }, _paperclip_status),
        ToolEntry("paperclip_create_agent", {
            "name": "paperclip_create_agent",
            "description": "Create a new agent in the Paperclip framework. Each agent is a top-tier copy with full capabilities.",
            "parameters": {"type": "object", "properties": {
                "agent_name": {"type": "string", "description": "Name for the new agent"},
                "agent_role": {"type": "string", "description": "Role: ceo, cto, cfo, coo, worker, analyst, etc."},
                "agent_prompt": {"type": "string", "description": "Custom system prompt for the agent"},
            }, "required": ["agent_name"]},
        }, _paperclip_create_agent),
        ToolEntry("paperclip_list_agents", {
            "name": "paperclip_list_agents",
            "description": "List all agents created in the Paperclip framework.",
            "parameters": {"type": "object", "properties": {}},
        }, _paperclip_list_agents),
        ToolEntry("paperclip_spawn_agent", {
            "name": "paperclip_spawn_agent",
            "description": "Spawn an agent to execute a specific task autonomously.",
            "parameters": {"type": "object", "properties": {
                "agent_name": {"type": "string", "description": "Name of the agent to spawn"},
                "task": {"type": "string", "description": "Task for the agent to execute"},
            }, "required": ["agent_name"]},
        }, _paperclip_spawn_agent),
    ]

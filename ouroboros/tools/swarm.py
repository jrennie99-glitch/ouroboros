"""Swarm coordinator: dispatch parallel tasks, collect results, inter-agent messaging.

This is the core swarm intelligence tool that lets Ouroboros orchestrate
multiple workers as a team. Each worker runs the full Ouroboros agent with
all tools available.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from ouroboros.tools.registry import ToolContext, ToolEntry

log = logging.getLogger(__name__)


def _swarm_status(ctx: ToolContext, **kwargs) -> str:
    """Get status of all swarm workers, queues, and running tasks."""
    try:
        from supervisor.workers import WORKERS, RUNNING
        from supervisor.queue import PENDING

        workers_info = []
        for wid, w in sorted(WORKERS.items()):
            workers_info.append({
                "id": wid,
                "alive": w.proc.is_alive() if w.proc else False,
                "busy_task": w.busy_task_id,
                "status": "busy" if w.busy_task_id else "idle",
            })

        running_info = []
        now = time.time()
        for task_id, meta in RUNNING.items():
            task = meta.get("task", {}) if isinstance(meta, dict) else {}
            started = float(meta.get("started_at", 0)) if isinstance(meta, dict) else 0
            running_info.append({
                "task_id": task_id,
                "type": task.get("type", "unknown"),
                "worker_id": meta.get("worker_id"),
                "runtime_sec": round(now - started, 1) if started > 0 else 0,
                "text_preview": str(task.get("text", ""))[:100],
            })

        pending_info = []
        for t in PENDING[:10]:
            pending_info.append({
                "task_id": t.get("id"),
                "type": t.get("type"),
                "text_preview": str(t.get("text", ""))[:100],
            })

        result = {
            "swarm_active": True,
            "total_workers": len(WORKERS),
            "idle_workers": sum(1 for w in workers_info if w["status"] == "idle"),
            "busy_workers": sum(1 for w in workers_info if w["status"] == "busy"),
            "pending_tasks": len(PENDING),
            "running_tasks": len(RUNNING),
            "workers": workers_info,
            "running": running_info,
            "pending": pending_info,
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"swarm_active": False, "error": str(e)})


def _swarm_dispatch(ctx: ToolContext, subtasks: str, **kwargs) -> str:
    """Dispatch multiple subtasks to swarm workers in parallel.

    subtasks: JSON array of objects with 'description' and optional 'type' fields.
    Example: [{"description": "Search for Python web frameworks"}, {"description": "Review auth code"}]
    """
    try:
        from supervisor.queue import enqueue_task, persist_queue_snapshot
        from supervisor.state import load_state
        from supervisor import messaging

        st = load_state()
        chat_id = int(st.get("owner_chat_id") or ctx.current_chat_id or 0)
        if not chat_id:
            return "ERROR: No chat_id available. Send a message first."

        # Parse subtasks
        if isinstance(subtasks, str):
            try:
                tasks_list = json.loads(subtasks)
            except json.JSONDecodeError:
                # Treat as single task description
                tasks_list = [{"description": subtasks}]
        elif isinstance(subtasks, list):
            tasks_list = subtasks
        else:
            return "ERROR: subtasks must be a JSON array or string"

        if not tasks_list:
            return "ERROR: No subtasks provided"

        # Create a batch ID to group these tasks
        batch_id = uuid.uuid4().hex[:8]
        dispatched = []

        for i, sub in enumerate(tasks_list):
            if isinstance(sub, str):
                sub = {"description": sub}

            task_id = f"swarm_{batch_id}_{i}"
            description = sub.get("description", str(sub))
            task_type = sub.get("type", "task")

            task = {
                "id": task_id,
                "type": task_type,
                "chat_id": chat_id,
                "text": description,
                "_batch_id": batch_id,
                "_batch_index": i,
                "_batch_total": len(tasks_list),
                "_is_swarm_task": True,
            }

            enqueue_task(task)
            dispatched.append({"task_id": task_id, "description": description[:100]})

        persist_queue_snapshot(reason="swarm_dispatch")

        # Store batch info for collection
        messaging.store_task_result(f"batch_{batch_id}", json.dumps({
            "batch_id": batch_id,
            "total_tasks": len(tasks_list),
            "dispatched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "task_ids": [d["task_id"] for d in dispatched],
            "status": "dispatched",
        }))

        return json.dumps({
            "batch_id": batch_id,
            "dispatched_count": len(dispatched),
            "tasks": dispatched,
            "status": "Tasks dispatched to swarm workers. Use swarm_collect to get results.",
        }, indent=2)

    except Exception as e:
        log.error("swarm_dispatch failed", exc_info=True)
        return f"ERROR: {e}"


def _swarm_collect(ctx: ToolContext, batch_id: str = "", **kwargs) -> str:
    """Collect results from completed swarm tasks.

    If batch_id is provided, collects results for that batch only.
    Otherwise returns all recent results.
    """
    try:
        from supervisor import messaging
        from supervisor.workers import RUNNING
        from supervisor.queue import PENDING

        if batch_id:
            # Get batch info
            batch_info = messaging.get_task_result(f"batch_{batch_id}")
            if not batch_info:
                return f"Batch '{batch_id}' not found."

            batch_data = json.loads(batch_info.get("result", "{}"))
            task_ids = batch_data.get("task_ids", [])

            results = []
            pending_ids = []
            running_ids = []

            for tid in task_ids:
                result = messaging.get_task_result(tid)
                if result:
                    results.append(result)
                elif tid in RUNNING:
                    running_ids.append(tid)
                elif any(t.get("id") == tid for t in PENDING):
                    pending_ids.append(tid)
                else:
                    results.append({"task_id": tid, "status": "unknown"})

            return json.dumps({
                "batch_id": batch_id,
                "total": len(task_ids),
                "completed": len(results),
                "running": running_ids,
                "pending": pending_ids,
                "results": results,
            }, indent=2)
        else:
            # Return all recent results
            all_results = messaging.get_all_results(limit=20)
            return json.dumps({
                "total_results": len(all_results),
                "results": all_results,
            }, indent=2)

    except Exception as e:
        return f"ERROR: {e}"


def _swarm_message(ctx: ToolContext, recipient: str, content: str,
                    msg_type: str = "message", **kwargs) -> str:
    """Send a message to a specific agent/worker in the swarm."""
    try:
        from supervisor import messaging
        msg_id = messaging.send_message(
            sender="ouroboros",
            recipient=recipient,
            content=content,
            msg_type=msg_type,
        )
        return f"Message sent to '{recipient}' (id: {msg_id})"
    except Exception as e:
        return f"ERROR: {e}"


def _swarm_broadcast(ctx: ToolContext, content: str, **kwargs) -> str:
    """Broadcast a message to all swarm workers."""
    try:
        from supervisor.workers import WORKERS
        from supervisor import messaging

        recipients = [f"worker_{wid}" for wid in WORKERS.keys()]
        if not recipients:
            return "No workers available to broadcast to."

        ids = messaging.broadcast(
            sender="ouroboros",
            recipients=recipients,
            content=content,
        )
        return f"Broadcast sent to {len(recipients)} workers. Message IDs: {ids}"
    except Exception as e:
        return f"ERROR: {e}"


def _swarm_inbox(ctx: ToolContext, agent_id: str = "ouroboros", **kwargs) -> str:
    """Check inbox for an agent. Defaults to Ouroboros' own inbox."""
    try:
        from supervisor import messaging
        messages = messaging.read_messages(agent_id, unread_only=True, limit=20)
        if not messages:
            return f"No unread messages for '{agent_id}'."
        # Clean up file paths from output
        for m in messages:
            m.pop("_file", None)
        return json.dumps({"agent": agent_id, "unread_count": len(messages), "messages": messages}, indent=2)
    except Exception as e:
        return f"ERROR: {e}"


def _swarm_scale(ctx: ToolContext, worker_count: int = 4, **kwargs) -> str:
    """Scale the swarm to a specific number of workers."""
    try:
        from supervisor.workers import WORKERS, kill_workers, spawn_workers

        current = len(WORKERS)
        if worker_count == current:
            return f"Swarm already has {current} workers."

        if worker_count < 1 or worker_count > 10:
            return "ERROR: Worker count must be between 1 and 10."

        # Respawn with new count
        kill_workers()
        spawn_workers(worker_count)

        return f"Swarm scaled from {current} to {worker_count} workers."
    except Exception as e:
        return f"ERROR: {e}"


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("swarm_status", {
            "name": "swarm_status",
            "description": "Get status of swarm: workers (idle/busy), running tasks, pending queue. Use this to see your team.",
            "parameters": {"type": "object", "properties": {}},
        }, _swarm_status),
        ToolEntry("swarm_dispatch", {
            "name": "swarm_dispatch",
            "description": "Dispatch multiple subtasks to swarm workers in parallel. Break big tasks into subtasks and let workers handle them simultaneously.",
            "parameters": {"type": "object", "properties": {
                "subtasks": {
                    "type": "string",
                    "description": 'JSON array of subtasks. Example: [{"description": "Search for X"}, {"description": "Review file Y"}]',
                },
            }, "required": ["subtasks"]},
        }, _swarm_dispatch),
        ToolEntry("swarm_collect", {
            "name": "swarm_collect",
            "description": "Collect results from completed swarm tasks. Use batch_id from swarm_dispatch or leave empty for all results.",
            "parameters": {"type": "object", "properties": {
                "batch_id": {"type": "string", "description": "Batch ID from swarm_dispatch (optional)"},
            }},
        }, _swarm_collect),
        ToolEntry("swarm_message", {
            "name": "swarm_message",
            "description": "Send a message to a specific agent/worker in the swarm.",
            "parameters": {"type": "object", "properties": {
                "recipient": {"type": "string", "description": "Agent/worker ID to message (e.g. 'worker_0')"},
                "content": {"type": "string", "description": "Message content"},
                "msg_type": {"type": "string", "description": "Message type: message, instruction, request", "default": "message"},
            }, "required": ["recipient", "content"]},
        }, _swarm_message),
        ToolEntry("swarm_broadcast", {
            "name": "swarm_broadcast",
            "description": "Broadcast a message to ALL swarm workers at once.",
            "parameters": {"type": "object", "properties": {
                "content": {"type": "string", "description": "Message to broadcast to all workers"},
            }, "required": ["content"]},
        }, _swarm_broadcast),
        ToolEntry("swarm_inbox", {
            "name": "swarm_inbox",
            "description": "Check inbox for unread messages. Defaults to Ouroboros' own inbox.",
            "parameters": {"type": "object", "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to check inbox for", "default": "ouroboros"},
            }},
        }, _swarm_inbox),
        ToolEntry("swarm_scale", {
            "name": "swarm_scale",
            "description": "Scale the swarm up or down (1-10 workers). More workers = more parallel tasks.",
            "parameters": {"type": "object", "properties": {
                "worker_count": {"type": "integer", "description": "Number of workers (1-10)", "default": 4},
            }},
        }, _swarm_scale),
    ]

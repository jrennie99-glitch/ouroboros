"""Agent Scaling System: mass spawning, auto-scaling, agent pools, cloud-ready.

Designed to scale from local (4 workers) to cloud (thousands+).
Currently runs locally with batched task queuing. When cloud endpoints
are added, the same tools scale horizontally.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import time
import uuid
from typing import Any, Dict, List, Optional

from ouroboros.tools.registry import ToolContext, ToolEntry

log = logging.getLogger(__name__)


def _pools_dir(ctx: ToolContext) -> pathlib.Path:
    d = ctx.drive_root / "agent_pools"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_pools(ctx: ToolContext) -> Dict:
    f = _pools_dir(ctx) / "pools.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"pools": {}, "total_spawned": 0, "total_completed": 0}


def _save_pools(ctx: ToolContext, data: Dict) -> None:
    f = _pools_dir(ctx) / "pools.json"
    f.write_text(json.dumps(data, indent=2))


def _scale_create_pool(ctx: ToolContext, pool_name: str, agent_role: str = "worker",
                        agent_prompt: str = "", size: int = 10, **kwargs) -> str:
    """Create a pool of identical agents ready to execute tasks.

    Each agent in the pool is a top-tier copy with the same prompt and capabilities.
    Tasks assigned to the pool are distributed round-robin to available agents.
    """
    if size < 1:
        return "ERROR: Pool size must be at least 1."
    if size > 10000:
        size = 10000  # Cap for local, remove for cloud

    data = _load_pools(ctx)

    pool = {
        "name": pool_name,
        "role": agent_role,
        "prompt": agent_prompt or f"You are a {agent_role} agent in pool '{pool_name}'. Execute tasks efficiently.",
        "size": size,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "ready",
        "tasks_completed": 0,
        "tasks_queued": 0,
        "agents": [
            {"id": f"{pool_name}_{i}", "status": "idle", "tasks_done": 0}
            for i in range(min(size, 100))  # Track first 100 individually
        ],
    }

    data["pools"][pool_name] = pool
    _save_pools(ctx, data)

    return json.dumps({
        "pool": pool_name,
        "size": size,
        "role": agent_role,
        "status": "ready",
        "message": f"Pool '{pool_name}' created with {size} agents. Use scale_dispatch to send tasks.",
    }, indent=2)


def _scale_list_pools(ctx: ToolContext, **kwargs) -> str:
    """List all agent pools and their status."""
    data = _load_pools(ctx)
    pools = []
    for name, pool in data["pools"].items():
        pools.append({
            "name": name,
            "role": pool.get("role"),
            "size": pool.get("size"),
            "status": pool.get("status"),
            "tasks_completed": pool.get("tasks_completed", 0),
            "tasks_queued": pool.get("tasks_queued", 0),
        })
    return json.dumps({
        "total_pools": len(pools),
        "total_spawned": data.get("total_spawned", 0),
        "total_completed": data.get("total_completed", 0),
        "pools": pools,
    }, indent=2)


def _scale_dispatch(ctx: ToolContext, pool_name: str, tasks: str, **kwargs) -> str:
    """Dispatch a batch of tasks to an agent pool.

    tasks: JSON array of task descriptions (strings) or objects with 'description' field.
    All tasks are queued and distributed to pool agents via the swarm system.
    """
    data = _load_pools(ctx)
    pool = data["pools"].get(pool_name)
    if not pool:
        return f"ERROR: Pool '{pool_name}' not found. Create it first with scale_create_pool."

    # Parse tasks
    if isinstance(tasks, str):
        try:
            task_list = json.loads(tasks)
        except json.JSONDecodeError:
            task_list = [tasks]
    elif isinstance(tasks, list):
        task_list = tasks
    else:
        return "ERROR: tasks must be a JSON array or string"

    if not task_list:
        return "ERROR: No tasks provided."

    # Enqueue all tasks via supervisor queue
    try:
        from supervisor.queue import enqueue_task, persist_queue_snapshot
        from supervisor.state import load_state

        st = load_state()
        chat_id = int(st.get("owner_chat_id") or ctx.current_chat_id or 0)
        if not chat_id:
            return "ERROR: No chat_id. Send a message to the bot first."

        batch_id = f"pool_{pool_name}_{uuid.uuid4().hex[:6]}"
        dispatched = []

        for i, task_desc in enumerate(task_list):
            if isinstance(task_desc, dict):
                desc = task_desc.get("description", str(task_desc))
            else:
                desc = str(task_desc)

            agent_id = f"{pool_name}_{i % pool['size']}"
            task_id = f"{batch_id}_{i}"

            # Prepend agent context
            full_text = (
                f"[Pool: {pool_name} | Agent: {agent_id} | Role: {pool.get('role', 'worker')}]\n"
                f"{pool.get('prompt', '')}\n\n"
                f"Task: {desc}"
            )

            enqueue_task({
                "id": task_id,
                "type": "task",
                "chat_id": chat_id,
                "text": full_text,
                "_pool": pool_name,
                "_agent_id": agent_id,
                "_batch_id": batch_id,
                "_batch_index": i,
            })
            dispatched.append({"task_id": task_id, "agent": agent_id, "description": desc[:80]})

        persist_queue_snapshot(reason="scale_dispatch")

        # Update pool stats
        pool["tasks_queued"] = pool.get("tasks_queued", 0) + len(dispatched)
        data["total_spawned"] = data.get("total_spawned", 0) + len(dispatched)
        _save_pools(ctx, data)

        return json.dumps({
            "batch_id": batch_id,
            "pool": pool_name,
            "tasks_dispatched": len(dispatched),
            "tasks_preview": dispatched[:20],
            "message": (
                f"Dispatched {len(dispatched)} tasks to pool '{pool_name}'. "
                f"Workers will pick them up automatically. "
                f"Use swarm_status to monitor progress."
            ),
        }, indent=2)

    except Exception as e:
        log.error("scale_dispatch failed", exc_info=True)
        return f"ERROR: {e}"


def _scale_auto(ctx: ToolContext, target_pending: int = 0, **kwargs) -> str:
    """Auto-scale workers based on current queue depth.

    Increases workers when queue is deep, decreases when idle.
    Respects local hardware limits (max 8 on single machine).
    """
    try:
        from supervisor.workers import WORKERS, kill_workers, spawn_workers
        from supervisor.queue import PENDING, RUNNING

        current_workers = len(WORKERS)
        pending = len(PENDING)
        running = len(RUNNING)
        idle = sum(1 for w in WORKERS.values() if w.busy_task_id is None)

        # Auto-scale logic
        max_local = min(8, os.cpu_count() or 4)
        target = current_workers

        if pending > current_workers * 2 and current_workers < max_local:
            target = min(max_local, current_workers + 2)
        elif pending == 0 and idle > 2 and current_workers > 2:
            target = max(2, current_workers - 1)

        if target_pending > 0:
            # User specified target: scale to handle it
            target = min(max_local, max(2, target_pending // 2))

        action = "no_change"
        if target != current_workers:
            kill_workers()
            spawn_workers(target)
            action = "scaled"

        return json.dumps({
            "previous_workers": current_workers,
            "current_workers": target,
            "pending_tasks": pending,
            "running_tasks": running,
            "idle_workers": idle,
            "max_local": max_local,
            "action": action,
            "message": (
                f"Workers: {current_workers} -> {target}. "
                f"Queue: {pending} pending, {running} running. "
                f"Max local capacity: {max_local}."
            ),
        }, indent=2)

    except Exception as e:
        return f"ERROR: {e}"


def _scale_stats(ctx: ToolContext, **kwargs) -> str:
    """Get scaling statistics: total agents spawned, completed, throughput."""
    data = _load_pools(ctx)

    # Get current queue stats
    try:
        from supervisor.workers import WORKERS
        from supervisor.queue import PENDING, RUNNING
        current = {
            "workers": len(WORKERS),
            "pending": len(PENDING),
            "running": len(RUNNING),
            "idle": sum(1 for w in WORKERS.values() if w.busy_task_id is None),
        }
    except Exception:
        current = {"workers": 0, "pending": 0, "running": 0, "idle": 0}

    stats = {
        "current_capacity": current,
        "total_pools": len(data["pools"]),
        "total_agents_spawned": data.get("total_spawned", 0),
        "total_tasks_completed": data.get("total_completed", 0),
        "max_local_workers": min(8, os.cpu_count() or 4),
        "scaling_mode": "local",
        "cloud_endpoints": [],  # Future: add cloud GPU endpoints here
        "pools": {
            name: {"size": p.get("size"), "completed": p.get("tasks_completed", 0)}
            for name, p in data["pools"].items()
        },
    }
    return json.dumps(stats, indent=2)


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("scale_create_pool", {
            "name": "scale_create_pool",
            "description": "Create a pool of identical top-tier agents ready for mass task execution. Each agent is an exact copy.",
            "parameters": {"type": "object", "properties": {
                "pool_name": {"type": "string", "description": "Name for the agent pool"},
                "agent_role": {"type": "string", "description": "Role for all agents in pool", "default": "worker"},
                "agent_prompt": {"type": "string", "description": "System prompt for all agents in pool"},
                "size": {"type": "integer", "description": "Number of agents in pool (up to 10000)", "default": 10},
            }, "required": ["pool_name"]},
        }, _scale_create_pool),
        ToolEntry("scale_list_pools", {
            "name": "scale_list_pools",
            "description": "List all agent pools with status, sizes, and completion stats.",
            "parameters": {"type": "object", "properties": {}},
        }, _scale_list_pools),
        ToolEntry("scale_dispatch", {
            "name": "scale_dispatch",
            "description": "Dispatch a batch of tasks to an agent pool for mass parallel execution.",
            "parameters": {"type": "object", "properties": {
                "pool_name": {"type": "string", "description": "Pool to dispatch tasks to"},
                "tasks": {"type": "string", "description": "JSON array of task descriptions to execute"},
            }, "required": ["pool_name", "tasks"]},
        }, _scale_dispatch),
        ToolEntry("scale_auto", {
            "name": "scale_auto",
            "description": "Auto-scale workers based on queue depth. Scales up when busy, down when idle.",
            "parameters": {"type": "object", "properties": {
                "target_pending": {"type": "integer", "description": "Target number of pending tasks to handle (0=auto)", "default": 0},
            }},
        }, _scale_auto),
        ToolEntry("scale_stats", {
            "name": "scale_stats",
            "description": "Get scaling statistics: total agents spawned, tasks completed, throughput, capacity.",
            "parameters": {"type": "object", "properties": {}},
        }, _scale_stats),
    ]

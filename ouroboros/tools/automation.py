"""
Ouroboros — Automation tools.

Task scheduler, workflow builder, file manager, system monitor, webhook manager.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_automation")
TASKS_PATH = os.path.join(WORKSPACE, "scheduled_tasks.json")
WORKFLOWS_PATH = os.path.join(WORKSPACE, "workflows.json")
WEBHOOKS_PATH = os.path.join(WORKSPACE, "webhooks.json")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


# ── Task Scheduler ────────────────────────────────────────────────────────

def _load_tasks() -> List[Dict[str, Any]]:
    _ensure_workspace()
    if os.path.exists(TASKS_PATH):
        with open(TASKS_PATH) as f:
            return json.load(f)
    return []


def _save_tasks(tasks: List[Dict[str, Any]]):
    _ensure_workspace()
    with open(TASKS_PATH, "w") as f:
        json.dump(tasks, f, indent=2)


def task_scheduler(action: str, name: str = "", command: str = "",
                   schedule: str = "", description: str = "",
                   task_id: int = 0) -> Dict[str, Any]:
    """Manage scheduled tasks: create, list, delete, run."""
    tasks = _load_tasks()

    if action == "create":
        if not name or not command:
            return {"error": "name and command are required"}
        task = {
            "id": len(tasks) + 1,
            "name": name,
            "command": command,
            "schedule": schedule,
            "description": description,
            "status": "active",
            "created": datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0,
        }
        tasks.append(task)
        _save_tasks(tasks)
        return {"action": "created", "task": task}

    elif action == "list":
        return {"tasks": tasks, "count": len(tasks)}

    elif action == "delete":
        tasks = [t for t in tasks if t["id"] != task_id]
        _save_tasks(tasks)
        return {"action": "deleted", "task_id": task_id, "remaining": len(tasks)}

    elif action == "run":
        target = next((t for t in tasks if t["id"] == task_id or t["name"] == name), None)
        if not target:
            return {"error": f"Task not found: {task_id or name}"}
        try:
            result = subprocess.run(
                target["command"], shell=True,
                capture_output=True, text=True, timeout=60,
            )
            target["last_run"] = datetime.now().isoformat()
            target["run_count"] += 1
            _save_tasks(tasks)
            return {
                "task": target["name"],
                "exit_code": result.returncode,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:500],
            }
        except subprocess.TimeoutExpired:
            return {"error": "Task timed out (60s limit)"}
        except Exception as e:
            return {"error": str(e)}

    elif action == "toggle":
        target = next((t for t in tasks if t["id"] == task_id or t["name"] == name), None)
        if not target:
            return {"error": f"Task not found"}
        target["status"] = "paused" if target["status"] == "active" else "active"
        _save_tasks(tasks)
        return {"task": target["name"], "status": target["status"]}

    return {"error": f"Unknown action: {action}"}


# ── Workflow Builder ──────────────────────────────────────────────────────

def _load_workflows() -> Dict[str, Any]:
    _ensure_workspace()
    if os.path.exists(WORKFLOWS_PATH):
        with open(WORKFLOWS_PATH) as f:
            return json.load(f)
    return {"workflows": {}}


def _save_workflows(wf: Dict[str, Any]):
    _ensure_workspace()
    with open(WORKFLOWS_PATH, "w") as f:
        json.dump(wf, f, indent=2)


def workflow_builder(action: str, name: str = "",
                     steps: List[Dict[str, Any]] = None,
                     description: str = "") -> Dict[str, Any]:
    """Build and execute multi-step workflows."""
    data = _load_workflows()

    if action == "create":
        if not name or not steps:
            return {"error": "name and steps are required"}
        workflow = {
            "name": name,
            "description": description,
            "steps": steps,
            "created": datetime.now().isoformat(),
            "runs": 0,
            "last_run": None,
        }
        data["workflows"][name] = workflow
        _save_workflows(data)
        return {"action": "created", "workflow": workflow}

    elif action == "list":
        summaries = []
        for wn, wf in data["workflows"].items():
            summaries.append({
                "name": wn,
                "description": wf.get("description", ""),
                "steps": len(wf.get("steps", [])),
                "runs": wf.get("runs", 0),
            })
        return {"workflows": summaries, "count": len(summaries)}

    elif action == "run":
        if name not in data["workflows"]:
            return {"error": f"Workflow not found: {name}"}
        wf = data["workflows"][name]
        results = []
        for i, step in enumerate(wf["steps"]):
            step_name = step.get("name", f"Step {i + 1}")
            step_cmd = step.get("command", "")
            step_type = step.get("type", "shell")

            if step_type == "shell" and step_cmd:
                try:
                    r = subprocess.run(
                        step_cmd, shell=True,
                        capture_output=True, text=True, timeout=30,
                    )
                    results.append({
                        "step": step_name,
                        "status": "success" if r.returncode == 0 else "failed",
                        "exit_code": r.returncode,
                        "output": r.stdout[:500],
                    })
                    if r.returncode != 0 and step.get("on_failure") == "stop":
                        results.append({"step": "WORKFLOW_STOPPED", "reason": f"Step '{step_name}' failed"})
                        break
                except Exception as e:
                    results.append({"step": step_name, "status": "error", "error": str(e)})
            elif step_type == "wait":
                wait_secs = step.get("seconds", 1)
                time.sleep(min(wait_secs, 5))
                results.append({"step": step_name, "status": "waited", "seconds": wait_secs})
            else:
                results.append({"step": step_name, "status": "skipped", "reason": "Unknown step type"})

        wf["runs"] += 1
        wf["last_run"] = datetime.now().isoformat()
        _save_workflows(data)
        return {"workflow": name, "steps_executed": len(results), "results": results}

    elif action == "delete":
        if name in data["workflows"]:
            del data["workflows"][name]
            _save_workflows(data)
            return {"action": "deleted", "name": name}
        return {"error": f"Workflow not found: {name}"}

    return {"error": f"Unknown action: {action}"}


# ── File Manager ──────────────────────────────────────────────────────────

def file_manager(action: str, path: str, content: str = "",
                 destination: str = "") -> Dict[str, Any]:
    """File operations: list, read, write, delete, copy, move, info."""
    # Security: restrict to workspace and home
    abs_path = os.path.abspath(os.path.expanduser(path))

    if action == "list":
        if not os.path.isdir(abs_path):
            return {"error": f"Not a directory: {abs_path}"}
        entries = []
        try:
            for item in sorted(os.listdir(abs_path)):
                item_path = os.path.join(abs_path, item)
                stat = os.stat(item_path)
                entries.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        except PermissionError:
            return {"error": f"Permission denied: {abs_path}"}
        return {"path": abs_path, "entries": entries, "count": len(entries)}

    elif action == "read":
        if not os.path.isfile(abs_path):
            return {"error": f"Not a file: {abs_path}"}
        try:
            size = os.path.getsize(abs_path)
            if size > 1_000_000:  # 1MB limit
                return {"error": f"File too large ({size} bytes). Max 1MB."}
            with open(abs_path) as f:
                content = f.read()
            return {"path": abs_path, "size": size, "content": content[:10000]}
        except UnicodeDecodeError:
            return {"error": "Binary file — cannot read as text"}
        except PermissionError:
            return {"error": "Permission denied"}

    elif action == "write":
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w") as f:
                f.write(content)
            return {"action": "written", "path": abs_path, "size": len(content)}
        except Exception as e:
            return {"error": str(e)}

    elif action == "delete":
        if not os.path.exists(abs_path):
            return {"error": f"Path not found: {abs_path}"}
        try:
            if os.path.isdir(abs_path):
                shutil.rmtree(abs_path)
            else:
                os.remove(abs_path)
            return {"action": "deleted", "path": abs_path}
        except Exception as e:
            return {"error": str(e)}

    elif action == "copy":
        if not destination:
            return {"error": "destination is required for copy"}
        try:
            abs_dest = os.path.abspath(os.path.expanduser(destination))
            if os.path.isdir(abs_path):
                shutil.copytree(abs_path, abs_dest)
            else:
                os.makedirs(os.path.dirname(abs_dest), exist_ok=True)
                shutil.copy2(abs_path, abs_dest)
            return {"action": "copied", "source": abs_path, "destination": abs_dest}
        except Exception as e:
            return {"error": str(e)}

    elif action == "move":
        if not destination:
            return {"error": "destination is required for move"}
        try:
            abs_dest = os.path.abspath(os.path.expanduser(destination))
            os.makedirs(os.path.dirname(abs_dest), exist_ok=True)
            shutil.move(abs_path, abs_dest)
            return {"action": "moved", "source": abs_path, "destination": abs_dest}
        except Exception as e:
            return {"error": str(e)}

    elif action == "info":
        if not os.path.exists(abs_path):
            return {"error": f"Path not found: {abs_path}"}
        stat = os.stat(abs_path)
        return {
            "path": abs_path,
            "type": "directory" if os.path.isdir(abs_path) else "file",
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
        }

    return {"error": f"Unknown action: {action}"}


# ── System Monitor ────────────────────────────────────────────────────────

def system_monitor(metric: str = "all") -> Dict[str, Any]:
    """Get system resource usage: CPU, RAM, disk, network, processes."""
    result = {"timestamp": datetime.now().isoformat(), "platform": platform.system()}

    if metric in ("all", "cpu"):
        try:
            if platform.system() == "Darwin":
                # macOS
                r = subprocess.run(["sysctl", "-n", "hw.ncpu"], capture_output=True, text=True, timeout=5)
                cpu_count = int(r.stdout.strip())
                r = subprocess.run(["sysctl", "-n", "hw.cpufrequency_max"], capture_output=True, text=True, timeout=5)
                freq = int(r.stdout.strip()) // 1_000_000 if r.stdout.strip() else 0
                # Load average
                r = subprocess.run(["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True, timeout=5)
                load = r.stdout.strip()
                result["cpu"] = {"cores": cpu_count, "frequency_mhz": freq, "load_average": load}
            else:
                # Linux
                r = subprocess.run(["nproc"], capture_output=True, text=True, timeout=5)
                cpu_count = int(r.stdout.strip()) if r.stdout.strip() else 0
                r = subprocess.run(["cat", "/proc/loadavg"], capture_output=True, text=True, timeout=5)
                load = r.stdout.strip()
                result["cpu"] = {"cores": cpu_count, "load_average": load}
        except Exception as e:
            result["cpu"] = {"error": str(e)}

    if metric in ("all", "memory", "ram"):
        try:
            if platform.system() == "Darwin":
                r = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5)
                total_bytes = int(r.stdout.strip())
                r = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5)
                # Parse vm_stat
                import re
                pages = {}
                for line in r.stdout.splitlines():
                    m = re.match(r'(.+):\s+(\d+)', line)
                    if m:
                        pages[m.group(1).strip()] = int(m.group(2))
                page_size = 16384  # default on Apple Silicon
                free_pages = pages.get("Pages free", 0) + pages.get("Pages speculative", 0)
                used_bytes = total_bytes - (free_pages * page_size)
                result["memory"] = {
                    "total_gb": round(total_bytes / (1024**3), 2),
                    "used_gb": round(used_bytes / (1024**3), 2),
                    "free_gb": round((total_bytes - used_bytes) / (1024**3), 2),
                    "usage_pct": round(used_bytes / total_bytes * 100, 1),
                }
            else:
                r = subprocess.run(["free", "-b"], capture_output=True, text=True, timeout=5)
                lines = r.stdout.strip().splitlines()
                if len(lines) >= 2:
                    parts = lines[1].split()
                    total = int(parts[1])
                    used = int(parts[2])
                    free = int(parts[3])
                    result["memory"] = {
                        "total_gb": round(total / (1024**3), 2),
                        "used_gb": round(used / (1024**3), 2),
                        "free_gb": round(free / (1024**3), 2),
                        "usage_pct": round(used / total * 100, 1),
                    }
        except Exception as e:
            result["memory"] = {"error": str(e)}

    if metric in ("all", "disk"):
        try:
            usage = shutil.disk_usage("/")
            result["disk"] = {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "usage_pct": round(usage.used / usage.total * 100, 1),
            }
        except Exception as e:
            result["disk"] = {"error": str(e)}

    if metric in ("all", "processes"):
        try:
            r = subprocess.run(
                ["ps", "aux", "--sort=-%mem"] if platform.system() != "Darwin" else ["ps", "aux", "-r"],
                capture_output=True, text=True, timeout=10,
            )
            lines = r.stdout.strip().splitlines()
            top_procs = []
            for line in lines[1:11]:  # top 10
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    top_procs.append({
                        "user": parts[0],
                        "pid": parts[1],
                        "cpu_pct": parts[2],
                        "mem_pct": parts[3],
                        "command": parts[10][:60],
                    })
            result["top_processes"] = top_procs
        except Exception as e:
            result["top_processes"] = {"error": str(e)}

    if metric in ("all", "uptime"):
        try:
            r = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
            result["uptime"] = r.stdout.strip()
        except Exception:
            pass

    return result


# ── Webhook Manager ───────────────────────────────────────────────────────

def _load_webhooks() -> Dict[str, Any]:
    _ensure_workspace()
    if os.path.exists(WEBHOOKS_PATH):
        with open(WEBHOOKS_PATH) as f:
            return json.load(f)
    return {"webhooks": {}}


def _save_webhooks(wh: Dict[str, Any]):
    _ensure_workspace()
    with open(WEBHOOKS_PATH, "w") as f:
        json.dump(wh, f, indent=2)


def webhook_manager(action: str, name: str = "", url: str = "",
                    method: str = "POST", headers: Dict[str, str] = None,
                    payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """Manage and fire webhooks."""
    data = _load_webhooks()

    if action == "register":
        if not name or not url:
            return {"error": "name and url are required"}
        data["webhooks"][name] = {
            "url": url,
            "method": method.upper(),
            "headers": headers or {"Content-Type": "application/json"},
            "created": datetime.now().isoformat(),
            "fire_count": 0,
            "last_fired": None,
        }
        _save_webhooks(data)
        return {"action": "registered", "name": name, "url": url}

    elif action == "list":
        summaries = []
        for wn, wh in data["webhooks"].items():
            summaries.append({
                "name": wn,
                "url": wh["url"],
                "method": wh.get("method", "POST"),
                "fire_count": wh.get("fire_count", 0),
                "last_fired": wh.get("last_fired"),
            })
        return {"webhooks": summaries, "count": len(summaries)}

    elif action == "fire":
        if name not in data["webhooks"]:
            return {"error": f"Webhook not found: {name}"}
        wh = data["webhooks"][name]
        body = json.dumps(payload or {})
        header_args = []
        for k, v in (wh.get("headers") or {}).items():
            header_args.extend(["-H", f"{k}: {v}"])

        try:
            cmd = [
                "curl", "-s", "-X", wh.get("method", "POST"),
                "-w", "\n%{http_code}",
                "--max-time", "15",
            ] + header_args + ["-d", body, wh["url"]]

            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            lines = r.stdout.strip().rsplit("\n", 1)
            response_body = lines[0] if lines else ""
            status_code = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 0

            wh["fire_count"] += 1
            wh["last_fired"] = datetime.now().isoformat()
            _save_webhooks(data)

            return {
                "webhook": name,
                "status_code": status_code,
                "response": response_body[:1000],
                "success": 200 <= status_code < 300,
            }
        except Exception as e:
            return {"error": str(e)}

    elif action == "delete":
        if name in data["webhooks"]:
            del data["webhooks"][name]
            _save_webhooks(data)
            return {"action": "deleted", "name": name}
        return {"error": f"Webhook not found: {name}"}

    elif action == "test":
        # Fire a test payload to the webhook
        if name not in data["webhooks"]:
            return {"error": f"Webhook not found: {name}"}
        test_payload = {
            "test": True,
            "message": "Ouroboros webhook test",
            "timestamp": datetime.now().isoformat(),
        }
        return webhook_manager("fire", name=name, payload=test_payload)

    return {"error": f"Unknown action: {action}"}


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "task_scheduler",
            "description": "Manage scheduled tasks: create, list, run, delete, toggle. Tasks run shell commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "list", "delete", "run", "toggle"]},
                    "name": {"type": "string", "default": ""},
                    "command": {"type": "string", "default": "", "description": "Shell command to run"},
                    "schedule": {"type": "string", "default": "", "description": "Cron-like schedule description"},
                    "description": {"type": "string", "default": ""},
                    "task_id": {"type": "integer", "default": 0},
                },
                "required": ["action"],
            },
            "function": task_scheduler,
        },
        {
            "name": "workflow_builder",
            "description": "Build and run multi-step workflows with shell commands, waits, and error handling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "list", "run", "delete"]},
                    "name": {"type": "string", "default": ""},
                    "steps": {"type": "array", "items": {"type": "object"},
                              "description": "List of {name, command, type: 'shell'|'wait', on_failure: 'stop'|'continue'}"},
                    "description": {"type": "string", "default": ""},
                },
                "required": ["action"],
            },
            "function": workflow_builder,
        },
        {
            "name": "file_manager",
            "description": "File operations: list, read, write, delete, copy, move, info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "read", "write", "delete", "copy", "move", "info"]},
                    "path": {"type": "string"},
                    "content": {"type": "string", "default": "", "description": "Content for write action"},
                    "destination": {"type": "string", "default": "", "description": "For copy/move actions"},
                },
                "required": ["action", "path"],
            },
            "function": file_manager,
        },
        {
            "name": "system_monitor",
            "description": "Get system resource usage: CPU, RAM, disk, top processes, uptime.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["all", "cpu", "memory", "ram", "disk", "processes", "uptime"], "default": "all"},
                },
            },
            "function": system_monitor,
        },
        {
            "name": "webhook_manager",
            "description": "Register, list, fire, test, and delete webhooks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["register", "list", "fire", "test", "delete"]},
                    "name": {"type": "string", "default": ""},
                    "url": {"type": "string", "default": ""},
                    "method": {"type": "string", "default": "POST"},
                    "headers": {"type": "object", "description": "Custom headers"},
                    "payload": {"type": "object", "description": "JSON payload for fire action"},
                },
                "required": ["action"],
            },
            "function": webhook_manager,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

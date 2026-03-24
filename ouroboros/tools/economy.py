"""Autonomous Economy System: revenue tracking, opportunity scanning, freelance, arbitrage.

This module gives Ouroboros the ability to:
- Track income/expenses across all operations
- Scan for revenue opportunities (freelance, bounties, affiliate)
- Manage crypto portfolios via web search + tracking
- Generate financial reports
- Monitor costs and optimize spending
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


def _economy_dir(ctx: ToolContext) -> pathlib.Path:
    d = ctx.drive_root / "economy"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_ledger(ctx: ToolContext) -> Dict:
    ledger_file = _economy_dir(ctx) / "ledger.json"
    if ledger_file.exists():
        try:
            return json.loads(ledger_file.read_text())
        except Exception:
            pass
    return {
        "total_income": 0.0,
        "total_expenses": 0.0,
        "balance": 0.0,
        "transactions": [],
        "revenue_streams": [],
        "opportunities": [],
    }


def _save_ledger(ctx: ToolContext, ledger: Dict) -> None:
    ledger_file = _economy_dir(ctx) / "ledger.json"
    ledger_file.write_text(json.dumps(ledger, indent=2))


def _economy_status(ctx: ToolContext, **kwargs) -> str:
    """Get full economic status: balance, income, expenses, active streams."""
    ledger = _load_ledger(ctx)

    # Calculate LLM costs from state
    state_file = ctx.drive_root / "state" / "state.json"
    llm_spent = 0.0
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            llm_spent = float(state.get("spent_usd", 0))
        except Exception:
            pass

    status = {
        "balance": ledger["balance"],
        "total_income": ledger["total_income"],
        "total_expenses": ledger["total_expenses"],
        "llm_costs": llm_spent,
        "net_profit": ledger["total_income"] - ledger["total_expenses"] - llm_spent,
        "active_revenue_streams": len(ledger.get("revenue_streams", [])),
        "pending_opportunities": len(ledger.get("opportunities", [])),
        "recent_transactions": ledger["transactions"][-10:],
    }
    return json.dumps(status, indent=2)


def _economy_record(ctx: ToolContext, amount: float, description: str,
                     category: str = "general", tx_type: str = "income", **kwargs) -> str:
    """Record an income or expense transaction."""
    ledger = _load_ledger(ctx)

    tx = {
        "id": uuid.uuid4().hex[:8],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": tx_type,
        "amount": abs(amount),
        "category": category,
        "description": description,
    }

    ledger["transactions"].append(tx)

    if tx_type == "income":
        ledger["total_income"] += abs(amount)
        ledger["balance"] += abs(amount)
    else:
        ledger["total_expenses"] += abs(amount)
        ledger["balance"] -= abs(amount)

    _save_ledger(ctx, ledger)
    symbol = "+" if tx_type == "income" else "-"
    return f"Recorded: {symbol}${abs(amount):.2f} ({category}) — {description}"


def _economy_add_stream(ctx: ToolContext, name: str, stream_type: str = "passive",
                         description: str = "", expected_monthly: float = 0, **kwargs) -> str:
    """Add a revenue stream to track."""
    ledger = _load_ledger(ctx)

    stream = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "type": stream_type,  # passive, active, freelance, bounty, affiliate, trading
        "description": description,
        "expected_monthly_usd": expected_monthly,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active",
        "total_earned": 0.0,
    }

    ledger.setdefault("revenue_streams", []).append(stream)
    _save_ledger(ctx, ledger)
    return f"Revenue stream added: {name} ({stream_type}) — expected ${expected_monthly:.2f}/month"


def _economy_scan_opportunities(ctx: ToolContext, focus: str = "all", **kwargs) -> str:
    """Scan for revenue opportunities. Returns actionable suggestions.

    Focus areas: freelance, bounty, affiliate, trading, content, all
    """
    opportunities = {
        "freelance": [
            {"platform": "Upwork", "action": "Search for AI/automation gigs", "tool": "web_search"},
            {"platform": "Fiverr", "action": "List AI agent services", "tool": "web_search"},
            {"platform": "Toptal", "action": "Apply for AI engineering roles", "tool": "web_search"},
        ],
        "bounty": [
            {"platform": "HackerOne", "action": "Find bug bounty programs", "tool": "web_search"},
            {"platform": "Immunefi", "action": "Check smart contract bounties", "tool": "web_search"},
            {"platform": "GitHub", "action": "Search for repos with bounty labels", "tool": "list_github_issues"},
        ],
        "affiliate": [
            {"platform": "Amazon Associates", "action": "Generate affiliate links for tech reviews", "tool": "web_search"},
            {"platform": "AI tool affiliates", "action": "Promote AI tools for commission", "tool": "web_search"},
        ],
        "trading": [
            {"platform": "Crypto exchanges", "action": "Monitor arbitrage opportunities", "tool": "qpanda_track_crypto"},
            {"platform": "DeFi", "action": "Yield farming opportunities", "tool": "web_search"},
        ],
        "content": [
            {"platform": "YouTube", "action": "Create AI tutorial content", "tool": "opencode_generate"},
            {"platform": "Medium/Substack", "action": "Write technical articles", "tool": "opencode_generate"},
            {"platform": "Twitter/X", "action": "Build audience with AI insights", "tool": "web_search"},
        ],
    }

    if focus != "all" and focus in opportunities:
        result = {focus: opportunities[focus]}
    else:
        result = opportunities

    # Store as pending opportunities
    ledger = _load_ledger(ctx)
    ledger["opportunities"] = []
    for category, opps in result.items():
        for opp in opps:
            opp["category"] = category
            opp["scanned_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            ledger["opportunities"].append(opp)
    _save_ledger(ctx, ledger)

    return json.dumps({
        "opportunities_found": sum(len(v) for v in result.values()),
        "opportunities": result,
        "instruction": "Use web_search and browse_page to investigate these opportunities. "
                       "Record any earnings with economy_record.",
    }, indent=2)


def _economy_report(ctx: ToolContext, period: str = "all", **kwargs) -> str:
    """Generate financial report."""
    ledger = _load_ledger(ctx)

    # Group by category
    income_by_cat = {}
    expense_by_cat = {}
    for tx in ledger["transactions"]:
        cat = tx.get("category", "general")
        amt = abs(tx.get("amount", 0))
        if tx.get("type") == "income":
            income_by_cat[cat] = income_by_cat.get(cat, 0) + amt
        else:
            expense_by_cat[cat] = expense_by_cat.get(cat, 0) + amt

    # LLM costs
    state_file = ctx.drive_root / "state" / "state.json"
    llm_spent = 0.0
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            llm_spent = float(state.get("spent_usd", 0))
        except Exception:
            pass

    report = {
        "period": period,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_income": ledger["total_income"],
            "total_expenses": ledger["total_expenses"],
            "llm_infrastructure_cost": llm_spent,
            "net_profit": ledger["total_income"] - ledger["total_expenses"] - llm_spent,
            "balance": ledger["balance"],
        },
        "income_breakdown": income_by_cat,
        "expense_breakdown": expense_by_cat,
        "active_streams": len([s for s in ledger.get("revenue_streams", []) if s.get("status") == "active"]),
        "total_transactions": len(ledger["transactions"]),
    }
    return json.dumps(report, indent=2)


def _economy_cost_optimize(ctx: ToolContext, **kwargs) -> str:
    """Analyze current costs and suggest optimizations."""
    state_file = ctx.drive_root / "state" / "state.json"
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            pass

    llm_spent = float(state.get("spent_usd", 0))
    model = os.environ.get("OUROBOROS_MODEL", "unknown")
    base_url = os.environ.get("OUROBOROS_LLM_BASE_URL", "unknown")

    optimizations = []

    # Check if using paid API when free is available
    if "openrouter" in base_url and ":free" not in model:
        optimizations.append({
            "type": "model_switch",
            "saving": "significant",
            "action": "Switch to free models on OpenRouter (add :free suffix)",
        })

    # Check if using cloud when local is available
    if "localhost" not in base_url:
        optimizations.append({
            "type": "use_local",
            "saving": "100% of LLM costs",
            "action": "Switch to local Ollama (OUROBOROS_LLM_BASE_URL=http://localhost:11434/v1)",
        })

    # Check worker count
    max_workers = int(os.environ.get("OUROBOROS_MAX_WORKERS", 4))
    if max_workers > 2 and llm_spent > 0:
        optimizations.append({
            "type": "reduce_workers",
            "saving": f"~{(max_workers-2)/max_workers*100:.0f}% reduction in parallel costs",
            "action": f"Reduce workers from {max_workers} to 2 when not needed",
        })

    # Check background consciousness
    if not os.environ.get("OUROBOROS_DISABLE_BG"):
        optimizations.append({
            "type": "disable_background",
            "saving": "variable",
            "action": "Set OUROBOROS_DISABLE_BG=1 to stop background LLM calls",
        })

    result = {
        "current_costs": {
            "llm_spent_usd": llm_spent,
            "model": model,
            "base_url": base_url,
            "workers": max_workers,
        },
        "optimizations": optimizations,
        "total_optimizations": len(optimizations),
    }
    return json.dumps(result, indent=2)


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("economy_status", {
            "name": "economy_status",
            "description": "Get full economic status: balance, income, expenses, profit, active revenue streams.",
            "parameters": {"type": "object", "properties": {}},
        }, _economy_status),
        ToolEntry("economy_record", {
            "name": "economy_record",
            "description": "Record an income or expense transaction in the ledger.",
            "parameters": {"type": "object", "properties": {
                "amount": {"type": "number", "description": "Amount in USD"},
                "description": {"type": "string", "description": "What the transaction is for"},
                "category": {"type": "string", "description": "Category: freelance, bounty, trading, affiliate, content, infrastructure, etc.", "default": "general"},
                "tx_type": {"type": "string", "enum": ["income", "expense"], "default": "income"},
            }, "required": ["amount", "description"]},
        }, _economy_record),
        ToolEntry("economy_add_stream", {
            "name": "economy_add_stream",
            "description": "Add a revenue stream to track (freelance gig, bounty program, affiliate, etc.).",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string", "description": "Name of the revenue stream"},
                "stream_type": {"type": "string", "enum": ["passive", "active", "freelance", "bounty", "affiliate", "trading"], "default": "active"},
                "description": {"type": "string", "description": "Description of the stream"},
                "expected_monthly": {"type": "number", "description": "Expected monthly income in USD", "default": 0},
            }, "required": ["name"]},
        }, _economy_add_stream),
        ToolEntry("economy_scan", {
            "name": "economy_scan",
            "description": "Scan for revenue opportunities: freelance, bug bounties, affiliate, trading, content creation.",
            "parameters": {"type": "object", "properties": {
                "focus": {"type": "string", "enum": ["all", "freelance", "bounty", "affiliate", "trading", "content"], "default": "all"},
            }},
        }, _economy_scan_opportunities),
        ToolEntry("economy_report", {
            "name": "economy_report",
            "description": "Generate comprehensive financial report with income/expense breakdown.",
            "parameters": {"type": "object", "properties": {
                "period": {"type": "string", "description": "Report period", "default": "all"},
            }},
        }, _economy_report),
        ToolEntry("economy_cost_optimize", {
            "name": "economy_cost_optimize",
            "description": "Analyze current infrastructure costs and suggest optimizations to reduce spending.",
            "parameters": {"type": "object", "properties": {}},
        }, _economy_cost_optimize),
    ]

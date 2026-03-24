"""QPanda integration: financial operations, crypto tracking, payment systems."""

from __future__ import annotations

import json
import logging
import pathlib
import time
from typing import Any, Dict, List

from ouroboros.tools.registry import ToolContext, ToolEntry

log = logging.getLogger(__name__)

QPANDA_DIR = pathlib.Path(__file__).resolve().parents[2] / "workspace" / "qpanda"


def _qpanda_status(ctx: ToolContext, **kwargs) -> str:
    """Get status of QPanda financial operations system."""
    result = {
        "path": str(QPANDA_DIR),
        "exists": QPANDA_DIR.exists(),
        "capabilities": [
            "crypto_price_tracking",
            "portfolio_management",
            "payment_processing",
            "financial_analysis",
            "budget_tracking",
        ],
    }
    # Check financial state
    fin_dir = ctx.drive_root / "financial"
    if fin_dir.exists():
        for f in fin_dir.glob("*.json"):
            try:
                result[f.stem] = json.loads(f.read_text())
            except Exception:
                pass
    return json.dumps(result, indent=2)


def _qpanda_track_crypto(ctx: ToolContext, symbol: str = "BTC", **kwargs) -> str:
    """Track cryptocurrency price. Uses web search for real-time data."""
    tracking = {
        "symbol": symbol.upper(),
        "instruction": (
            f"Use web_search to find current price of {symbol.upper()}. "
            f"Search for '{symbol} price USD today'. Return current price, 24h change, and market cap."
        ),
        "status": "tracking_prepared",
    }
    return json.dumps(tracking, indent=2)


def _qpanda_financial_report(ctx: ToolContext, **kwargs) -> str:
    """Generate financial report of all operations, spending, and revenue."""
    fin_dir = ctx.drive_root / "financial"
    fin_dir.mkdir(parents=True, exist_ok=True)

    # Read state
    state_file = ctx.drive_root / "state" / "state.json"
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            pass

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "budget_total": float(state.get("total_budget", 0)),
        "spent_usd": float(state.get("spent_usd", 0)),
        "remaining": float(state.get("total_budget", 0)) - float(state.get("spent_usd", 0)),
        "revenue": 0.0,  # Track revenue from operations
        "operations": [],
    }

    # Read transaction log if exists
    tx_file = fin_dir / "transactions.jsonl"
    if tx_file.exists():
        lines = tx_file.read_text().strip().splitlines()
        for line in lines[-20:]:  # Last 20 transactions
            try:
                report["operations"].append(json.loads(line))
            except Exception:
                pass

    return json.dumps(report, indent=2)


def _qpanda_record_transaction(ctx: ToolContext, amount: float, description: str,
                                tx_type: str = "expense", **kwargs) -> str:
    """Record a financial transaction."""
    fin_dir = ctx.drive_root / "financial"
    fin_dir.mkdir(parents=True, exist_ok=True)

    tx = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "amount": amount,
        "type": tx_type,
        "description": description,
        "currency": "USD",
    }

    tx_file = fin_dir / "transactions.jsonl"
    with open(tx_file, "a") as f:
        f.write(json.dumps(tx) + "\n")

    return f"Transaction recorded: {tx_type} ${amount:.2f} — {description}"


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("qpanda_status", {
            "name": "qpanda_status",
            "description": "Get status of QPanda financial operations system. Shows budget, spending, and capabilities.",
            "parameters": {"type": "object", "properties": {}},
        }, _qpanda_status),
        ToolEntry("qpanda_track_crypto", {
            "name": "qpanda_track_crypto",
            "description": "Track cryptocurrency price in real-time using web search.",
            "parameters": {"type": "object", "properties": {
                "symbol": {"type": "string", "description": "Crypto symbol (BTC, ETH, SOL, etc.)", "default": "BTC"},
            }},
        }, _qpanda_track_crypto),
        ToolEntry("qpanda_financial_report", {
            "name": "qpanda_financial_report",
            "description": "Generate complete financial report: budget, spending, revenue, transactions.",
            "parameters": {"type": "object", "properties": {}},
        }, _qpanda_financial_report),
        ToolEntry("qpanda_record_transaction", {
            "name": "qpanda_record_transaction",
            "description": "Record a financial transaction (income or expense).",
            "parameters": {"type": "object", "properties": {
                "amount": {"type": "number", "description": "Transaction amount in USD"},
                "description": {"type": "string", "description": "What the transaction is for"},
                "tx_type": {"type": "string", "enum": ["income", "expense", "investment"], "default": "expense"},
            }, "required": ["amount", "description"]},
        }, _qpanda_record_transaction),
    ]

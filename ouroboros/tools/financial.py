"""
Ouroboros — Financial Agency tools.

Crypto tracking, payment collection, revenue management, trading analysis.
Principle 9: Financial Agency.
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

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_financial")
LEDGER_PATH = os.path.join(WORKSPACE, "ledger.json")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


def _load_ledger() -> Dict[str, Any]:
    _ensure_workspace()
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH) as f:
            return json.load(f)
    return {"transactions": [], "balances": {}, "created": datetime.now().isoformat()}


def _save_ledger(ledger: Dict[str, Any]):
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=2)


def crypto_price(symbol: str = "BTC") -> Dict[str, Any]:
    """Get current crypto price via public API."""
    try:
        r = subprocess.run(
            ["curl", "-s", f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd,eur&include_24hr_change=true"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(r.stdout)
        return {"symbol": symbol, "data": data, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        # Try alternative
        try:
            symbol_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "DOGE": "dogecoin"}
            coin_id = symbol_map.get(symbol.upper(), symbol.lower())
            r = subprocess.run(
                ["curl", "-s", f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"],
                capture_output=True, text=True, timeout=15
            )
            data = json.loads(r.stdout)
            return {"symbol": symbol, "data": data, "timestamp": datetime.now().isoformat()}
        except Exception as e2:
            return {"symbol": symbol, "error": str(e2)}


def record_transaction(amount: float, currency: str, description: str,
                       tx_type: str = "income", category: str = "general") -> Dict[str, Any]:
    """Record a financial transaction in the ledger."""
    ledger = _load_ledger()

    tx = {
        "id": len(ledger["transactions"]) + 1,
        "amount": amount,
        "currency": currency,
        "description": description,
        "type": tx_type,
        "category": category,
        "timestamp": datetime.now().isoformat(),
    }

    ledger["transactions"].append(tx)

    # Update balance
    key = currency.upper()
    if key not in ledger["balances"]:
        ledger["balances"][key] = 0
    if tx_type == "income":
        ledger["balances"][key] += amount
    else:
        ledger["balances"][key] -= amount

    _save_ledger(ledger)
    return {"transaction": tx, "new_balance": {key: ledger["balances"][key]}}


def financial_report(period: str = "all") -> Dict[str, Any]:
    """Generate financial report from ledger."""
    ledger = _load_ledger()

    report = {
        "period": period,
        "generated": datetime.now().isoformat(),
        "balances": ledger["balances"],
        "total_transactions": len(ledger["transactions"]),
        "income": sum(t["amount"] for t in ledger["transactions"] if t["type"] == "income"),
        "expenses": sum(t["amount"] for t in ledger["transactions"] if t["type"] == "expense"),
        "by_category": {},
    }

    for tx in ledger["transactions"]:
        cat = tx.get("category", "general")
        if cat not in report["by_category"]:
            report["by_category"][cat] = {"income": 0, "expense": 0, "count": 0}
        report["by_category"][cat][tx["type"]] = report["by_category"][cat].get(tx["type"], 0) + tx["amount"]
        report["by_category"][cat]["count"] += 1

    report["net"] = report["income"] - report["expenses"]
    return report


def trading_analysis(symbol: str, action: str = "analyze") -> Dict[str, Any]:
    """Analyze a trading opportunity. Does NOT execute trades automatically."""
    result = {
        "symbol": symbol,
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "analysis": {},
    }

    # Get current price
    price_data = crypto_price(symbol)
    result["current_price"] = price_data

    result["analysis"] = {
        "recommendation": "Requires manual review — Ouroboros provides analysis, creator confirms trades",
        "factors": [
            "Check 24h change percentage",
            "Review volume trends",
            "Check market sentiment",
            "Review support/resistance levels",
            "Consider portfolio allocation",
        ],
        "risk_note": "Never invest more than you can afford to lose. Crypto is volatile.",
    }

    return result


def revenue_scan(business_type: str = "digital") -> Dict[str, Any]:
    """Scan for revenue opportunities based on business type."""
    opportunities = {
        "digital": [
            {"type": "SaaS", "effort": "high", "potential": "$1K-$100K/mo", "description": "Build and sell software as a service"},
            {"type": "Freelancing", "effort": "medium", "potential": "$500-$10K/mo", "description": "Offer skills on platforms like Upwork, Fiverr"},
            {"type": "Digital Products", "effort": "medium", "potential": "$100-$50K/mo", "description": "Courses, ebooks, templates, tools"},
            {"type": "Affiliate Marketing", "effort": "low", "potential": "$100-$5K/mo", "description": "Promote products for commission"},
            {"type": "Content Monetization", "effort": "medium", "potential": "$100-$10K/mo", "description": "YouTube, blog, newsletter with ads/sponsors"},
        ],
        "service": [
            {"type": "Consulting", "effort": "medium", "potential": "$1K-$20K/mo", "description": "Expert advice in your field"},
            {"type": "Agency", "effort": "high", "potential": "$5K-$100K/mo", "description": "Offer services at scale with a team"},
            {"type": "Coaching", "effort": "medium", "potential": "$500-$10K/mo", "description": "1-on-1 or group coaching programs"},
        ],
        "crypto": [
            {"type": "Trading", "effort": "high", "potential": "Variable", "description": "Active trading (high risk)"},
            {"type": "Staking", "effort": "low", "potential": "3-15% APY", "description": "Stake tokens for passive yield"},
            {"type": "DeFi Yield", "effort": "medium", "potential": "5-30% APY", "description": "Liquidity provision, farming"},
        ],
    }

    return {
        "business_type": business_type,
        "opportunities": opportunities.get(business_type, opportunities["digital"]),
        "timestamp": datetime.now().isoformat(),
    }


def _raw_tools() -> list:
    return [
        {
            "name": "crypto_price",
            "description": "Get current cryptocurrency price (BTC, ETH, SOL, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "default": "BTC"},
                },
                "required": ["symbol"],
            },
            "function": crypto_price,
        },
        {
            "name": "record_transaction",
            "description": "Record a financial transaction (income or expense) in the ledger.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "description": {"type": "string"},
                    "tx_type": {"type": "string", "enum": ["income", "expense"], "default": "income"},
                    "category": {"type": "string", "default": "general"},
                },
                "required": ["amount", "currency", "description"],
            },
            "function": record_transaction,
        },
        {
            "name": "financial_report",
            "description": "Generate financial report from the transaction ledger.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "default": "all"},
                },
            },
            "function": financial_report,
        },
        {
            "name": "trading_analysis",
            "description": "Analyze a crypto trading opportunity. Provides analysis, does not auto-execute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "action": {"type": "string", "default": "analyze"},
                },
                "required": ["symbol"],
            },
            "function": trading_analysis,
        },
        {
            "name": "revenue_scan",
            "description": "Scan for revenue opportunities by business type (digital, service, crypto).",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_type": {"type": "string", "enum": ["digital", "service", "crypto"], "default": "digital"},
                },
            },
            "function": revenue_scan,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

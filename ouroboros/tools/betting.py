"""
Ouroboros — Betting & sports odds tools.

Sports odds (The Odds API free tier), arbitrage calculator, bet analyzer,
bankroll management, expected value calculator.
"""

from __future__ import annotations

import json
import logging
import math
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_betting")
BANKROLL_PATH = os.path.join(WORKSPACE, "bankroll.json")

# The Odds API free tier — 500 requests/month
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
ODDS_BASE = "https://api.the-odds-api.com/v4"


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


def _curl_json(url: str, timeout: int = 15) -> Any:
    r = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(timeout), url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    return json.loads(r.stdout)


def _load_bankroll() -> Dict[str, Any]:
    _ensure_workspace()
    if os.path.exists(BANKROLL_PATH):
        with open(BANKROLL_PATH) as f:
            return json.load(f)
    return {
        "balance": 0, "initial": 0, "bets": [],
        "wins": 0, "losses": 0, "pushes": 0,
        "created": datetime.now().isoformat(),
    }


def _save_bankroll(br: Dict[str, Any]):
    _ensure_workspace()
    with open(BANKROLL_PATH, "w") as f:
        json.dump(br, f, indent=2)


# ── Odds conversion helpers ───────────────────────────────────────────────

def _american_to_decimal(american: float) -> float:
    if american > 0:
        return 1 + american / 100
    else:
        return 1 + 100 / abs(american)


def _decimal_to_implied_prob(decimal_odds: float) -> float:
    return 1 / decimal_odds if decimal_odds > 0 else 0


def _american_to_implied_prob(american: float) -> float:
    return _decimal_to_implied_prob(_american_to_decimal(american))


# ── Sports Odds ────────────────────────────────────────────────────────────

def sports_odds(sport: str = "americanfootball_nfl", regions: str = "us",
                markets: str = "h2h") -> Dict[str, Any]:
    """Get live sports odds from The Odds API."""
    if not ODDS_API_KEY:
        return {
            "error": "ODDS_API_KEY not set. Get a free key at https://the-odds-api.com",
            "tip": "Set env var ODDS_API_KEY to enable live odds.",
            "available_sports": [
                "americanfootball_nfl", "americanfootball_ncaaf",
                "basketball_nba", "basketball_ncaab",
                "baseball_mlb", "icehockey_nhl",
                "soccer_epl", "soccer_usa_mls",
                "mma_mixed_martial_arts", "boxing_boxing",
            ],
        }

    url = (
        f"{ODDS_BASE}/sports/{sport}/odds"
        f"?apiKey={ODDS_API_KEY}&regions={regions}&markets={markets}"
        f"&oddsFormat=american"
    )
    try:
        data = _curl_json(url)
        if isinstance(data, dict) and "message" in data:
            return {"error": data["message"]}

        events = []
        for event in data[:20]:  # Limit to 20 events
            bookmakers = []
            for bm in event.get("bookmakers", [])[:5]:
                outcomes = []
                for market in bm.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        outcomes.append({
                            "name": outcome["name"],
                            "price": outcome["price"],
                            "implied_prob": round(_american_to_implied_prob(outcome["price"]) * 100, 1),
                        })
                bookmakers.append({"name": bm["title"], "outcomes": outcomes})
            events.append({
                "id": event.get("id"),
                "home": event.get("home_team"),
                "away": event.get("away_team"),
                "commence": event.get("commence_time"),
                "bookmakers": bookmakers,
            })
        return {"sport": sport, "events": events, "count": len(events)}
    except Exception as e:
        return {"error": str(e)}


def available_sports() -> Dict[str, Any]:
    """List available sports for odds lookup."""
    if not ODDS_API_KEY:
        return {
            "sports": [
                {"key": "americanfootball_nfl", "title": "NFL"},
                {"key": "americanfootball_ncaaf", "title": "NCAAF"},
                {"key": "basketball_nba", "title": "NBA"},
                {"key": "basketball_ncaab", "title": "NCAAB"},
                {"key": "baseball_mlb", "title": "MLB"},
                {"key": "icehockey_nhl", "title": "NHL"},
                {"key": "soccer_epl", "title": "EPL"},
                {"key": "soccer_usa_mls", "title": "MLS"},
                {"key": "mma_mixed_martial_arts", "title": "MMA"},
            ],
            "note": "Set ODDS_API_KEY for live odds data",
        }
    url = f"{ODDS_BASE}/sports?apiKey={ODDS_API_KEY}"
    try:
        data = _curl_json(url)
        sports = [{"key": s["key"], "title": s["title"], "active": s["active"]} for s in data if s.get("active")]
        return {"sports": sports, "count": len(sports)}
    except Exception as e:
        return {"error": str(e)}


# ── Arbitrage Calculator ──────────────────────────────────────────────────

def arbitrage_calculator(odds: List[float], stake: float = 100.0,
                         odds_format: str = "american") -> Dict[str, Any]:
    """
    Calculate arbitrage opportunity from a list of odds (one per outcome).
    E.g. odds=[150, -200] for a 2-way market.
    """
    if len(odds) < 2:
        return {"error": "Need at least 2 odds values (one per outcome)"}

    if odds_format == "american":
        decimal_odds = [_american_to_decimal(o) for o in odds]
    else:
        decimal_odds = odds

    implied_probs = [1 / d for d in decimal_odds]
    total_implied = sum(implied_probs)
    margin = total_implied - 1

    is_arb = total_implied < 1.0
    profit_pct = round((1 / total_implied - 1) * 100, 2) if is_arb else 0

    stakes = []
    payouts = []
    for i, d in enumerate(decimal_odds):
        individual_stake = round(stake * (implied_probs[i] / total_implied), 2)
        payout = round(individual_stake * d, 2)
        stakes.append(individual_stake)
        payouts.append(payout)

    return {
        "is_arbitrage": is_arb,
        "margin": round(margin * 100, 2),
        "profit_pct": profit_pct,
        "total_stake": stake,
        "guaranteed_profit": round(min(payouts) - stake, 2) if is_arb else 0,
        "outcomes": [
            {
                "odds_american": odds[i] if odds_format == "american" else None,
                "odds_decimal": round(decimal_odds[i], 3),
                "implied_prob": round(implied_probs[i] * 100, 1),
                "stake": stakes[i],
                "payout": payouts[i],
            }
            for i in range(len(odds))
        ],
    }


# ── Bet Analyzer / EV Calculator ─────────────────────────────────────────

def expected_value(odds: float, win_probability: float, stake: float = 100.0,
                   odds_format: str = "american") -> Dict[str, Any]:
    """
    Calculate expected value of a bet.
    odds: the offered odds
    win_probability: your estimated probability of winning (0-1)
    """
    if odds_format == "american":
        decimal_odds = _american_to_decimal(odds)
    else:
        decimal_odds = odds

    implied_prob = 1 / decimal_odds
    profit_if_win = stake * (decimal_odds - 1)
    loss_if_lose = stake

    ev = (win_probability * profit_if_win) - ((1 - win_probability) * loss_if_lose)
    roi = ev / stake * 100

    edge = win_probability - implied_prob

    return {
        "odds": odds,
        "odds_decimal": round(decimal_odds, 3),
        "implied_probability": round(implied_prob * 100, 1),
        "your_probability": round(win_probability * 100, 1),
        "edge": round(edge * 100, 1),
        "stake": stake,
        "profit_if_win": round(profit_if_win, 2),
        "expected_value": round(ev, 2),
        "roi_pct": round(roi, 2),
        "verdict": "+EV (good bet)" if ev > 0 else "-EV (bad bet)",
        "kelly_fraction": round(edge / (decimal_odds - 1), 4) if decimal_odds > 1 and edge > 0 else 0,
    }


def parlay_calculator(legs: List[Dict[str, Any]], stake: float = 100.0) -> Dict[str, Any]:
    """
    Calculate parlay payout and implied probability.
    legs: list of {odds: number, odds_format: "american"|"decimal"}
    """
    if len(legs) < 2:
        return {"error": "Need at least 2 legs for a parlay"}

    combined_decimal = 1.0
    implied_probs = []
    for leg in legs:
        odds = leg.get("odds", 0)
        fmt = leg.get("odds_format", "american")
        if fmt == "american":
            d = _american_to_decimal(odds)
        else:
            d = odds
        combined_decimal *= d
        implied_probs.append(1 / d)

    combined_prob = 1.0
    for p in implied_probs:
        combined_prob *= p

    payout = stake * combined_decimal
    profit = payout - stake

    return {
        "legs": len(legs),
        "combined_decimal_odds": round(combined_decimal, 3),
        "combined_implied_prob": round(combined_prob * 100, 2),
        "stake": stake,
        "potential_payout": round(payout, 2),
        "potential_profit": round(profit, 2),
    }


# ── Bankroll Management ──────────────────────────────────────────────────

def bankroll_manage(action: str, amount: float = 0, description: str = "",
                    odds: float = 0, result: str = "") -> Dict[str, Any]:
    """
    Manage betting bankroll.
    action: 'deposit', 'withdraw', 'bet', 'settle', 'status'
    """
    br = _load_bankroll()

    if action == "deposit":
        br["balance"] += amount
        br["initial"] += amount
        br["bets"].append({
            "type": "deposit", "amount": amount,
            "description": description, "timestamp": datetime.now().isoformat(),
        })
        _save_bankroll(br)
        return {"action": "deposit", "amount": amount, "balance": br["balance"]}

    elif action == "withdraw":
        if amount > br["balance"]:
            return {"error": "Insufficient balance", "balance": br["balance"]}
        br["balance"] -= amount
        br["bets"].append({
            "type": "withdraw", "amount": amount,
            "description": description, "timestamp": datetime.now().isoformat(),
        })
        _save_bankroll(br)
        return {"action": "withdraw", "amount": amount, "balance": br["balance"]}

    elif action == "bet":
        if amount > br["balance"]:
            return {"error": "Insufficient balance", "balance": br["balance"]}
        br["balance"] -= amount
        bet_id = len([b for b in br["bets"] if b["type"] == "bet"]) + 1
        br["bets"].append({
            "type": "bet", "id": bet_id, "amount": amount,
            "odds": odds, "description": description,
            "status": "pending", "timestamp": datetime.now().isoformat(),
        })
        _save_bankroll(br)
        return {"action": "bet", "bet_id": bet_id, "amount": amount, "balance": br["balance"]}

    elif action == "settle":
        # Find latest pending bet or by description
        pending = [b for b in br["bets"] if b.get("type") == "bet" and b.get("status") == "pending"]
        if not pending:
            return {"error": "No pending bets to settle"}
        bet = pending[-1]
        bet["status"] = result

        if result == "win":
            decimal_odds = _american_to_decimal(bet["odds"]) if bet["odds"] else 2.0
            winnings = bet["amount"] * decimal_odds
            br["balance"] += winnings
            br["wins"] += 1
            _save_bankroll(br)
            return {"result": "win", "winnings": round(winnings, 2), "balance": br["balance"]}
        elif result == "push":
            br["balance"] += bet["amount"]
            br["pushes"] += 1
            _save_bankroll(br)
            return {"result": "push", "refund": bet["amount"], "balance": br["balance"]}
        else:
            br["losses"] += 1
            _save_bankroll(br)
            return {"result": "loss", "lost": bet["amount"], "balance": br["balance"]}

    elif action == "status":
        total_bets = br["wins"] + br["losses"] + br["pushes"]
        win_rate = (br["wins"] / total_bets * 100) if total_bets else 0
        roi = ((br["balance"] - br["initial"]) / br["initial"] * 100) if br["initial"] else 0
        pending = len([b for b in br["bets"] if b.get("type") == "bet" and b.get("status") == "pending"])
        return {
            "balance": br["balance"],
            "initial_deposit": br["initial"],
            "profit_loss": round(br["balance"] - br["initial"], 2),
            "roi_pct": round(roi, 2),
            "total_bets": total_bets,
            "wins": br["wins"],
            "losses": br["losses"],
            "pushes": br["pushes"],
            "win_rate": round(win_rate, 1),
            "pending_bets": pending,
        }

    return {"error": f"Unknown action: {action}"}


def kelly_criterion(odds: float, win_probability: float,
                    bankroll: float = 0, fraction: float = 0.25,
                    odds_format: str = "american") -> Dict[str, Any]:
    """
    Calculate optimal bet size using Kelly Criterion.
    fraction: Kelly fraction (0.25 = quarter Kelly for safety)
    """
    if odds_format == "american":
        decimal_odds = _american_to_decimal(odds)
    else:
        decimal_odds = odds

    b = decimal_odds - 1  # net odds
    p = win_probability
    q = 1 - p

    full_kelly = (b * p - q) / b if b > 0 else 0
    adjusted_kelly = full_kelly * fraction

    if bankroll <= 0:
        br = _load_bankroll()
        bankroll = br.get("balance", 0)

    suggested_bet = max(0, round(bankroll * adjusted_kelly, 2))

    return {
        "odds": odds,
        "odds_decimal": round(decimal_odds, 3),
        "win_probability": round(p * 100, 1),
        "full_kelly_pct": round(full_kelly * 100, 2),
        "adjusted_kelly_pct": round(adjusted_kelly * 100, 2),
        "kelly_fraction_used": fraction,
        "bankroll": bankroll,
        "suggested_bet": suggested_bet,
        "edge": round((p - 1 / decimal_odds) * 100, 1),
        "verdict": "Positive edge" if full_kelly > 0 else "No edge — do not bet",
    }


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "sports_odds",
            "description": "Get live sports odds from The Odds API. Supports NFL, NBA, MLB, NHL, EPL, MMA, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sport": {"type": "string", "default": "americanfootball_nfl",
                              "description": "Sport key (e.g. basketball_nba, baseball_mlb)"},
                    "regions": {"type": "string", "default": "us"},
                    "markets": {"type": "string", "default": "h2h", "description": "h2h, spreads, totals"},
                },
            },
            "function": sports_odds,
        },
        {
            "name": "available_sports",
            "description": "List available sports for odds lookup.",
            "parameters": {"type": "object", "properties": {}},
            "function": available_sports,
        },
        {
            "name": "arbitrage_calculator",
            "description": "Calculate arbitrage opportunity from odds across bookmakers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "odds": {"type": "array", "items": {"type": "number"},
                             "description": "List of odds, one per outcome"},
                    "stake": {"type": "number", "default": 100},
                    "odds_format": {"type": "string", "enum": ["american", "decimal"], "default": "american"},
                },
                "required": ["odds"],
            },
            "function": arbitrage_calculator,
        },
        {
            "name": "expected_value",
            "description": "Calculate expected value of a bet given odds and your estimated win probability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "odds": {"type": "number", "description": "Offered odds"},
                    "win_probability": {"type": "number", "description": "Your estimated win prob (0-1)"},
                    "stake": {"type": "number", "default": 100},
                    "odds_format": {"type": "string", "enum": ["american", "decimal"], "default": "american"},
                },
                "required": ["odds", "win_probability"],
            },
            "function": expected_value,
        },
        {
            "name": "parlay_calculator",
            "description": "Calculate parlay payout and implied probability from multiple legs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "legs": {"type": "array", "items": {"type": "object"},
                             "description": "List of {odds, odds_format} objects"},
                    "stake": {"type": "number", "default": 100},
                },
                "required": ["legs"],
            },
            "function": parlay_calculator,
        },
        {
            "name": "bankroll_manage",
            "description": "Manage betting bankroll: deposit, withdraw, place bets, settle results, check status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["deposit", "withdraw", "bet", "settle", "status"]},
                    "amount": {"type": "number", "default": 0},
                    "description": {"type": "string", "default": ""},
                    "odds": {"type": "number", "default": 0, "description": "American odds for the bet"},
                    "result": {"type": "string", "enum": ["win", "loss", "push"], "description": "For settle action"},
                },
                "required": ["action"],
            },
            "function": bankroll_manage,
        },
        {
            "name": "kelly_criterion",
            "description": "Calculate optimal bet size using Kelly Criterion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "odds": {"type": "number"},
                    "win_probability": {"type": "number", "description": "Estimated win probability (0-1)"},
                    "bankroll": {"type": "number", "default": 0, "description": "Override bankroll (0 = use tracked)"},
                    "fraction": {"type": "number", "default": 0.25, "description": "Kelly fraction (0.25 = quarter Kelly)"},
                    "odds_format": {"type": "string", "enum": ["american", "decimal"], "default": "american"},
                },
                "required": ["odds", "win_probability"],
            },
            "function": kelly_criterion,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

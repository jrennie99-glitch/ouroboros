"""
Ouroboros — Trading tools.

Crypto prices (CoinGecko), stock quotes (Yahoo Finance), technical analysis,
portfolio tracking, trading signals.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_trading")
PORTFOLIO_PATH = os.path.join(WORKSPACE, "portfolio.json")

COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "DOGE": "dogecoin",
    "ADA": "cardano", "XRP": "ripple", "DOT": "polkadot", "AVAX": "avalanche-2",
    "MATIC": "matic-network", "LINK": "chainlink", "UNI": "uniswap",
    "ATOM": "cosmos", "LTC": "litecoin", "NEAR": "near", "APT": "aptos",
    "ARB": "arbitrum", "OP": "optimism", "SUI": "sui", "SEI": "sei-network",
    "TIA": "celestia", "PEPE": "pepe", "SHIB": "shiba-inu", "BNB": "binancecoin",
}


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


def _load_portfolio() -> Dict[str, Any]:
    _ensure_workspace()
    if os.path.exists(PORTFOLIO_PATH):
        with open(PORTFOLIO_PATH) as f:
            return json.load(f)
    return {"holdings": {}, "history": [], "created": datetime.now().isoformat()}


def _save_portfolio(portfolio: Dict[str, Any]):
    _ensure_workspace()
    with open(PORTFOLIO_PATH, "w") as f:
        json.dump(portfolio, f, indent=2)


def _curl_json(url: str, timeout: int = 15) -> Any:
    """Fetch JSON from URL using curl."""
    r = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(timeout), url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    return json.loads(r.stdout)


# ── Crypto Prices ──────────────────────────────────────────────────────────

def crypto_price_detailed(symbol: str = "BTC", vs_currency: str = "usd") -> Dict[str, Any]:
    """Get detailed crypto price with market data from CoinGecko."""
    coin_id = COINGECKO_IDS.get(symbol.upper(), symbol.lower())
    url = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        f"?localization=false&tickers=false&community_data=false&developer_data=false"
    )
    try:
        data = _curl_json(url)
        market = data.get("market_data", {})
        return {
            "symbol": symbol.upper(),
            "name": data.get("name", symbol),
            "price_usd": market.get("current_price", {}).get("usd"),
            "price_requested": market.get("current_price", {}).get(vs_currency),
            "market_cap_usd": market.get("market_cap", {}).get("usd"),
            "volume_24h_usd": market.get("total_volume", {}).get("usd"),
            "change_24h_pct": market.get("price_change_percentage_24h"),
            "change_7d_pct": market.get("price_change_percentage_7d"),
            "change_30d_pct": market.get("price_change_percentage_30d"),
            "ath_usd": market.get("ath", {}).get("usd"),
            "ath_change_pct": market.get("ath_change_percentage", {}).get("usd"),
            "circulating_supply": market.get("circulating_supply"),
            "total_supply": market.get("total_supply"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def crypto_market_overview(limit: int = 10) -> Dict[str, Any]:
    """Get top cryptocurrencies by market cap."""
    url = (
        f"https://api.coingecko.com/api/v3/coins/markets"
        f"?vs_currency=usd&order=market_cap_desc&per_page={min(limit, 50)}&page=1"
        f"&sparkline=false&price_change_percentage=24h,7d"
    )
    try:
        data = _curl_json(url)
        coins = []
        for c in data:
            coins.append({
                "rank": c.get("market_cap_rank"),
                "symbol": c.get("symbol", "").upper(),
                "name": c.get("name"),
                "price_usd": c.get("current_price"),
                "change_24h_pct": c.get("price_change_percentage_24h"),
                "change_7d_pct": c.get("price_change_percentage_7d_in_currency"),
                "market_cap": c.get("market_cap"),
                "volume_24h": c.get("total_volume"),
            })
        return {"coins": coins, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"error": str(e)}


# ── Stock Quotes ───────────────────────────────────────────────────────────

def stock_quote(ticker: str = "AAPL") -> Dict[str, Any]:
    """Get stock quote from Yahoo Finance."""
    ticker = ticker.upper().strip()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
    try:
        data = _curl_json(url)
        result = data["chart"]["result"][0]
        meta = result["meta"]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        current = meta.get("regularMarketPrice", closes[-1] if closes else None)
        prev_close = meta.get("previousClose") or (closes[-2] if len(closes) >= 2 else None)
        change = (current - prev_close) if current and prev_close else None
        change_pct = (change / prev_close * 100) if change and prev_close else None
        return {
            "ticker": ticker,
            "price": current,
            "previous_close": prev_close,
            "change": round(change, 2) if change else None,
            "change_pct": round(change_pct, 2) if change_pct else None,
            "currency": meta.get("currency", "USD"),
            "exchange": meta.get("exchangeName"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def stock_history(ticker: str = "AAPL", period: str = "1mo", interval: str = "1d") -> Dict[str, Any]:
    """Get historical stock data from Yahoo Finance."""
    ticker = ticker.upper().strip()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={period}"
    try:
        data = _curl_json(url)
        result = data["chart"]["result"][0]
        timestamps = result["timestamps"]
        quote = result["indicators"]["quote"][0]
        points = []
        for i in range(len(timestamps)):
            points.append({
                "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                "open": quote["open"][i],
                "high": quote["high"][i],
                "low": quote["low"][i],
                "close": quote["close"][i],
                "volume": quote["volume"][i],
            })
        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data_points": len(points),
            "prices": points,
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ── Technical Analysis ─────────────────────────────────────────────────────

def _compute_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    gains = gains[-(period):]
    losses = losses[-(period):]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _compute_ema(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def _compute_macd(closes: List[float]) -> Dict[str, Any]:
    if len(closes) < 26:
        return {"error": "Need at least 26 data points for MACD"}
    ema12 = _compute_ema(closes, 12)
    ema26 = _compute_ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal_line = _compute_ema(macd_line, 9)
    histogram = [macd_line[i] - signal_line[i] for i in range(len(closes))]
    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(histogram[-1], 4),
        "trend": "bullish" if histogram[-1] > 0 else "bearish",
        "crossover": "bullish" if histogram[-1] > 0 and histogram[-2] <= 0 else
                     ("bearish" if histogram[-1] < 0 and histogram[-2] >= 0 else "none"),
    }


def _compute_sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return round(sum(values[-period:]) / period, 4)


def _compute_bollinger(closes: List[float], period: int = 20, num_std: float = 2.0) -> Dict[str, Any]:
    if len(closes) < period:
        return {"error": f"Need at least {period} data points"}
    window = closes[-period:]
    sma = sum(window) / period
    std = statistics.stdev(window)
    return {
        "upper": round(sma + num_std * std, 4),
        "middle": round(sma, 4),
        "lower": round(sma - num_std * std, 4),
        "bandwidth": round((num_std * 2 * std) / sma * 100, 4),
    }


def technical_analysis(symbol: str, asset_type: str = "crypto", period: str = "3mo") -> Dict[str, Any]:
    """Run technical analysis on a stock or crypto."""
    try:
        if asset_type == "crypto":
            coin_id = COINGECKO_IDS.get(symbol.upper(), symbol.lower())
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=90"
            data = _curl_json(url)
            closes = [p[1] for p in data.get("prices", [])]
        else:
            ticker = symbol.upper()
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={period}"
            data = _curl_json(url)
            result = data["chart"]["result"][0]
            closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]

        if len(closes) < 2:
            return {"symbol": symbol, "error": "Insufficient data"}

        rsi = _compute_rsi(closes)
        macd = _compute_macd(closes)
        bollinger = _compute_bollinger(closes)

        # Signals
        signals = []
        if rsi is not None:
            if rsi > 70:
                signals.append("RSI overbought (>70) — potential sell signal")
            elif rsi < 30:
                signals.append("RSI oversold (<30) — potential buy signal")
            else:
                signals.append(f"RSI neutral ({rsi})")

        if isinstance(macd, dict) and "crossover" in macd:
            if macd["crossover"] == "bullish":
                signals.append("MACD bullish crossover — buy signal")
            elif macd["crossover"] == "bearish":
                signals.append("MACD bearish crossover — sell signal")

        current = closes[-1]
        if isinstance(bollinger, dict) and "upper" in bollinger:
            if current > bollinger["upper"]:
                signals.append("Price above upper Bollinger Band — overbought")
            elif current < bollinger["lower"]:
                signals.append("Price below lower Bollinger Band — oversold")

        sma20 = _compute_sma(closes, 20)
        sma50 = _compute_sma(closes, 50)
        sma200 = _compute_sma(closes, 200)

        if sma20 and sma50:
            if sma20 > sma50:
                signals.append("SMA20 > SMA50 — short-term bullish")
            else:
                signals.append("SMA20 < SMA50 — short-term bearish")

        return {
            "symbol": symbol.upper(),
            "current_price": round(current, 4),
            "rsi_14": rsi,
            "macd": macd,
            "bollinger_bands": bollinger,
            "moving_averages": {
                "sma_20": sma20,
                "sma_50": sma50,
                "sma_200": sma200,
            },
            "signals": signals,
            "data_points": len(closes),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


# ── Portfolio Tracker ──────────────────────────────────────────────────────

def portfolio_update(action: str, symbol: str, quantity: float,
                     price: float, asset_type: str = "crypto") -> Dict[str, Any]:
    """Add/remove holdings to portfolio tracker."""
    portfolio = _load_portfolio()
    key = symbol.upper()

    if action == "buy":
        if key not in portfolio["holdings"]:
            portfolio["holdings"][key] = {"quantity": 0, "avg_cost": 0, "type": asset_type}
        h = portfolio["holdings"][key]
        total_cost = h["avg_cost"] * h["quantity"] + price * quantity
        h["quantity"] += quantity
        h["avg_cost"] = total_cost / h["quantity"] if h["quantity"] else 0
    elif action == "sell":
        if key in portfolio["holdings"]:
            portfolio["holdings"][key]["quantity"] -= quantity
            if portfolio["holdings"][key]["quantity"] <= 0:
                del portfolio["holdings"][key]
    else:
        return {"error": f"Unknown action: {action}. Use 'buy' or 'sell'."}

    portfolio["history"].append({
        "action": action, "symbol": key, "quantity": quantity,
        "price": price, "timestamp": datetime.now().isoformat(),
    })
    _save_portfolio(portfolio)
    return {"portfolio": portfolio["holdings"], "action_recorded": action}


def portfolio_view() -> Dict[str, Any]:
    """View current portfolio with live prices."""
    portfolio = _load_portfolio()
    if not portfolio["holdings"]:
        return {"message": "Portfolio is empty", "holdings": {}}

    total_value = 0
    total_cost = 0
    enriched = {}

    for sym, h in portfolio["holdings"].items():
        try:
            if h.get("type") == "crypto":
                coin_id = COINGECKO_IDS.get(sym, sym.lower())
                data = _curl_json(
                    f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                )
                price = list(data.values())[0].get("usd", 0) if data else 0
            else:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
                data = _curl_json(url)
                price = data["chart"]["result"][0]["meta"].get("regularMarketPrice", 0)

            value = price * h["quantity"]
            cost = h["avg_cost"] * h["quantity"]
            pnl = value - cost
            total_value += value
            total_cost += cost

            enriched[sym] = {
                "quantity": h["quantity"],
                "avg_cost": round(h["avg_cost"], 4),
                "current_price": round(price, 4),
                "value_usd": round(value, 2),
                "pnl_usd": round(pnl, 2),
                "pnl_pct": round(pnl / cost * 100, 2) if cost else 0,
            }
        except Exception:
            enriched[sym] = {
                "quantity": h["quantity"],
                "avg_cost": h["avg_cost"],
                "error": "Price fetch failed",
            }

    return {
        "holdings": enriched,
        "total_value_usd": round(total_value, 2),
        "total_cost_usd": round(total_cost, 2),
        "total_pnl_usd": round(total_value - total_cost, 2),
        "total_pnl_pct": round((total_value - total_cost) / total_cost * 100, 2) if total_cost else 0,
        "timestamp": datetime.now().isoformat(),
    }


# ── Trading Signals ────────────────────────────────────────────────────────

def trading_signal(symbol: str, asset_type: str = "crypto") -> Dict[str, Any]:
    """Generate composite trading signal for a symbol."""
    ta = technical_analysis(symbol, asset_type)
    if "error" in ta:
        return ta

    bullish = 0
    bearish = 0
    for sig in ta.get("signals", []):
        if "buy" in sig.lower() or "bullish" in sig.lower():
            bullish += 1
        elif "sell" in sig.lower() or "bearish" in sig.lower():
            bearish += 1

    rsi = ta.get("rsi_14")
    if rsi and rsi < 30:
        bullish += 2
    elif rsi and rsi > 70:
        bearish += 2
    elif rsi and rsi < 40:
        bullish += 1
    elif rsi and rsi > 60:
        bearish += 1

    total = bullish + bearish
    if total == 0:
        score = 50
    else:
        score = round(bullish / total * 100)

    if score >= 70:
        signal = "STRONG BUY"
    elif score >= 55:
        signal = "BUY"
    elif score >= 45:
        signal = "HOLD"
    elif score >= 30:
        signal = "SELL"
    else:
        signal = "STRONG SELL"

    return {
        "symbol": symbol.upper(),
        "signal": signal,
        "score": score,
        "bullish_indicators": bullish,
        "bearish_indicators": bearish,
        "rsi": rsi,
        "macd_trend": ta.get("macd", {}).get("trend"),
        "details": ta.get("signals", []),
        "disclaimer": "Not financial advice. Do your own research.",
        "timestamp": datetime.now().isoformat(),
    }


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "crypto_price_detailed",
            "description": "Get detailed crypto price with market data (market cap, volume, 24h/7d/30d change, ATH, supply) from CoinGecko.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Crypto symbol like BTC, ETH, SOL"},
                    "vs_currency": {"type": "string", "default": "usd"},
                },
                "required": ["symbol"],
            },
            "function": crypto_price_detailed,
        },
        {
            "name": "crypto_market_overview",
            "description": "Get top cryptocurrencies by market cap with prices and 24h changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10, "description": "Number of coins (max 50)"},
                },
            },
            "function": crypto_market_overview,
        },
        {
            "name": "stock_quote",
            "description": "Get stock quote (price, change, volume) from Yahoo Finance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker like AAPL, TSLA, MSFT"},
                },
                "required": ["ticker"],
            },
            "function": stock_quote,
        },
        {
            "name": "stock_history",
            "description": "Get historical stock price data (OHLCV).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "period": {"type": "string", "default": "1mo", "description": "1d,5d,1mo,3mo,6mo,1y,2y,5y,max"},
                    "interval": {"type": "string", "default": "1d", "description": "1m,5m,15m,1h,1d,1wk,1mo"},
                },
                "required": ["ticker"],
            },
            "function": stock_history,
        },
        {
            "name": "technical_analysis",
            "description": "Run technical analysis (RSI, MACD, Bollinger Bands, SMAs) on a stock or crypto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbol (BTC, AAPL, etc)"},
                    "asset_type": {"type": "string", "enum": ["crypto", "stock"], "default": "crypto"},
                    "period": {"type": "string", "default": "3mo"},
                },
                "required": ["symbol"],
            },
            "function": technical_analysis,
        },
        {
            "name": "portfolio_update",
            "description": "Add or remove a position from the portfolio tracker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["buy", "sell"]},
                    "symbol": {"type": "string"},
                    "quantity": {"type": "number"},
                    "price": {"type": "number", "description": "Price per unit at time of trade"},
                    "asset_type": {"type": "string", "enum": ["crypto", "stock"], "default": "crypto"},
                },
                "required": ["action", "symbol", "quantity", "price"],
            },
            "function": portfolio_update,
        },
        {
            "name": "portfolio_view",
            "description": "View current portfolio with live prices, P&L, and total value.",
            "parameters": {"type": "object", "properties": {}},
            "function": portfolio_view,
        },
        {
            "name": "trading_signal",
            "description": "Generate a composite trading signal (STRONG BUY/BUY/HOLD/SELL/STRONG SELL) based on technical indicators.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "asset_type": {"type": "string", "enum": ["crypto", "stock"], "default": "crypto"},
                },
                "required": ["symbol"],
            },
            "function": trading_signal,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

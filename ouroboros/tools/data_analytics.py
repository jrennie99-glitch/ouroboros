"""
Ouroboros — Data analytics tools.

CSV/JSON analyzer, report generator, trend analyzer, sentiment analysis,
data visualization descriptions.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import os
import re
import statistics
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_analytics")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


# ── CSV/JSON Analyzer ─────────────────────────────────────────────────────

def data_analyzer(data: str = "", file_path: str = "",
                  data_format: str = "auto") -> Dict[str, Any]:
    """Analyze CSV or JSON data — compute stats, detect types, find patterns."""
    # Load data
    if file_path and os.path.exists(file_path):
        with open(file_path) as f:
            data = f.read()

    if not data:
        return {"error": "No data provided. Pass 'data' string or 'file_path'."}

    # Detect format
    if data_format == "auto":
        stripped = data.strip()
        if stripped.startswith(("{", "[")):
            data_format = "json"
        else:
            data_format = "csv"

    # Parse
    if data_format == "json":
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            records = [parsed]
        elif isinstance(parsed, list):
            records = parsed
        else:
            return {"error": "JSON must be an object or array of objects"}
    else:
        reader = csv.DictReader(io.StringIO(data))
        records = list(reader)

    if not records:
        return {"error": "No records found in data"}

    # Analyze
    columns = list(records[0].keys()) if records else []
    analysis = {
        "format": data_format,
        "total_records": len(records),
        "columns": len(columns),
        "column_names": columns,
        "column_analysis": {},
    }

    for col in columns:
        values = [r.get(col) for r in records if r.get(col) is not None and str(r.get(col)).strip() != ""]
        col_info = {
            "non_null_count": len(values),
            "null_count": len(records) - len(values),
            "unique_count": len(set(str(v) for v in values)),
        }

        # Try numeric analysis
        numeric_vals = []
        for v in values:
            try:
                numeric_vals.append(float(str(v).replace(",", "")))
            except (ValueError, TypeError):
                pass

        if len(numeric_vals) > len(values) * 0.5 and numeric_vals:
            col_info["type"] = "numeric"
            col_info["min"] = round(min(numeric_vals), 4)
            col_info["max"] = round(max(numeric_vals), 4)
            col_info["mean"] = round(statistics.mean(numeric_vals), 4)
            col_info["median"] = round(statistics.median(numeric_vals), 4)
            if len(numeric_vals) > 1:
                col_info["std_dev"] = round(statistics.stdev(numeric_vals), 4)
            col_info["sum"] = round(sum(numeric_vals), 4)
        else:
            col_info["type"] = "categorical"
            str_vals = [str(v) for v in values]
            top_values = Counter(str_vals).most_common(10)
            col_info["top_values"] = [{"value": v, "count": c} for v, c in top_values]
            if str_vals:
                lengths = [len(s) for s in str_vals]
                col_info["avg_length"] = round(statistics.mean(lengths), 1)

        analysis["column_analysis"][col] = col_info

    # Detect potential issues
    issues = []
    for col, info in analysis["column_analysis"].items():
        if info["null_count"] > len(records) * 0.5:
            issues.append(f"Column '{col}' has >50% null values ({info['null_count']}/{len(records)})")
        if info["unique_count"] == 1:
            issues.append(f"Column '{col}' has only 1 unique value — consider removing")
        if info["unique_count"] == len(records) and info["type"] == "categorical":
            issues.append(f"Column '{col}' may be an ID column (all unique values)")

    analysis["data_quality_issues"] = issues

    return analysis


# ── Report Generator ─────────────────────────────────────────────────────

def report_generator(title: str, data: Dict[str, Any],
                     sections: List[str] = None,
                     format_type: str = "markdown") -> Dict[str, Any]:
    """Generate a formatted report from data."""
    if not sections:
        sections = ["summary", "key_metrics", "analysis", "recommendations"]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if format_type == "markdown":
        report = [f"# {title}", f"*Generated: {timestamp}*\n"]

        if "summary" in sections:
            report.append("## Executive Summary\n")
            if isinstance(data, dict):
                for key, value in list(data.items())[:5]:
                    if isinstance(value, (int, float)):
                        report.append(f"- **{key.replace('_', ' ').title()}**: {value:,.2f}" if isinstance(value, float) else f"- **{key.replace('_', ' ').title()}**: {value:,}")
                    elif isinstance(value, str):
                        report.append(f"- **{key.replace('_', ' ').title()}**: {value}")

        if "key_metrics" in sections:
            report.append("\n## Key Metrics\n")
            report.append("| Metric | Value |")
            report.append("|--------|-------|")
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (int, float, str)):
                        display = f"{value:,.2f}" if isinstance(value, float) else str(value)
                        report.append(f"| {key.replace('_', ' ').title()} | {display} |")

        if "analysis" in sections:
            report.append("\n## Detailed Analysis\n")
            report.append("*Analysis based on provided data points.*\n")
            if isinstance(data, dict):
                numeric_items = {k: v for k, v in data.items() if isinstance(v, (int, float))}
                if numeric_items:
                    values = list(numeric_items.values())
                    report.append(f"- Data points analyzed: {len(numeric_items)}")
                    if len(values) > 1:
                        report.append(f"- Range: {min(values):,.2f} to {max(values):,.2f}")
                        report.append(f"- Average: {statistics.mean(values):,.2f}")

        if "recommendations" in sections:
            report.append("\n## Recommendations\n")
            report.append("1. [Add actionable recommendations based on analysis]")
            report.append("2. [Consider trends and patterns identified]")
            report.append("3. [Suggest next steps for follow-up analysis]")

        content = "\n".join(report)

    elif format_type == "html":
        rows = ""
        if isinstance(data, dict):
            for k, v in data.items():
                rows += f"<tr><td>{k}</td><td>{v}</td></tr>\n"
        content = f"""<!DOCTYPE html>
<html><head><title>{title}</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}
th{{background:#f4f4f4}}</style></head>
<body><h1>{title}</h1><p>Generated: {timestamp}</p>
<table><tr><th>Metric</th><th>Value</th></tr>{rows}</table></body></html>"""

    else:
        content = json.dumps({"title": title, "generated": timestamp, "data": data}, indent=2, default=str)

    # Save report
    _ensure_workspace()
    ext = {"markdown": "md", "html": "html", "json": "json"}.get(format_type, "txt")
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    filepath = os.path.join(WORKSPACE, filename)
    with open(filepath, "w") as f:
        f.write(content)

    return {
        "title": title,
        "format": format_type,
        "file_path": filepath,
        "content_preview": content[:1000],
        "sections": sections,
    }


# ── Trend Analyzer ────────────────────────────────────────────────────────

def trend_analyzer(values: List[float], labels: List[str] = None,
                   period: str = "auto") -> Dict[str, Any]:
    """Analyze trends in a series of numeric values."""
    if not values or len(values) < 2:
        return {"error": "Need at least 2 values for trend analysis"}

    n = len(values)
    if not labels:
        labels = [str(i + 1) for i in range(n)]

    # Basic stats
    result = {
        "count": n,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "std_dev": round(statistics.stdev(values), 4) if n > 1 else 0,
    }

    # Linear regression (simple least squares)
    x = list(range(n))
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(values)
    numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator else 0
    intercept = y_mean - slope * x_mean

    # R-squared
    ss_res = sum((values[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
    ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot else 0

    result["trend"] = {
        "direction": "up" if slope > 0 else ("down" if slope < 0 else "flat"),
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 4),
        "strength": "strong" if abs(r_squared) > 0.7 else ("moderate" if abs(r_squared) > 0.3 else "weak"),
    }

    # Change analysis
    total_change = values[-1] - values[0]
    pct_change = (total_change / abs(values[0]) * 100) if values[0] != 0 else 0
    result["change"] = {
        "total": round(total_change, 4),
        "percentage": round(pct_change, 2),
        "first_value": values[0],
        "last_value": values[-1],
    }

    # Moving average (window = min(5, n//2))
    window = min(5, max(2, n // 2))
    ma = []
    for i in range(n - window + 1):
        ma.append(round(statistics.mean(values[i:i + window]), 4))
    result["moving_average"] = {"window": window, "values": ma}

    # Detect anomalies (values > 2 std devs from mean)
    if n > 2:
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        anomalies = []
        for i, v in enumerate(values):
            if abs(v - mean) > 2 * std:
                anomalies.append({
                    "index": i,
                    "label": labels[i] if i < len(labels) else str(i),
                    "value": v,
                    "z_score": round((v - mean) / std, 2),
                })
        result["anomalies"] = anomalies

    # Forecast next 3 values
    forecasts = []
    for i in range(1, 4):
        predicted = slope * (n - 1 + i) + intercept
        forecasts.append(round(predicted, 4))
    result["forecast_next_3"] = forecasts

    return result


# ── Sentiment Analysis ────────────────────────────────────────────────────

# Simple lexicon-based sentiment (no external dependencies)
POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "wonderful", "fantastic", "outstanding",
    "perfect", "love", "best", "happy", "awesome", "beautiful", "brilliant", "superb",
    "impressive", "incredible", "magnificent", "delightful", "pleasant", "positive",
    "success", "successful", "win", "winning", "recommend", "recommended", "enjoy",
    "enjoyed", "favorite", "thank", "thanks", "grateful", "glad", "pleased",
    "satisfied", "exceptional", "remarkable", "helpful", "useful", "valuable",
    "innovative", "efficient", "reliable", "comfortable", "exciting", "easy",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "horrible", "worst", "hate", "poor", "disappointing",
    "disappointed", "ugly", "boring", "annoying", "frustrating", "useless", "waste",
    "broken", "fail", "failed", "failure", "problem", "problems", "issue", "issues",
    "complain", "complaint", "angry", "upset", "unhappy", "difficult", "confusing",
    "slow", "expensive", "overpriced", "cheap", "rude", "unprofessional", "defective",
    "unreliable", "uncomfortable", "painful", "regret", "unfortunately", "worse",
    "lacking", "mediocre", "subpar", "inferior",
}

INTENSIFIERS = {"very", "extremely", "incredibly", "absolutely", "totally", "really", "highly", "super"}
NEGATORS = {"not", "no", "never", "neither", "nor", "hardly", "barely", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "won't", "wouldn't", "can't", "cannot", "shouldn't"}


def sentiment_analysis(text: str, detailed: bool = False) -> Dict[str, Any]:
    """Analyze sentiment of text using lexicon-based approach."""
    if not text:
        return {"error": "No text provided"}

    # Tokenize
    words = re.findall(r'\b\w+\b', text.lower())
    total_words = len(words)
    if total_words == 0:
        return {"error": "No analyzable words found"}

    pos_count = 0
    neg_count = 0
    pos_words_found = []
    neg_words_found = []
    intensity_multiplier = 1.0
    negate_next = False

    for i, word in enumerate(words):
        if word in INTENSIFIERS:
            intensity_multiplier = 1.5
            continue
        if word in NEGATORS:
            negate_next = True
            continue

        is_positive = word in POSITIVE_WORDS
        is_negative = word in NEGATIVE_WORDS

        if negate_next:
            is_positive, is_negative = is_negative, is_positive
            negate_next = False

        if is_positive:
            pos_count += intensity_multiplier
            pos_words_found.append(word)
        elif is_negative:
            neg_count += intensity_multiplier
            neg_words_found.append(word)

        intensity_multiplier = 1.0

    # Calculate score (-1 to 1)
    total_sentiment_words = pos_count + neg_count
    if total_sentiment_words == 0:
        score = 0.0
    else:
        score = (pos_count - neg_count) / total_sentiment_words

    # Classify
    if score > 0.25:
        label = "positive"
    elif score < -0.25:
        label = "negative"
    else:
        label = "neutral"

    confidence = min(abs(score) * 2, 1.0)

    result = {
        "text_length": len(text),
        "word_count": total_words,
        "sentiment": label,
        "score": round(score, 3),
        "confidence": round(confidence, 3),
        "positive_count": int(pos_count),
        "negative_count": int(neg_count),
    }

    if detailed:
        result["positive_words"] = pos_words_found
        result["negative_words"] = neg_words_found
        # Sentence-level breakdown
        sentences = re.split(r'[.!?]+', text)
        sentence_sentiments = []
        for sent in sentences:
            if sent.strip():
                s_result = sentiment_analysis(sent.strip())
                sentence_sentiments.append({
                    "text": sent.strip()[:100],
                    "sentiment": s_result.get("sentiment", "neutral"),
                    "score": s_result.get("score", 0),
                })
        result["sentence_breakdown"] = sentence_sentiments[:20]

    return result


# ── Data Visualization Descriptions ──────────────────────────────────────

def viz_description(data: Dict[str, Any], chart_type: str = "auto",
                    title: str = "") -> Dict[str, Any]:
    """Generate data visualization descriptions and chart recommendations."""
    if not data:
        return {"error": "No data provided"}

    # Analyze data to recommend chart type
    keys = list(data.keys()) if isinstance(data, dict) else []
    values = list(data.values()) if isinstance(data, dict) else data

    numeric_values = []
    categorical_keys = []
    for k, v in (data.items() if isinstance(data, dict) else enumerate(values)):
        if isinstance(v, (int, float)):
            numeric_values.append(v)
            categorical_keys.append(str(k))

    # Auto-detect best chart type
    if chart_type == "auto":
        n_categories = len(categorical_keys)
        if n_categories <= 5:
            chart_type = "pie"
        elif n_categories <= 20:
            chart_type = "bar"
        else:
            chart_type = "line"
        if all(isinstance(v, (int, float)) for v in values) and len(values) > 10:
            chart_type = "line"

    # Generate description and config
    chart_configs = {
        "bar": {
            "description": f"A bar chart showing {title or 'values by category'}. "
                          f"Highest value: {max(numeric_values):,.2f} ({categorical_keys[numeric_values.index(max(numeric_values))]}). "
                          f"Lowest value: {min(numeric_values):,.2f} ({categorical_keys[numeric_values.index(min(numeric_values))]})."
                          if numeric_values else "Bar chart with no numeric data.",
            "plotly_config": {
                "type": "bar",
                "x": categorical_keys,
                "y": numeric_values,
                "title": title,
            },
            "matplotlib_code": f"plt.bar({categorical_keys!r}, {numeric_values!r})\nplt.title('{title}')\nplt.xticks(rotation=45)",
        },
        "line": {
            "description": f"A line chart tracking {title or 'values over time'}. "
                          f"Range: {min(numeric_values):,.2f} to {max(numeric_values):,.2f}. "
                          f"Trend: {'upward' if numeric_values[-1] > numeric_values[0] else 'downward' if numeric_values[-1] < numeric_values[0] else 'flat'}."
                          if numeric_values else "Line chart with no numeric data.",
            "plotly_config": {
                "type": "scatter",
                "mode": "lines+markers",
                "x": categorical_keys,
                "y": numeric_values,
                "title": title,
            },
        },
        "pie": {
            "description": f"A pie chart showing distribution of {title or 'categories'}. "
                          f"Total: {sum(numeric_values):,.2f}. "
                          + (f"Largest segment: {categorical_keys[numeric_values.index(max(numeric_values))]} ({max(numeric_values)/sum(numeric_values)*100:.1f}%)."
                          if numeric_values and sum(numeric_values) > 0 else ""),
            "plotly_config": {
                "type": "pie",
                "labels": categorical_keys,
                "values": numeric_values,
                "title": title,
            },
        },
        "histogram": {
            "description": f"A histogram showing distribution of {title or 'values'}. "
                          f"Mean: {statistics.mean(numeric_values):,.2f}, "
                          f"Median: {statistics.median(numeric_values):,.2f}."
                          if numeric_values else "Histogram with no numeric data.",
        },
        "scatter": {
            "description": f"A scatter plot of {title or 'data points'}. "
                          f"{len(numeric_values)} data points plotted.",
        },
    }

    config = chart_configs.get(chart_type, chart_configs["bar"])

    return {
        "recommended_chart": chart_type,
        "title": title,
        "description": config.get("description", ""),
        "data_summary": {
            "categories": len(categorical_keys),
            "total": round(sum(numeric_values), 2) if numeric_values else 0,
            "mean": round(statistics.mean(numeric_values), 2) if numeric_values else 0,
        },
        "config": config.get("plotly_config", {}),
        "code_snippet": config.get("matplotlib_code", ""),
    }


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "data_analyzer",
            "description": "Analyze CSV or JSON data — compute statistics, detect types, find data quality issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Raw CSV or JSON string"},
                    "file_path": {"type": "string", "description": "Path to CSV/JSON file (alternative to data)"},
                    "data_format": {"type": "string", "enum": ["auto", "csv", "json"], "default": "auto"},
                },
            },
            "function": data_analyzer,
        },
        {
            "name": "report_generator",
            "description": "Generate formatted reports (Markdown, HTML, JSON) from data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "data": {"type": "object", "description": "Key-value data to report on"},
                    "sections": {"type": "array", "items": {"type": "string"},
                                 "description": "Sections to include: summary, key_metrics, analysis, recommendations"},
                    "format_type": {"type": "string", "enum": ["markdown", "html", "json"], "default": "markdown"},
                },
                "required": ["title", "data"],
            },
            "function": report_generator,
        },
        {
            "name": "trend_analyzer",
            "description": "Analyze trends in numeric data: regression, moving averages, anomaly detection, forecasting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "values": {"type": "array", "items": {"type": "number"}, "description": "List of numeric values"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Labels for each value"},
                    "period": {"type": "string", "default": "auto"},
                },
                "required": ["values"],
            },
            "function": trend_analyzer,
        },
        {
            "name": "sentiment_analysis",
            "description": "Analyze sentiment of text (positive/negative/neutral) with confidence scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "detailed": {"type": "boolean", "default": False, "description": "Include word-level and sentence-level breakdown"},
                },
                "required": ["text"],
            },
            "function": sentiment_analysis,
        },
        {
            "name": "viz_description",
            "description": "Generate data visualization descriptions and chart recommendations with config.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "object", "description": "Key-value data to visualize"},
                    "chart_type": {"type": "string", "enum": ["auto", "bar", "line", "pie", "histogram", "scatter"], "default": "auto"},
                    "title": {"type": "string", "default": ""},
                },
                "required": ["data"],
            },
            "function": viz_description,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

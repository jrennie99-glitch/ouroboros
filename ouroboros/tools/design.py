"""UI/UX Pro Max Design Intelligence: website design, styling, branding, logos.

Integrates the UI/UX Pro Max skill system into Ouroboros for professional
website building with 161 reasoning rules, 67 styles, 161 color palettes,
57 font pairings, and 13 tech stack guidelines.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import pathlib
import subprocess
from typing import Any, Dict, List, Optional

from ouroboros.tools.registry import ToolContext, ToolEntry

log = logging.getLogger(__name__)

UIUX_DIR = pathlib.Path("/Users/godmode/Documents/ui-ux-pro-max-skill")
DATA_DIR = UIUX_DIR / "src" / "ui-ux-pro-max" / "data"
SCRIPTS_DIR = UIUX_DIR / "src" / "ui-ux-pro-max" / "scripts"


def _read_csv(filename: str, limit: int = 50) -> List[Dict]:
    """Read a CSV file from the data directory."""
    f = DATA_DIR / filename
    if not f.exists():
        return []
    try:
        rows = []
        with open(f, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                rows.append(dict(row))
        return rows
    except Exception as e:
        log.warning("Failed to read %s: %s", filename, e)
        return []


def _search_csv(filename: str, query: str, fields: List[str] = None, limit: int = 10) -> List[Dict]:
    """Search a CSV file for matching rows."""
    f = DATA_DIR / filename
    if not f.exists():
        return []
    query_lower = query.lower()
    results = []
    try:
        with open(f, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                search_fields = fields or list(row.keys())
                text = " ".join(str(row.get(k, "")) for k in search_fields).lower()
                if query_lower in text:
                    results.append(dict(row))
                    if len(results) >= limit:
                        break
    except Exception:
        pass
    return results


def _design_status(ctx: ToolContext, **kwargs) -> str:
    """Get status of the UI/UX Pro Max design system."""
    result = {
        "path": str(UIUX_DIR),
        "installed": UIUX_DIR.exists(),
        "data_dir": str(DATA_DIR),
        "data_available": DATA_DIR.exists(),
    }
    if DATA_DIR.exists():
        csvs = list(DATA_DIR.glob("*.csv"))
        result["databases"] = {f.stem: sum(1 for _ in open(f)) - 1 for f in csvs}
        result["total_records"] = sum(result["databases"].values())
        stacks_dir = DATA_DIR / "stacks"
        if stacks_dir.exists():
            result["tech_stacks"] = [f.stem for f in stacks_dir.glob("*.csv")]
    return json.dumps(result, indent=2)


def _design_system_generate(ctx: ToolContext, product: str, **kwargs) -> str:
    """Generate a complete design system for a product/website type.

    Uses 161 reasoning rules to match the product to the optimal:
    - UI style + pattern
    - Color palette
    - Typography (font pairing)
    - Effects and interactions
    - Anti-patterns to avoid
    """
    # Search reasoning rules for the product
    reasoning = _search_csv("ui-reasoning.csv", product, limit=3)
    products = _search_csv("products.csv", product, limit=3)

    if not reasoning and not products:
        # Broader search
        words = product.split()
        for word in words:
            reasoning = _search_csv("ui-reasoning.csv", word, limit=3)
            products = _search_csv("products.csv", word, limit=3)
            if reasoning or products:
                break

    # Get recommended style
    style_name = ""
    if reasoning:
        style_name = reasoning[0].get("style", reasoning[0].get("recommended_style", ""))
    elif products:
        style_name = products[0].get("style", products[0].get("recommended_style", ""))

    styles = _search_csv("styles.csv", style_name or product, limit=3) if style_name else []

    # Get color palette
    colors = _search_csv("colors.csv", product, limit=3)
    if not colors and style_name:
        colors = _search_csv("colors.csv", style_name, limit=3)

    # Get typography
    typography = _search_csv("typography.csv", product, limit=3)
    if not typography:
        typography = _read_csv("typography.csv", limit=5)

    # Get UX guidelines
    ux = _search_csv("ux-guidelines.csv", product, limit=5)

    design_system = {
        "product": product,
        "reasoning": reasoning[:2],
        "recommended_style": styles[:2],
        "color_palette": colors[:2],
        "typography": typography[:3],
        "ux_guidelines": ux[:5],
        "instruction": (
            f"Build a website for '{product}' using the design system above. "
            f"Apply the recommended style, colors, and typography. "
            f"Follow the UX guidelines. Use repo_write_commit to save files."
        ),
    }
    return json.dumps(design_system, indent=2)


def _design_search_styles(ctx: ToolContext, query: str, **kwargs) -> str:
    """Search 67+ UI styles by keyword, category, or use case."""
    results = _search_csv("styles.csv", query, limit=10)
    return json.dumps({"query": query, "results": results, "count": len(results)}, indent=2)


def _design_search_colors(ctx: ToolContext, query: str, **kwargs) -> str:
    """Search 161 color palettes by industry, mood, or style."""
    results = _search_csv("colors.csv", query, limit=10)
    return json.dumps({"query": query, "results": results, "count": len(results)}, indent=2)


def _design_search_fonts(ctx: ToolContext, query: str = "", **kwargs) -> str:
    """Search font pairings. Empty query returns popular pairings."""
    if query:
        results = _search_csv("typography.csv", query, limit=10)
    else:
        results = _read_csv("typography.csv", limit=15)
    return json.dumps({"query": query or "all", "results": results, "count": len(results)}, indent=2)


def _design_stack_guide(ctx: ToolContext, stack: str = "react", **kwargs) -> str:
    """Get stack-specific design guidelines (React, Next.js, Vue, Svelte, Flutter, etc.)."""
    stack_file = DATA_DIR / "stacks" / f"{stack}.csv"
    if not stack_file.exists():
        # Try fuzzy match
        stacks_dir = DATA_DIR / "stacks"
        if stacks_dir.exists():
            available = [f.stem for f in stacks_dir.glob("*.csv")]
            matches = [s for s in available if stack.lower() in s.lower()]
            if matches:
                stack_file = stacks_dir / f"{matches[0]}.csv"
            else:
                return json.dumps({"error": f"Stack '{stack}' not found", "available": available})

    rows = []
    try:
        with open(stack_file, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(dict(row))
    except Exception:
        pass

    return json.dumps({"stack": stack, "guidelines": rows[:30], "count": len(rows)}, indent=2)


def _design_ux_guidelines(ctx: ToolContext, query: str = "", **kwargs) -> str:
    """Get UX guidelines. Search by topic or get all 99 guidelines."""
    if query:
        results = _search_csv("ux-guidelines.csv", query, limit=15)
    else:
        results = _read_csv("ux-guidelines.csv", limit=20)
    return json.dumps({"query": query or "all", "results": results, "count": len(results)}, indent=2)


def _design_charts(ctx: ToolContext, query: str = "", **kwargs) -> str:
    """Get chart type recommendations for data visualization."""
    if query:
        results = _search_csv("charts.csv", query, limit=10)
    else:
        results = _read_csv("charts.csv", limit=25)
    return json.dumps({"query": query or "all", "results": results, "count": len(results)}, indent=2)


def _design_landing_patterns(ctx: ToolContext, query: str = "", **kwargs) -> str:
    """Get landing page design patterns for conversion optimization."""
    if query:
        results = _search_csv("landing.csv", query, limit=10)
    else:
        results = _read_csv("landing.csv", limit=35)
    return json.dumps({"query": query or "all", "results": results, "count": len(results)}, indent=2)


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("design_status", {
            "name": "design_status",
            "description": "Get status of UI/UX Pro Max design system. Shows available databases, styles, and stacks.",
            "parameters": {"type": "object", "properties": {}},
        }, _design_status),
        ToolEntry("design_system_generate", {
            "name": "design_system_generate",
            "description": "Generate a complete design system for a product/website: style, colors, typography, UX guidelines. Uses 161 reasoning rules.",
            "parameters": {"type": "object", "properties": {
                "product": {"type": "string", "description": "Product/website type (e.g. 'saas dashboard', 'ecommerce', 'portfolio', 'fintech app')"},
            }, "required": ["product"]},
        }, _design_system_generate),
        ToolEntry("design_search_styles", {
            "name": "design_search_styles",
            "description": "Search 67+ UI styles by keyword, category, or use case.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Style keyword (e.g. 'minimal', 'brutalist', 'glassmorphism', 'dashboard')"},
            }, "required": ["query"]},
        }, _design_search_styles),
        ToolEntry("design_search_colors", {
            "name": "design_search_colors",
            "description": "Search 161 color palettes by industry, mood, or style.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Color search (e.g. 'fintech', 'dark', 'luxury', 'healthcare')"},
            }, "required": ["query"]},
        }, _design_search_colors),
        ToolEntry("design_search_fonts", {
            "name": "design_search_fonts",
            "description": "Search font pairings from 1900+ Google Fonts database.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Font search (e.g. 'modern', 'serif', 'tech', 'elegant'). Empty for popular."},
            }},
        }, _design_search_fonts),
        ToolEntry("design_stack_guide", {
            "name": "design_stack_guide",
            "description": "Get stack-specific design guidelines: React, Next.js, Vue, Svelte, Flutter, SwiftUI, etc.",
            "parameters": {"type": "object", "properties": {
                "stack": {"type": "string", "description": "Tech stack: react, nextjs, vue, nuxtjs, svelte, flutter, swiftui, react-native, shadcn, html-tailwind, jetpack-compose"},
            }, "required": ["stack"]},
        }, _design_stack_guide),
        ToolEntry("design_ux_guidelines", {
            "name": "design_ux_guidelines",
            "description": "Get UX guidelines (99 rules). Search by topic or browse all.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "UX topic (e.g. 'navigation', 'forms', 'accessibility', 'mobile')"},
            }},
        }, _design_ux_guidelines),
        ToolEntry("design_charts", {
            "name": "design_charts",
            "description": "Get chart type recommendations for data visualization (25 types).",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Chart search (e.g. 'comparison', 'time series', 'distribution')"},
            }},
        }, _design_charts),
        ToolEntry("design_landing", {
            "name": "design_landing",
            "description": "Get landing page design patterns for conversion optimization.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Landing page search (e.g. 'hero', 'CTA', 'pricing', 'testimonial')"},
            }},
        }, _design_landing_patterns),
    ]

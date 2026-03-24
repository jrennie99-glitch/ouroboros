"""
Adapter to convert simple tool dicts (name, description, parameters, function)
into ToolEntry objects that the Ouroboros registry expects.

Usage in any tool module:
    from ouroboros.tools._adapter import adapt_tools
    def get_tools():
        return adapt_tools(_my_raw_tools())
"""

from __future__ import annotations
import json
from typing import Any, Dict, List
from ouroboros.tools.registry import ToolEntry


def adapt_tools(raw_tools: List[Dict[str, Any]]) -> List[ToolEntry]:
    """Convert list of dicts with 'name', 'description', 'parameters', 'function'
    into ToolEntry objects compatible with the Ouroboros registry."""
    entries = []
    for t in raw_tools:
        fn = t["function"]
        name = t["name"]
        schema = {
            "name": name,
            "description": t.get("description", ""),
            "parameters": t.get("parameters", {"type": "object", "properties": {}}),
        }

        # Wrap the raw function to accept (ctx, **kwargs) signature
        def make_handler(raw_fn):
            def handler(ctx, **kwargs):
                return json.dumps(raw_fn(**kwargs), default=str)
            return handler

        entries.append(ToolEntry(
            name=name,
            schema=schema,
            handler=make_handler(fn),
        ))
    return entries

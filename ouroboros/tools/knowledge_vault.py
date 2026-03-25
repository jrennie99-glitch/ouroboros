"""
Knowledge Vault — Obsidian-compatible "second brain" for Ouroboros.

All notes are markdown files with YAML frontmatter, stored in a vault directory.
Supports wiki links [[Like This]], tags (#tag), daily notes, templates,
Maps of Content, Kanban boards, backlinks, and knowledge graph generation.

Vault location: /app/local_state/vault/ (fallback: /tmp/ouroboros_vault/)
"""

from __future__ import annotations

import datetime
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from ouroboros.tools.registry import ToolEntry, ToolContext

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vault path resolution
# ---------------------------------------------------------------------------

_PRIMARY_VAULT = Path("/app/local_state/vault")
_FALLBACK_VAULT = Path("/tmp/ouroboros_vault")


def _vault_root() -> Path:
    """Return the vault root, creating it if needed."""
    if _PRIMARY_VAULT.parent.exists():
        _PRIMARY_VAULT.mkdir(parents=True, exist_ok=True)
        return _PRIMARY_VAULT
    _FALLBACK_VAULT.mkdir(parents=True, exist_ok=True)
    return _FALLBACK_VAULT


def _resolve_note_path(title: str) -> Path:
    """Resolve a note title (possibly with folder) to an absolute path inside the vault."""
    root = _vault_root()
    # Normalise: strip .md if caller included it
    title = title.strip().rstrip("/")
    if title.endswith(".md"):
        title = title[:-3]
    # Prevent path traversal
    parts = Path(title).parts
    safe_parts = [p for p in parts if p not in ("..", ".")]
    path = root.joinpath(*safe_parts).with_suffix(".md")
    # Ensure it resolves inside vault
    if not str(path.resolve()).startswith(str(root.resolve())):
        raise ValueError(f"Path traversal detected: {title}")
    return path


# ---------------------------------------------------------------------------
# YAML frontmatter helpers
# ---------------------------------------------------------------------------

def _build_frontmatter(title: str, tags: List[str] | None = None,
                       aliases: List[str] | None = None,
                       extra: Dict[str, Any] | None = None) -> str:
    """Build YAML frontmatter block."""
    lines = ["---"]
    lines.append(f"title: \"{title}\"")
    lines.append(f"date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if tags:
        lines.append("tags:")
        for t in tags:
            lines.append(f"  - {t.lstrip('#').strip()}")
    if aliases:
        lines.append("aliases:")
        for a in aliases:
            lines.append(f"  - \"{a}\"")
    if extra:
        for k, v in extra.items():
            if isinstance(v, list):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _parse_frontmatter(text: str) -> tuple[Dict[str, Any], str]:
    """Split text into (frontmatter_dict, body). Returns ({}, text) if no frontmatter."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm_block = text[3:end].strip()
    body = text[end + 3:].lstrip("\n")
    # Simple YAML parse (good enough for our frontmatter)
    meta: Dict[str, Any] = {}
    current_key = None
    current_list: list | None = None
    for line in fm_block.split("\n"):
        if line.startswith("  - "):
            val = line.strip().lstrip("- ").strip().strip('"')
            if current_list is not None:
                current_list.append(val)
        elif ": " in line or line.endswith(":"):
            if current_key and current_list is not None:
                meta[current_key] = current_list
                current_list = None
            if ": " in line:
                k, v = line.split(": ", 1)
                k = k.strip()
                v = v.strip().strip('"')
                if v == "":
                    current_key = k
                    current_list = []
                else:
                    meta[k] = v
                    current_key = k
                    current_list = None
            else:
                current_key = line.rstrip(":").strip()
                current_list = []
    if current_key and current_list is not None:
        meta[current_key] = current_list
    return meta, body


def _extract_tags_from_text(text: str) -> List[str]:
    """Extract #tags from body text and frontmatter."""
    meta, body = _parse_frontmatter(text)
    tags = set()
    # From frontmatter
    fm_tags = meta.get("tags", [])
    if isinstance(fm_tags, list):
        tags.update(fm_tags)
    elif isinstance(fm_tags, str):
        tags.add(fm_tags)
    # From body
    for m in re.finditer(r'(?<!\w)#([a-zA-Z0-9_/-]+)', body):
        tags.add(m.group(1))
    return sorted(tags)


def _extract_wiki_links(text: str) -> List[str]:
    """Extract [[wiki link]] targets from text."""
    return list(dict.fromkeys(re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', text)))


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _vault_create(ctx: ToolContext, *, title: str, content: str = "",
                  tags: Optional[List[str]] = None, links: Optional[List[str]] = None,
                  aliases: Optional[List[str]] = None) -> str:
    path = _resolve_note_path(title)
    if path.exists():
        return f"Note '{title}' already exists. Use vault_edit to modify it."
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = _build_frontmatter(title.split("/")[-1], tags=tags, aliases=aliases)
    body = content
    if links:
        body += "\n\n## Related\n" + "\n".join(f"- [[{l}]]" for l in links)
    path.write_text(fm + "\n" + body + "\n", encoding="utf-8")
    return f"Created note: {title} ({path.relative_to(_vault_root())})"


def _vault_read(ctx: ToolContext, *, title: str) -> str:
    path = _resolve_note_path(title)
    if not path.exists():
        return f"Note '{title}' not found."
    return path.read_text(encoding="utf-8")


def _vault_edit(ctx: ToolContext, *, title: str, content: str,
                mode: str = "append") -> str:
    path = _resolve_note_path(title)
    if not path.exists():
        return f"Note '{title}' not found. Use vault_create first."
    existing = path.read_text(encoding="utf-8")
    if mode == "append":
        new = existing.rstrip("\n") + "\n\n" + content + "\n"
    elif mode == "prepend":
        meta, body = _parse_frontmatter(existing)
        fm_end = existing.find("---", 3)
        if fm_end != -1 and existing.startswith("---"):
            header = existing[:fm_end + 3]
            new = header + "\n\n" + content + "\n\n" + body
        else:
            new = content + "\n\n" + existing
    elif mode == "replace":
        meta, _ = _parse_frontmatter(existing)
        if meta:
            fm_end = existing.find("---", 3)
            header = existing[:fm_end + 3]
            new = header + "\n\n" + content + "\n"
        else:
            new = content + "\n"
    else:
        return f"Invalid mode '{mode}'. Use append, prepend, or replace."
    path.write_text(new, encoding="utf-8")
    return f"Updated note: {title} (mode={mode})"


def _vault_delete(ctx: ToolContext, *, title: str) -> str:
    path = _resolve_note_path(title)
    if not path.exists():
        return f"Note '{title}' not found."
    path.unlink()
    # Clean up empty parent dirs
    parent = path.parent
    root = _vault_root()
    while parent != root and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent
    return f"Deleted note: {title}"


def _vault_list(ctx: ToolContext, *, folder: str = "", tag: str = "") -> str:
    root = _vault_root()
    search_root = root / folder if folder else root
    if not search_root.exists():
        return f"Folder '{folder}' not found."
    notes = sorted(search_root.rglob("*.md"))
    if not notes:
        return "No notes found."
    results = []
    for n in notes:
        rel = n.relative_to(root)
        if tag:
            text = n.read_text(encoding="utf-8")
            tags = _extract_tags_from_text(text)
            if tag.lstrip("#") not in tags:
                continue
        meta, _ = _parse_frontmatter(n.read_text(encoding="utf-8"))
        title = meta.get("title", n.stem)
        results.append(f"- {rel}  (title: {title})")
    if not results:
        return f"No notes found matching filter (folder={folder!r}, tag={tag!r})."
    return f"## Vault Notes ({len(results)})\n\n" + "\n".join(results)


def _vault_search(ctx: ToolContext, *, query: str, max_results: int = 10) -> str:
    root = _vault_root()
    query_lower = query.lower()
    hits = []
    for note_path in sorted(root.rglob("*.md")):
        text = note_path.read_text(encoding="utf-8")
        if query_lower in text.lower():
            # Find context snippet
            idx = text.lower().index(query_lower)
            start = max(0, idx - 60)
            end = min(len(text), idx + len(query) + 60)
            snippet = text[start:end].replace("\n", " ").strip()
            rel = note_path.relative_to(root)
            hits.append(f"- **{rel}**: ...{snippet}...")
            if len(hits) >= max_results:
                break
    if not hits:
        return f"No results for '{query}'."
    return f"## Search: {query} ({len(hits)} results)\n\n" + "\n".join(hits)


def _vault_tag_search(ctx: ToolContext, *, tag: str) -> str:
    root = _vault_root()
    tag_clean = tag.lstrip("#").strip()
    hits = []
    for note_path in sorted(root.rglob("*.md")):
        text = note_path.read_text(encoding="utf-8")
        tags = _extract_tags_from_text(text)
        if tag_clean in tags:
            rel = note_path.relative_to(root)
            hits.append(f"- [[{note_path.stem}]] ({rel})")
    if not hits:
        return f"No notes tagged #{tag_clean}."
    return f"## Notes tagged #{tag_clean} ({len(hits)})\n\n" + "\n".join(hits)


def _vault_backlinks(ctx: ToolContext, *, title: str) -> str:
    root = _vault_root()
    hits = []
    for note_path in sorted(root.rglob("*.md")):
        text = note_path.read_text(encoding="utf-8")
        links = _extract_wiki_links(text)
        if title in links or title.split("/")[-1] in links:
            rel = note_path.relative_to(root)
            hits.append(f"- [[{note_path.stem}]] ({rel})")
    if not hits:
        return f"No backlinks to '{title}'."
    return f"## Backlinks to {title} ({len(hits)})\n\n" + "\n".join(hits)


def _vault_graph(ctx: ToolContext) -> str:
    root = _vault_root()
    adjacency: Dict[str, List[str]] = {}
    for note_path in sorted(root.rglob("*.md")):
        name = note_path.stem
        text = note_path.read_text(encoding="utf-8")
        links = _extract_wiki_links(text)
        adjacency[name] = links
    if not adjacency:
        return "Vault is empty — no graph to generate."
    lines = ["## Knowledge Graph (Adjacency List)\n"]
    for node, edges in sorted(adjacency.items()):
        if edges:
            lines.append(f"- **{node}** -> {', '.join(f'[[{e}]]' for e in edges)}")
        else:
            lines.append(f"- **{node}** (no outgoing links)")
    total_edges = sum(len(e) for e in adjacency.values())
    lines.append(f"\n**Nodes:** {len(adjacency)} | **Edges:** {total_edges}")
    return "\n".join(lines)


def _vault_daily_note(ctx: ToolContext, *, content: str = "",
                      date: str = "") -> str:
    if not date:
        date = datetime.date.today().isoformat()
    title = f"daily/{date}"
    path = _resolve_note_path(title)
    if path.exists():
        if content:
            existing = path.read_text(encoding="utf-8")
            timestamp = datetime.datetime.now().strftime("%H:%M")
            path.write_text(
                existing.rstrip("\n") + f"\n\n### {timestamp}\n{content}\n",
                encoding="utf-8",
            )
            return f"Appended to daily note: {date}"
        return path.read_text(encoding="utf-8")
    # Create new daily note
    path.parent.mkdir(parents=True, exist_ok=True)
    weekday = datetime.date.fromisoformat(date).strftime("%A")
    fm = _build_frontmatter(date, tags=["daily-note"], extra={"day": weekday})
    body = f"# {date} ({weekday})\n"
    if content:
        timestamp = datetime.datetime.now().strftime("%H:%M")
        body += f"\n### {timestamp}\n{content}\n"
    path.write_text(fm + "\n" + body, encoding="utf-8")
    return f"Created daily note: {date}"


def _vault_weekly_summary(ctx: ToolContext, *, week_start: str = "") -> str:
    if not week_start:
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        week_start = monday.isoformat()
    start_date = datetime.date.fromisoformat(week_start)
    root = _vault_root()
    daily_dir = root / "daily"
    entries = []
    for i in range(7):
        day = start_date + datetime.timedelta(days=i)
        day_path = daily_dir / f"{day.isoformat()}.md"
        if day_path.exists():
            text = day_path.read_text(encoding="utf-8")
            _, body = _parse_frontmatter(text)
            entries.append(f"### {day.isoformat()} ({day.strftime('%A')})\n{body.strip()}")
    if not entries:
        return f"No daily notes found for week starting {week_start}."
    summary_title = f"weekly/{week_start}-summary"
    path = _resolve_note_path(summary_title)
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = _build_frontmatter(f"Week of {week_start}", tags=["weekly-summary"])
    body = f"# Weekly Summary: {week_start}\n\n" + "\n\n".join(entries) + "\n"
    path.write_text(fm + "\n" + body, encoding="utf-8")
    return f"Generated weekly summary: {summary_title}\n\n{body}"


_TEMPLATES = {
    "meeting": "# Meeting: {title}\n\n**Date:** {date}\n**Attendees:**\n\n## Agenda\n\n- \n\n## Notes\n\n\n\n## Action Items\n\n- [ ] \n",
    "project": "# Project: {title}\n\n## Overview\n\n\n\n## Goals\n\n- \n\n## Milestones\n\n- [ ] \n\n## Notes\n\n\n\n## Related\n\n",
    "research": "# Research: {title}\n\n## Question\n\n\n\n## Sources\n\n- \n\n## Findings\n\n\n\n## Conclusions\n\n\n\n## Open Questions\n\n- \n",
    "decision": "# Decision: {title}\n\n**Date:** {date}\n**Status:** decided\n\n## Context\n\n\n\n## Options Considered\n\n1. \n2. \n3. \n\n## Decision\n\n\n\n## Rationale\n\n\n\n## Consequences\n\n- \n",
    "retrospective": "# Retrospective: {title}\n\n**Date:** {date}\n\n## What Went Well\n\n- \n\n## What Could Improve\n\n- \n\n## Action Items\n\n- [ ] \n",
}


def _vault_templates(ctx: ToolContext, *, action: str = "list",
                     template_name: str = "", title: str = "",
                     folder: str = "") -> str:
    if action == "list":
        return "## Available Templates\n\n" + "\n".join(
            f"- **{k}**" for k in sorted(_TEMPLATES)
        )
    if action == "use":
        if template_name not in _TEMPLATES:
            return f"Unknown template '{template_name}'. Available: {', '.join(sorted(_TEMPLATES))}"
        if not title:
            return "Provide a title for the new note."
        date_str = datetime.date.today().isoformat()
        body = _TEMPLATES[template_name].format(title=title, date=date_str)
        note_title = f"{folder}/{title}" if folder else title
        path = _resolve_note_path(note_title)
        if path.exists():
            return f"Note '{note_title}' already exists."
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = _build_frontmatter(title, tags=[template_name, "from-template"])
        path.write_text(fm + "\n" + body, encoding="utf-8")
        return f"Created note from '{template_name}' template: {note_title}"
    return f"Invalid action '{action}'. Use 'list' or 'use'."


def _vault_moc(ctx: ToolContext, *, topic: str, note_titles: Optional[List[str]] = None,
               auto_discover: bool = False) -> str:
    moc_title = f"MOC-{topic}"
    path = _resolve_note_path(moc_title)
    root = _vault_root()
    linked: List[str] = []
    if auto_discover:
        topic_lower = topic.lower()
        for note_path in sorted(root.rglob("*.md")):
            if note_path.stem.startswith("MOC-"):
                continue
            text = note_path.read_text(encoding="utf-8")
            tags = _extract_tags_from_text(text)
            if (topic_lower in note_path.stem.lower()
                    or topic_lower in text.lower()[:500]
                    or topic_lower in [t.lower() for t in tags]):
                linked.append(note_path.stem)
    if note_titles:
        for t in note_titles:
            if t not in linked:
                linked.append(t)
    fm = _build_frontmatter(f"MOC: {topic}", tags=["moc", topic])
    body = f"# Map of Content: {topic}\n\n"
    if linked:
        body += "\n".join(f"- [[{n}]]" for n in sorted(linked)) + "\n"
    else:
        body += "(No notes linked yet. Add note_titles or use auto_discover.)\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fm + "\n" + body, encoding="utf-8")
    return f"{'Updated' if path.exists() else 'Created'} MOC: {moc_title} ({len(linked)} linked notes)"


def _vault_learn(ctx: ToolContext, *, fact: str, source: str = "",
                 context: str = "", confidence: str = "high",
                 tags: Optional[List[str]] = None) -> str:
    root = _vault_root()
    learn_dir = root / "learned"
    learn_dir.mkdir(parents=True, exist_ok=True)
    # Generate a slug from the fact
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', fact[:60]).strip('-').lower()
    if not slug:
        slug = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    path = learn_dir / f"{slug}.md"
    # If exists, make unique
    counter = 1
    while path.exists():
        path = learn_dir / f"{slug}-{counter}.md"
        counter += 1
    all_tags = list(tags or []) + ["learned"]
    fm = _build_frontmatter(fact[:80], tags=all_tags,
                            extra={"confidence": confidence, "source": f'"{source}"' if source else '""'})
    body = f"# {fact}\n\n"
    if context:
        body += f"## Context\n{context}\n\n"
    if source:
        body += f"## Source\n{source}\n\n"
    body += f"**Confidence:** {confidence}\n"
    path.write_text(fm + "\n" + body, encoding="utf-8")
    rel = path.relative_to(root)
    return f"Learned and stored: {rel}"


def _vault_recall(ctx: ToolContext, *, topic: str, max_results: int = 5) -> str:
    root = _vault_root()
    learn_dir = root / "learned"
    if not learn_dir.exists():
        return "No learned facts yet."
    topic_lower = topic.lower()
    hits = []
    for note_path in sorted(learn_dir.rglob("*.md")):
        text = note_path.read_text(encoding="utf-8")
        if topic_lower in text.lower():
            meta, body = _parse_frontmatter(text)
            title = meta.get("title", note_path.stem)
            confidence = meta.get("confidence", "unknown")
            source = meta.get("source", "").strip('"')
            hits.append(f"- **{title}** (confidence: {confidence}, source: {source})")
            if len(hits) >= max_results:
                break
    if not hits:
        return f"No learned facts about '{topic}'."
    return f"## Recall: {topic} ({len(hits)} results)\n\n" + "\n".join(hits)


def _vault_connect(ctx: ToolContext, *, title: str = "") -> str:
    root = _vault_root()
    # Build index of all notes: tags, links, words
    notes_data: Dict[str, Dict[str, Any]] = {}
    for note_path in sorted(root.rglob("*.md")):
        text = note_path.read_text(encoding="utf-8")
        name = note_path.stem
        notes_data[name] = {
            "tags": set(_extract_tags_from_text(text)),
            "links": set(_extract_wiki_links(text)),
            "words": set(re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())),
            "path": note_path,
        }
    if not notes_data:
        return "Vault is empty."

    targets = [title] if title else list(notes_data.keys())
    suggestions = []
    for src in targets:
        if src not in notes_data:
            continue
        src_data = notes_data[src]
        for other, other_data in notes_data.items():
            if other == src or other in src_data["links"]:
                continue
            # Score connection
            shared_tags = src_data["tags"] & other_data["tags"]
            shared_words = src_data["words"] & other_data["words"]
            score = len(shared_tags) * 3 + min(len(shared_words), 20)
            if score >= 3:
                reasons = []
                if shared_tags:
                    reasons.append(f"shared tags: {', '.join(sorted(shared_tags)[:5])}")
                if shared_words:
                    top_words = sorted(shared_words)[:5]
                    reasons.append(f"common terms: {', '.join(top_words)}")
                suggestions.append((score, src, other, reasons))

    suggestions.sort(key=lambda x: -x[0])
    if not suggestions:
        return "No new connections suggested."
    lines = ["## Suggested Connections\n"]
    for score, src, tgt, reasons in suggestions[:15]:
        reason_str = "; ".join(reasons)
        lines.append(f"- **{src}** <-> **[[{tgt}]]** (score: {score}) — {reason_str}")
    return "\n".join(lines)


def _vault_export(ctx: ToolContext) -> str:
    root = _vault_root()
    all_notes = list(root.rglob("*.md"))
    if not all_notes:
        return "Vault is empty."
    tag_counts: Dict[str, int] = defaultdict(int)
    link_counts: Dict[str, int] = defaultdict(int)
    linked_to: Dict[str, int] = defaultdict(int)
    all_links: set = set()
    recent: List[tuple] = []
    for note_path in all_notes:
        text = note_path.read_text(encoding="utf-8")
        name = note_path.stem
        tags = _extract_tags_from_text(text)
        links = _extract_wiki_links(text)
        for t in tags:
            tag_counts[t] += 1
        link_counts[name] = len(links)
        for l in links:
            linked_to[l] += 1
            all_links.add(l)
        mtime = note_path.stat().st_mtime
        recent.append((mtime, name))

    # Orphans: notes that link to nothing and nobody links to
    all_names = {n.stem for n in all_notes}
    orphans = [n for n in all_names if link_counts.get(n, 0) == 0 and linked_to.get(n, 0) == 0]

    # Most connected
    connection_score = {n: link_counts.get(n, 0) + linked_to.get(n, 0) for n in all_names}
    most_connected = sorted(connection_score.items(), key=lambda x: -x[1])[:10]

    # Top tags
    top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:15]

    # Recent activity
    recent.sort(key=lambda x: -x[0])
    recent_names = [name for _, name in recent[:10]]

    lines = [
        "## Vault Statistics\n",
        f"**Total notes:** {len(all_notes)}",
        f"**Total unique tags:** {len(tag_counts)}",
        f"**Total links:** {sum(link_counts.values())}",
        f"**Orphan notes:** {len(orphans)}",
        "",
        "### Top Tags",
    ]
    for tag, count in top_tags:
        lines.append(f"- #{tag}: {count} notes")
    lines.append("\n### Most Connected Notes")
    for name, score in most_connected:
        lines.append(f"- [[{name}]]: {score} connections")
    if orphans:
        lines.append(f"\n### Orphan Notes ({len(orphans)})")
        for o in sorted(orphans)[:20]:
            lines.append(f"- {o}")
    lines.append("\n### Recent Activity")
    for name in recent_names:
        lines.append(f"- [[{name}]]")
    return "\n".join(lines)


def _vault_kanban(ctx: ToolContext, *, board: str = "kanban",
                  action: str = "view", item: str = "",
                  from_column: str = "", to_column: str = "") -> str:
    path = _resolve_note_path(board)
    columns_order = ["Backlog", "In Progress", "Done"]

    if action == "view" or (action == "view" and not path.exists()):
        if not path.exists():
            return f"Kanban board '{board}' does not exist. Use action='add' to create it."
        return path.read_text(encoding="utf-8")

    if action == "create":
        if path.exists():
            return f"Board '{board}' already exists."
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = _build_frontmatter(board, tags=["kanban"],
                                extra={"kanban-plugin": "basic"})
        body = "## Backlog\n\n\n## In Progress\n\n\n## Done\n\n"
        path.write_text(fm + "\n" + body, encoding="utf-8")
        return f"Created kanban board: {board}"

    if action == "add":
        if not item:
            return "Provide 'item' text to add."
        column = to_column or "Backlog"
        if not path.exists():
            # Auto-create
            path.parent.mkdir(parents=True, exist_ok=True)
            fm = _build_frontmatter(board, tags=["kanban"],
                                    extra={"kanban-plugin": "basic"})
            body = "## Backlog\n\n\n## In Progress\n\n\n## Done\n\n"
            path.write_text(fm + "\n" + body, encoding="utf-8")
        text = path.read_text(encoding="utf-8")
        marker = f"## {column}"
        if marker not in text:
            return f"Column '{column}' not found in board."
        # Insert item after the column header
        idx = text.index(marker) + len(marker)
        text = text[:idx] + f"\n- [ ] {item}" + text[idx:]
        path.write_text(text, encoding="utf-8")
        return f"Added '{item}' to {column}"

    if action == "move":
        if not item or not to_column:
            return "Provide 'item' and 'to_column' for move."
        if not path.exists():
            return f"Board '{board}' not found."
        text = path.read_text(encoding="utf-8")
        # Find and remove item from any column
        # Match both checked and unchecked
        patterns = [f"- [ ] {item}", f"- [x] {item}"]
        found = False
        for pat in patterns:
            if pat in text:
                text = text.replace(pat + "\n", "", 1)
                if pat not in text:
                    text = text.replace(pat, "", 1)
                found = True
                break
        if not found:
            return f"Item '{item}' not found on board."
        # Add to target column
        marker = f"## {to_column}"
        if marker not in text:
            return f"Column '{to_column}' not found."
        check = "[x]" if to_column == "Done" else "[ ]"
        idx = text.index(marker) + len(marker)
        text = text[:idx] + f"\n- {check} {item}" + text[idx:]
        path.write_text(text, encoding="utf-8")
        return f"Moved '{item}' to {to_column}"

    return f"Unknown kanban action '{action}'. Use: view, create, add, move."


def _vault_bookmark(ctx: ToolContext, *, url: str, title: str = "",
                    notes: str = "", tags: Optional[List[str]] = None) -> str:
    root = _vault_root()
    bm_dir = root / "bookmarks"
    bm_dir.mkdir(parents=True, exist_ok=True)
    display_title = title or url
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', display_title[:60]).strip('-').lower()
    if not slug:
        slug = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    path = bm_dir / f"{slug}.md"
    counter = 1
    while path.exists():
        path = bm_dir / f"{slug}-{counter}.md"
        counter += 1
    all_tags = list(tags or []) + ["bookmark"]
    fm = _build_frontmatter(display_title, tags=all_tags, extra={"url": f'"{url}"'})
    body = f"# {display_title}\n\n**URL:** {url}\n"
    if notes:
        body += f"\n## Notes\n{notes}\n"
    path.write_text(fm + "\n" + body, encoding="utf-8")
    return f"Bookmarked: {display_title} ({path.relative_to(root)})"


def _vault_decision_log(ctx: ToolContext, *, decision: str, context_text: str = "",
                        options: Optional[List[str]] = None, rationale: str = "",
                        outcome: str = "", tags: Optional[List[str]] = None) -> str:
    root = _vault_root()
    dec_dir = root / "decisions"
    dec_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', decision[:60]).strip('-').lower()
    if not slug:
        slug = date_str
    path = dec_dir / f"{date_str}-{slug}.md"
    all_tags = list(tags or []) + ["decision"]
    fm = _build_frontmatter(decision, tags=all_tags,
                            extra={"status": "decided", "decision_date": date_str})
    body = f"# Decision: {decision}\n\n**Date:** {date_str}\n"
    if context_text:
        body += f"\n## Context\n{context_text}\n"
    if options:
        body += "\n## Options Considered\n"
        for i, opt in enumerate(options, 1):
            body += f"{i}. {opt}\n"
    if rationale:
        body += f"\n## Rationale\n{rationale}\n"
    if outcome:
        body += f"\n## Expected Outcome\n{outcome}\n"
    path.write_text(fm + "\n" + body, encoding="utf-8")
    return f"Decision logged: {path.relative_to(root)}"


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("vault_create", {
            "name": "vault_create",
            "description": "Create a new note in the knowledge vault with YAML frontmatter. Supports folders (e.g. 'projects/aalp').",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title/path (e.g. 'My Note' or 'projects/my-project')"},
                    "content": {"type": "string", "description": "Note body content (markdown)", "default": ""},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for the note"},
                    "links": {"type": "array", "items": {"type": "string"}, "description": "Wiki link targets to add as [[links]]"},
                    "aliases": {"type": "array", "items": {"type": "string"}, "description": "Alternative titles for this note"},
                },
                "required": ["title"],
            },
        }, _vault_create),

        ToolEntry("vault_read", {
            "name": "vault_read",
            "description": "Read a note from the vault by title or path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title or path to read"},
                },
                "required": ["title"],
            },
        }, _vault_read),

        ToolEntry("vault_edit", {
            "name": "vault_edit",
            "description": "Edit an existing note: append, prepend, or replace content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title/path"},
                    "content": {"type": "string", "description": "Content to add or replace with"},
                    "mode": {"type": "string", "enum": ["append", "prepend", "replace"], "description": "Edit mode (default: append)"},
                },
                "required": ["title", "content"],
            },
        }, _vault_edit),

        ToolEntry("vault_delete", {
            "name": "vault_delete",
            "description": "Delete a note from the vault.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title/path to delete"},
                },
                "required": ["title"],
            },
        }, _vault_delete),

        ToolEntry("vault_list", {
            "name": "vault_list",
            "description": "List all notes in the vault, optionally filtered by folder or tag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Filter to notes in this folder", "default": ""},
                    "tag": {"type": "string", "description": "Filter to notes with this tag", "default": ""},
                },
                "required": [],
            },
        }, _vault_list),

        ToolEntry("vault_search", {
            "name": "vault_search",
            "description": "Full-text search across all vault notes. Returns matching notes with context snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query string"},
                    "max_results": {"type": "integer", "description": "Max results to return (default 10)", "default": 10},
                },
                "required": ["query"],
            },
        }, _vault_search),

        ToolEntry("vault_tag_search", {
            "name": "vault_tag_search",
            "description": "Find all notes with a specific tag.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "description": "Tag to search for (with or without #)"},
                },
                "required": ["tag"],
            },
        }, _vault_tag_search),

        ToolEntry("vault_backlinks", {
            "name": "vault_backlinks",
            "description": "Find all notes that link TO a specific note (backlinks).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title to find backlinks for"},
                },
                "required": ["title"],
            },
        }, _vault_backlinks),

        ToolEntry("vault_graph", {
            "name": "vault_graph",
            "description": "Generate a knowledge graph showing all notes and their [[wiki link]] connections as an adjacency list.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }, _vault_graph),

        ToolEntry("vault_daily_note", {
            "name": "vault_daily_note",
            "description": "Create or append to today's daily note. Perfect for logging activity, thoughts, discoveries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to add to daily note", "default": ""},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format (default: today)", "default": ""},
                },
                "required": [],
            },
        }, _vault_daily_note),

        ToolEntry("vault_weekly_summary", {
            "name": "vault_weekly_summary",
            "description": "Auto-generate a weekly summary from daily notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "week_start": {"type": "string", "description": "Monday date YYYY-MM-DD (default: this week's Monday)", "default": ""},
                },
                "required": [],
            },
        }, _vault_weekly_summary),

        ToolEntry("vault_templates", {
            "name": "vault_templates",
            "description": "Create notes from templates: meeting, project, research, decision, retrospective.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "use"], "description": "List templates or use one"},
                    "template_name": {"type": "string", "description": "Template name (for action=use)"},
                    "title": {"type": "string", "description": "Title for the new note (for action=use)"},
                    "folder": {"type": "string", "description": "Optional folder to create note in", "default": ""},
                },
                "required": ["action"],
            },
        }, _vault_templates),

        ToolEntry("vault_moc", {
            "name": "vault_moc",
            "description": "Create or update a Map of Content (MOC) — an index note linking related notes by topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "MOC topic name"},
                    "note_titles": {"type": "array", "items": {"type": "string"}, "description": "Note titles to include"},
                    "auto_discover": {"type": "boolean", "description": "Auto-discover related notes by topic match", "default": False},
                },
                "required": ["topic"],
            },
        }, _vault_moc),

        ToolEntry("vault_learn", {
            "name": "vault_learn",
            "description": "Store a learned fact/insight with source, context, and confidence level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "The fact or insight learned"},
                    "source": {"type": "string", "description": "Where this was learned from", "default": ""},
                    "context": {"type": "string", "description": "Additional context", "default": ""},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"], "description": "Confidence level", "default": "high"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                },
                "required": ["fact"],
            },
        }, _vault_learn),

        ToolEntry("vault_recall", {
            "name": "vault_recall",
            "description": "Query learned facts by topic. Returns relevant knowledge with sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic to recall facts about"},
                    "max_results": {"type": "integer", "description": "Max results (default 5)", "default": 5},
                },
                "required": ["topic"],
            },
        }, _vault_recall),

        ToolEntry("vault_connect", {
            "name": "vault_connect",
            "description": "Find potential connections between notes based on shared tags, words, and links. Suggests new [[links]] to add.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Specific note to find connections for (optional, searches all if empty)", "default": ""},
                },
                "required": [],
            },
        }, _vault_connect),

        ToolEntry("vault_export", {
            "name": "vault_export",
            "description": "Export vault stats: total notes, tag distribution, most connected notes, orphans, recent activity.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }, _vault_export),

        ToolEntry("vault_kanban", {
            "name": "vault_kanban",
            "description": "Create/manage a Kanban board as markdown (Obsidian Kanban plugin format). Columns: Backlog, In Progress, Done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "board": {"type": "string", "description": "Board name (default: kanban)", "default": "kanban"},
                    "action": {"type": "string", "enum": ["view", "create", "add", "move"], "description": "Action to perform"},
                    "item": {"type": "string", "description": "Item text (for add/move)", "default": ""},
                    "from_column": {"type": "string", "description": "Source column (for move)", "default": ""},
                    "to_column": {"type": "string", "description": "Target column (for add/move)", "default": ""},
                },
                "required": ["action"],
            },
        }, _vault_kanban),

        ToolEntry("vault_bookmark", {
            "name": "vault_bookmark",
            "description": "Save a URL with title, notes, and tags for later reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to bookmark"},
                    "title": {"type": "string", "description": "Bookmark title (default: URL)", "default": ""},
                    "notes": {"type": "string", "description": "Notes about the bookmark", "default": ""},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                },
                "required": ["url"],
            },
        }, _vault_bookmark),

        ToolEntry("vault_decision_log", {
            "name": "vault_decision_log",
            "description": "Log a decision with context, options considered, rationale, and outcome tracking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string", "description": "The decision made"},
                    "context_text": {"type": "string", "description": "Context/background for the decision", "default": ""},
                    "options": {"type": "array", "items": {"type": "string"}, "description": "Options that were considered"},
                    "rationale": {"type": "string", "description": "Why this option was chosen", "default": ""},
                    "outcome": {"type": "string", "description": "Expected outcome", "default": ""},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                },
                "required": ["decision"],
            },
        }, _vault_decision_log),
    ]

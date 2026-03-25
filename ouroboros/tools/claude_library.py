"""Runtime access to Claude Code skills, agents, and coding rules."""
import os, re
from pathlib import Path
from ouroboros.tools.registry import ToolEntry

_BASE = Path(os.environ.get("OUROBOROS_REPO_DIR", "/app"))
_SKILLS = _BASE / "claude_skills"
_AGENTS = _BASE / "claude_agents"
_RULES = _BASE / "claude_rules"


def _list_skills(args, ctx):
    q = args.get("query", "").lower()
    skills = []
    if _SKILLS.exists():
        for d in sorted(_SKILLS.iterdir()):
            if d.is_dir() and (not q or q in d.name.lower()):
                desc = ""
                skill_md = d / "SKILL.md"
                if skill_md.exists():
                    lines = skill_md.read_text(errors="ignore").split("\n")[:5]
                    for l in lines:
                        if l.strip() and not l.startswith("#") and not l.startswith("---"):
                            desc = l.strip()[:120]
                            break
                skills.append(f"- {d.name}: {desc}")
    if not skills:
        return "No skills found" + (f" matching '{q}'" if q else "")
    return f"Found {len(skills)} skills:\n" + "\n".join(skills)


def _read_skill(args, ctx):
    name = args.get("name", "").strip()
    if not name:
        return "Error: provide a skill name"
    skill_md = _SKILLS / name / "SKILL.md"
    if not skill_md.exists():
        matches = [d.name for d in _SKILLS.iterdir() if d.is_dir() and name.lower() in d.name.lower()]
        if matches:
            return f"Skill '{name}' not found. Did you mean: {', '.join(matches[:5])}"
        return f"Skill '{name}' not found"
    content = skill_md.read_text(errors="ignore")
    if len(content) > 4000:
        content = content[:4000] + "\n... (truncated)"
    return content


def _list_agents(args, ctx):
    q = args.get("query", "").lower()
    agents = []
    if _AGENTS.exists():
        for f in sorted(_AGENTS.glob("*.md")):
            if not q or q in f.stem.lower():
                lines = f.read_text(errors="ignore").split("\n")[:5]
                desc = ""
                for l in lines:
                    if l.strip() and not l.startswith("#") and not l.startswith("---"):
                        desc = l.strip()[:120]
                        break
                agents.append(f"- {f.stem}: {desc}")
    if not agents:
        return "No agents found" + (f" matching '{q}'" if q else "")
    return f"Found {len(agents)} agents:\n" + "\n".join(agents)


def _read_agent(args, ctx):
    name = args.get("name", "").strip()
    if not name:
        return "Error: provide an agent name"
    agent_md = _AGENTS / f"{name}.md"
    if not agent_md.exists():
        matches = [f.stem for f in _AGENTS.glob("*.md") if name.lower() in f.stem.lower()]
        if matches:
            return f"Agent '{name}' not found. Did you mean: {', '.join(matches[:5])}"
        return f"Agent '{name}' not found"
    content = agent_md.read_text(errors="ignore")
    if len(content) > 4000:
        content = content[:4000] + "\n... (truncated)"
    return content


def _list_rules(args, ctx):
    lang = args.get("language", "").lower()
    rules = []
    if _RULES.exists():
        for d in sorted(_RULES.iterdir()):
            if d.is_dir() and d.name != "__pycache__":
                if not lang or lang in d.name.lower():
                    files = [f.stem for f in d.glob("*.md") if f.name != "README.md"]
                    rules.append(f"- {d.name}: {', '.join(files)}")
    if not rules:
        return "No rules found" + (f" for '{lang}'" if lang else "")
    return f"Found {len(rules)} rule sets:\n" + "\n".join(rules)


def _read_rule(args, ctx):
    language = args.get("language", "").strip()
    topic = args.get("topic", "").strip()
    if not language or not topic:
        return "Error: provide language and topic (e.g. language='python', topic='security')"
    rule_md = _RULES / language / f"{topic}.md"
    if not rule_md.exists():
        avail = [f.stem for f in (_RULES / language).glob("*.md")] if (_RULES / language).exists() else []
        if avail:
            return f"Rule '{topic}' not found for {language}. Available: {', '.join(avail)}"
        return f"Language '{language}' not found"
    content = rule_md.read_text(errors="ignore")
    if len(content) > 4000:
        content = content[:4000] + "\n... (truncated)"
    return content


def _search_library(args, ctx):
    q = args.get("query", "").lower().strip()
    if not q:
        return "Error: provide a search query"
    results = []
    for base, label in [(_SKILLS, "skill"), (_AGENTS, "agent"), (_RULES, "rule")]:
        if not base.exists():
            continue
        for md in base.rglob("*.md"):
            try:
                content = md.read_text(errors="ignore")
                if q in content.lower():
                    rel = md.relative_to(_BASE)
                    for line in content.split("\n"):
                        if q in line.lower():
                            results.append(f"- [{label}] {rel}: ...{line.strip()[:100]}...")
                            break
            except Exception:
                pass
    if not results:
        return f"No results for '{q}'"
    return f"Found {len(results)} matches:\n" + "\n".join(results[:20])


def get_tools():
    return [
        ToolEntry(name="list_skills", description="List all Claude Code skills. Optional query to filter.", parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Filter skills by name"}}, "required": []}, handler=_list_skills),
        ToolEntry(name="read_skill", description="Read a Claude Code skill by name", parameters={"type": "object", "properties": {"name": {"type": "string", "description": "Skill name (e.g. 'deep-research')"}}, "required": ["name"]}, handler=_read_skill),
        ToolEntry(name="list_agents", description="List all Claude agents. Optional query to filter.", parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Filter agents by name"}}, "required": []}, handler=_list_agents),
        ToolEntry(name="read_agent", description="Read a Claude agent definition", parameters={"type": "object", "properties": {"name": {"type": "string", "description": "Agent name (e.g. 'architect')"}}, "required": ["name"]}, handler=_read_agent),
        ToolEntry(name="list_rules", description="List coding rules by language", parameters={"type": "object", "properties": {"language": {"type": "string", "description": "Language (python, rust, typescript, etc)"}}, "required": []}, handler=_list_rules),
        ToolEntry(name="read_rule", description="Read a coding rule for a language and topic", parameters={"type": "object", "properties": {"language": {"type": "string", "description": "Language (python, rust, etc)"}, "topic": {"type": "string", "description": "Topic (security, testing, patterns, etc)"}}, "required": ["language", "topic"]}, handler=_read_rule),
        ToolEntry(name="search_library", description="Search across all skills, agents, and rules by keyword", parameters={"type": "object", "properties": {"query": {"type": "string", "description": "Search keyword"}}, "required": ["query"]}, handler=_search_library),
    ]

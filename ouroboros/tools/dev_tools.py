"""
Ouroboros — Developer tools.

Code generator, API endpoint builder, database schema designer,
unit test generator, documentation writer, deployment scripts.
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional

from ouroboros.tools._adapter import adapt_tools

log = logging.getLogger(__name__)


# ── Code Generator ─────────────────────────────────────────────────────────

def code_generator(description: str, language: str = "python",
                   pattern: str = "function") -> Dict[str, Any]:
    """Generate code scaffolding for common patterns."""
    templates = _get_templates(language)
    template = templates.get(pattern, templates.get("function", ""))

    # Language-specific boilerplate
    boilerplate = {
        "python": {
            "function": textwrap.dedent(f'''
                def {_snake_case(description)}(params):
                    """
                    {description}

                    Args:
                        params: Input parameters

                    Returns:
                        Result of operation
                    """
                    # TODO: Implement {description}
                    result = None
                    return result
            ''').strip(),
            "class": textwrap.dedent(f'''
                class {_pascal_case(description)}:
                    """
                    {description}
                    """

                    def __init__(self):
                        """Initialize {_pascal_case(description)}."""
                        pass

                    def process(self, data):
                        """Process the given data."""
                        # TODO: Implement
                        return data

                    def validate(self, data):
                        """Validate input data."""
                        if data is None:
                            raise ValueError("Data cannot be None")
                        return True

                    def __repr__(self):
                        return f"{_pascal_case(description)}()"
            ''').strip(),
            "api_handler": textwrap.dedent(f'''
                from fastapi import APIRouter, HTTPException
                from pydantic import BaseModel

                router = APIRouter()

                class {_pascal_case(description)}Request(BaseModel):
                    # TODO: Define request fields
                    pass

                class {_pascal_case(description)}Response(BaseModel):
                    success: bool
                    data: dict = {{}}
                    message: str = ""

                @router.post("/{_snake_case(description)}")
                async def {_snake_case(description)}(request: {_pascal_case(description)}Request):
                    """
                    {description}
                    """
                    try:
                        # TODO: Implement
                        return {_pascal_case(description)}Response(success=True, data={{}}, message="OK")
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=str(e))
            ''').strip(),
            "cli": textwrap.dedent(f'''
                import argparse
                import sys

                def main():
                    parser = argparse.ArgumentParser(description="{description}")
                    parser.add_argument("input", help="Input file or value")
                    parser.add_argument("-o", "--output", help="Output file", default=None)
                    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
                    args = parser.parse_args()

                    # TODO: Implement {description}
                    if args.verbose:
                        print(f"Processing: {{args.input}}")

                    result = process(args.input)

                    if args.output:
                        with open(args.output, "w") as f:
                            f.write(str(result))
                    else:
                        print(result)

                def process(input_data):
                    """Process the input data."""
                    return input_data

                if __name__ == "__main__":
                    main()
            ''').strip(),
        },
        "javascript": {
            "function": textwrap.dedent(f'''
                /**
                 * {description}
                 * @param {{Object}} params - Input parameters
                 * @returns {{Promise<*>}} Result
                 */
                async function {_camel_case(description)}(params) {{
                  // TODO: Implement {description}
                  try {{
                    const result = null;
                    return result;
                  }} catch (error) {{
                    console.error(`Error in {_camel_case(description)}:`, error);
                    throw error;
                  }}
                }}

                module.exports = {{ {_camel_case(description)} }};
            ''').strip(),
            "class": textwrap.dedent(f'''
                /**
                 * {description}
                 */
                class {_pascal_case(description)} {{
                  constructor(options = {{}}) {{
                    this.options = options;
                  }}

                  async process(data) {{
                    // TODO: Implement
                    return data;
                  }}

                  validate(data) {{
                    if (!data) throw new Error("Data is required");
                    return true;
                  }}
                }}

                module.exports = {{ {_pascal_case(description)} }};
            ''').strip(),
            "api_handler": textwrap.dedent(f'''
                const express = require('express');
                const router = express.Router();

                /**
                 * {description}
                 */
                router.post('/{_kebab_case(description)}', async (req, res) => {{
                  try {{
                    const {{ /* destructure fields */ }} = req.body;
                    // TODO: Implement
                    res.json({{ success: true, data: {{}} }});
                  }} catch (error) {{
                    console.error(error);
                    res.status(500).json({{ success: false, error: error.message }});
                  }}
                }});

                module.exports = router;
            ''').strip(),
            "react_component": textwrap.dedent(f'''
                import React, {{ useState, useEffect }} from 'react';

                /**
                 * {description}
                 */
                const {_pascal_case(description)} = ({{ children, ...props }}) => {{
                  const [data, setData] = useState(null);
                  const [loading, setLoading] = useState(false);
                  const [error, setError] = useState(null);

                  useEffect(() => {{
                    // TODO: Fetch data or initialize
                  }}, []);

                  if (loading) return <div>Loading...</div>;
                  if (error) return <div>Error: {{error.message}}</div>;

                  return (
                    <div className="{_kebab_case(description)}">
                      {{/* TODO: Implement UI */}}
                      {{children}}
                    </div>
                  );
                }};

                export default {_pascal_case(description)};
            ''').strip(),
        },
        "typescript": {
            "function": textwrap.dedent(f'''
                /**
                 * {description}
                 */
                interface {_pascal_case(description)}Params {{
                  // TODO: Define parameters
                  input: string;
                }}

                interface {_pascal_case(description)}Result {{
                  success: boolean;
                  data: unknown;
                }}

                export async function {_camel_case(description)}(
                  params: {_pascal_case(description)}Params
                ): Promise<{_pascal_case(description)}Result> {{
                  // TODO: Implement
                  return {{ success: true, data: null }};
                }}
            ''').strip(),
        },
        "go": {
            "function": textwrap.dedent(f'''
                package main

                import (
                    "fmt"
                    "errors"
                )

                // {_pascal_case(description)} - {description}
                func {_pascal_case(description)}(input string) (string, error) {{
                    if input == "" {{
                        return "", errors.New("input cannot be empty")
                    }}
                    // TODO: Implement {description}
                    result := input
                    return result, nil
                }}
            ''').strip(),
        },
        "rust": {
            "function": textwrap.dedent(f'''
                /// {description}
                ///
                /// # Arguments
                /// * `input` - The input to process
                ///
                /// # Returns
                /// Result with the processed output or an error
                pub fn {_snake_case(description)}(input: &str) -> Result<String, Box<dyn std::error::Error>> {{
                    // TODO: Implement {description}
                    Ok(input.to_string())
                }}

                #[cfg(test)]
                mod tests {{
                    use super::*;

                    #[test]
                    fn test_{_snake_case(description)}() {{
                        let result = {_snake_case(description)}("test").unwrap();
                        assert!(!result.is_empty());
                    }}
                }}
            ''').strip(),
        },
    }

    lang_templates = boilerplate.get(language, boilerplate.get("python", {}))
    code = lang_templates.get(pattern, lang_templates.get("function", f"// TODO: Implement {description} in {language}"))

    return {
        "language": language,
        "pattern": pattern,
        "description": description,
        "code": code,
        "file_extension": _get_extension(language),
        "suggested_filename": f"{_snake_case(description)}.{_get_extension(language)}",
    }


def _get_templates(language: str) -> Dict[str, str]:
    return {"function": "", "class": "", "api_handler": "", "cli": ""}


def _snake_case(s: str) -> str:
    return "_".join(s.lower().split())[:50]


def _pascal_case(s: str) -> str:
    return "".join(w.capitalize() for w in s.split())[:50]


def _camel_case(s: str) -> str:
    pc = _pascal_case(s)
    return pc[0].lower() + pc[1:] if pc else ""


def _kebab_case(s: str) -> str:
    return "-".join(s.lower().split())[:50]


def _get_extension(language: str) -> str:
    exts = {
        "python": "py", "javascript": "js", "typescript": "ts",
        "go": "go", "rust": "rs", "java": "java", "c": "c",
        "cpp": "cpp", "ruby": "rb", "php": "php", "swift": "swift",
        "kotlin": "kt", "bash": "sh", "sql": "sql",
    }
    return exts.get(language.lower(), "txt")


# ── Database Schema Designer ──────────────────────────────────────────────

def db_schema_designer(tables: List[Dict[str, Any]],
                       dialect: str = "postgresql") -> Dict[str, Any]:
    """
    Generate database schema SQL from table definitions.
    tables: [{"name": "users", "columns": [{"name": "id", "type": "serial", "primary": true}, ...]}]
    """
    sql_lines = []
    for table in tables:
        tname = table["name"]
        cols = table.get("columns", [])
        col_defs = []
        pks = []
        fks = []

        for col in cols:
            cname = col["name"]
            ctype = col.get("type", "text")

            # Map types to dialect
            if dialect == "mysql":
                type_map = {"serial": "INT AUTO_INCREMENT", "text": "TEXT", "varchar": "VARCHAR(255)",
                            "integer": "INT", "boolean": "BOOLEAN", "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                            "jsonb": "JSON", "uuid": "CHAR(36)", "decimal": "DECIMAL(10,2)"}
            elif dialect == "sqlite":
                type_map = {"serial": "INTEGER", "text": "TEXT", "varchar": "TEXT",
                            "integer": "INTEGER", "boolean": "INTEGER", "timestamp": "TEXT",
                            "jsonb": "TEXT", "uuid": "TEXT", "decimal": "REAL"}
            else:  # postgresql
                type_map = {"serial": "SERIAL", "text": "TEXT", "varchar": "VARCHAR(255)",
                            "integer": "INTEGER", "boolean": "BOOLEAN", "timestamp": "TIMESTAMP DEFAULT NOW()",
                            "jsonb": "JSONB", "uuid": "UUID DEFAULT gen_random_uuid()", "decimal": "DECIMAL(10,2)"}

            mapped_type = type_map.get(ctype.lower(), ctype.upper())
            parts = [cname, mapped_type]

            if col.get("not_null", False):
                parts.append("NOT NULL")
            if col.get("unique", False):
                parts.append("UNIQUE")
            if col.get("default") is not None:
                parts.append(f"DEFAULT {col['default']}")
            if col.get("primary", False):
                pks.append(cname)

            col_defs.append("  " + " ".join(parts))

            if col.get("references"):
                ref = col["references"]
                fks.append(f"  FOREIGN KEY ({cname}) REFERENCES {ref}")

        if pks:
            col_defs.append(f"  PRIMARY KEY ({', '.join(pks)})")
        col_defs.extend(fks)

        sql_lines.append(f"CREATE TABLE {tname} (")
        sql_lines.append(",\n".join(col_defs))
        sql_lines.append(");\n")

    # Generate indexes
    index_lines = []
    for table in tables:
        for col in table.get("columns", []):
            if col.get("index", False):
                idx_name = f"idx_{table['name']}_{col['name']}"
                index_lines.append(f"CREATE INDEX {idx_name} ON {table['name']} ({col['name']});")

    sql = "\n".join(sql_lines)
    if index_lines:
        sql += "\n-- Indexes\n" + "\n".join(index_lines)

    return {
        "dialect": dialect,
        "tables": len(tables),
        "sql": sql,
        "migration_tip": "Use Alembic (Python), Prisma (JS), or Flyway (Java) for migrations.",
    }


# ── Unit Test Generator ──────────────────────────────────────────────────

def test_generator(function_name: str, language: str = "python",
                   test_cases: List[Dict[str, Any]] = None,
                   description: str = "") -> Dict[str, Any]:
    """Generate unit test scaffolding."""
    if not test_cases:
        test_cases = [
            {"name": "basic_valid_input", "input": "valid_input", "expected": "expected_output"},
            {"name": "empty_input", "input": "", "expected": "handle_empty"},
            {"name": "none_input", "input": None, "expected": "raise_error"},
            {"name": "edge_case", "input": "edge_value", "expected": "edge_result"},
        ]

    if language == "python":
        test_methods = []
        for tc in test_cases:
            test_methods.append(textwrap.dedent(f'''
    def test_{tc["name"]}(self):
        """{tc.get("description", f"Test {tc['name']}")}."""
        # Arrange
        input_data = {repr(tc["input"])}
        expected = {repr(tc["expected"])}
        # Act
        result = {function_name}(input_data)
        # Assert
        self.assertEqual(result, expected)
'''))
        code = textwrap.dedent(f'''
import unittest
from your_module import {function_name}


class Test{_pascal_case(function_name)}(unittest.TestCase):
    """Tests for {function_name}. {description}"""

    def setUp(self):
        """Set up test fixtures."""
        pass

    def tearDown(self):
        """Clean up after tests."""
        pass
{"".join(test_methods)}

if __name__ == "__main__":
    unittest.main()
''').strip()

    elif language == "javascript":
        test_blocks = []
        for tc in test_cases:
            test_blocks.append(textwrap.dedent(f'''
  it('should handle {tc["name"]}', () => {{
    const input = {json.dumps(tc["input"])};
    const expected = {json.dumps(tc["expected"])};
    const result = {_camel_case(function_name)}(input);
    expect(result).toEqual(expected);
  }});
'''))
        code = textwrap.dedent(f'''
const {{ {_camel_case(function_name)} }} = require('./your_module');

describe('{_camel_case(function_name)}', () => {{
  beforeEach(() => {{
    // Setup
  }});

  afterEach(() => {{
    // Cleanup
  }});
{"".join(test_blocks)}
}});
''').strip()

    elif language == "go":
        test_funcs = []
        for tc in test_cases:
            test_funcs.append(textwrap.dedent(f'''
func Test{_pascal_case(function_name)}_{_pascal_case(tc["name"])}(t *testing.T) {{
    input := {json.dumps(tc["input"])}
    expected := {json.dumps(tc["expected"])}
    result := {_pascal_case(function_name)}(input)
    if result != expected {{
        t.Errorf("Expected %v, got %v", expected, result)
    }}
}}
'''))
        code = textwrap.dedent(f'''
package main

import "testing"
{"".join(test_funcs)}
''').strip()

    else:
        code = f"// TODO: Generate tests for {function_name} in {language}"

    return {
        "function": function_name,
        "language": language,
        "test_count": len(test_cases),
        "code": code,
        "suggested_filename": f"test_{_snake_case(function_name)}.{_get_extension(language)}",
    }


# ── Documentation Writer ─────────────────────────────────────────────────

def doc_writer(project_name: str, components: List[str] = None,
               doc_type: str = "readme", api_endpoints: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate documentation: README, API docs, or contributing guide."""
    if doc_type == "readme":
        doc = textwrap.dedent(f'''
# {project_name}

> Brief description of {project_name}

## Features

{chr(10).join(f"- {c}" for c in (components or ["Feature 1", "Feature 2", "Feature 3"]))}

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/{_kebab_case(project_name)}.git
cd {_kebab_case(project_name)}

# Install dependencies
pip install -r requirements.txt  # or: npm install
```

## Usage

```bash
# Quick start
python main.py  # or: npm start
```

## Configuration

| Variable | Description | Default |
|----------|------------|---------|
| `PORT` | Server port | `8000` |
| `DEBUG` | Debug mode | `false` |
| `DATABASE_URL` | Database connection | `sqlite:///db.sqlite3` |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.
''').strip()

    elif doc_type == "api":
        endpoints = api_endpoints or [
            {"method": "GET", "path": "/api/v1/items", "description": "List items"},
            {"method": "POST", "path": "/api/v1/items", "description": "Create item"},
        ]
        sections = []
        for ep in endpoints:
            sections.append(textwrap.dedent(f'''
### {ep["method"]} `{ep["path"]}`

{ep.get("description", "")}

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| - | - | - | TODO: Add parameters |

**Response:** `200 OK`
```json
{{
  "success": true,
  "data": {{}}
}}
```
'''))
        doc = f"# {project_name} API Documentation\n\nBase URL: `https://api.example.com`\n\n## Endpoints\n" + "\n".join(sections)

    elif doc_type == "contributing":
        doc = textwrap.dedent(f'''
# Contributing to {project_name}

## Development Setup

1. Fork and clone the repository
2. Install dependencies
3. Create a branch for your feature
4. Make your changes
5. Run tests
6. Submit a PR

## Code Style

- Follow the existing code style
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed

## Pull Request Process

1. Update the README if needed
2. Ensure all tests pass
3. Get at least one code review approval
4. Squash commits before merging
''').strip()
    else:
        doc = f"# {project_name}\n\nDocumentation for {doc_type}"

    return {
        "project": project_name,
        "doc_type": doc_type,
        "content": doc,
        "suggested_filename": {"readme": "README.md", "api": "API.md", "contributing": "CONTRIBUTING.md"}.get(doc_type, f"{doc_type}.md"),
    }


# ── Deployment Scripts ────────────────────────────────────────────────────

def deployment_script(platform: str = "docker", project_name: str = "app",
                      language: str = "python", port: int = 8000) -> Dict[str, Any]:
    """Generate deployment configuration files."""
    scripts = {}

    if platform == "docker" or platform == "all":
        if language == "python":
            scripts["Dockerfile"] = textwrap.dedent(f'''
                FROM python:3.11-slim
                WORKDIR /app
                COPY requirements.txt .
                RUN pip install --no-cache-dir -r requirements.txt
                COPY . .
                EXPOSE {port}
                CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
            ''').strip()
        elif language in ("javascript", "typescript"):
            scripts["Dockerfile"] = textwrap.dedent(f'''
                FROM node:20-slim
                WORKDIR /app
                COPY package*.json ./
                RUN npm ci --only=production
                COPY . .
                EXPOSE {port}
                CMD ["node", "index.js"]
            ''').strip()
        else:
            scripts["Dockerfile"] = textwrap.dedent(f'''
                FROM ubuntu:22.04
                WORKDIR /app
                COPY . .
                EXPOSE {port}
                CMD ["./start.sh"]
            ''').strip()

        scripts["docker-compose.yml"] = textwrap.dedent(f'''
            version: '3.8'
            services:
              {project_name}:
                build: .
                ports:
                  - "{port}:{port}"
                environment:
                  - NODE_ENV=production
                  - PORT={port}
                restart: unless-stopped
                volumes:
                  - ./data:/app/data
        ''').strip()

        scripts[".dockerignore"] = textwrap.dedent('''
            node_modules
            __pycache__
            .git
            .env
            *.pyc
            .venv
            dist
            coverage
        ''').strip()

    if platform == "github_actions" or platform == "all":
        scripts[".github/workflows/ci.yml"] = textwrap.dedent(f'''
            name: CI/CD
            on:
              push:
                branches: [main]
              pull_request:
                branches: [main]

            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
                  - name: Set up environment
                    uses: {"actions/setup-python@v5\n                    with:\n                      python-version: '3.11'" if language == "python" else "actions/setup-node@v4\n                    with:\n                      node-version: '20'"}
                  - name: Install dependencies
                    run: {"pip install -r requirements.txt" if language == "python" else "npm ci"}
                  - name: Run tests
                    run: {"python -m pytest" if language == "python" else "npm test"}

              deploy:
                needs: test
                runs-on: ubuntu-latest
                if: github.ref == 'refs/heads/main'
                steps:
                  - uses: actions/checkout@v4
                  - name: Deploy
                    run: echo "Add deployment steps here"
        ''').strip()

    if platform == "systemd" or platform == "all":
        scripts[f"{project_name}.service"] = textwrap.dedent(f'''
            [Unit]
            Description={project_name}
            After=network.target

            [Service]
            Type=simple
            User=www-data
            WorkingDirectory=/opt/{project_name}
            ExecStart=/opt/{project_name}/venv/bin/python -m uvicorn main:app --port {port}
            Restart=always
            RestartSec=5
            Environment=PORT={port}

            [Install]
            WantedBy=multi-user.target
        ''').strip()

    if platform == "nginx" or platform == "all":
        scripts[f"{project_name}.nginx.conf"] = textwrap.dedent(f'''
            server {{
                listen 80;
                server_name example.com;

                location / {{
                    proxy_pass http://127.0.0.1:{port};
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                }}

                location /static/ {{
                    alias /opt/{project_name}/static/;
                }}
            }}
        ''').strip()

    return {
        "platform": platform,
        "project": project_name,
        "language": language,
        "port": port,
        "files": scripts,
        "file_count": len(scripts),
    }


# ── Raw tools ──────────────────────────────────────────────────────────────

def _raw_tools() -> list:
    return [
        {
            "name": "code_generator",
            "description": "Generate code scaffolding (functions, classes, API handlers, CLI apps, React components) in any language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "What the code should do"},
                    "language": {"type": "string", "enum": ["python", "javascript", "typescript", "go", "rust"], "default": "python"},
                    "pattern": {"type": "string", "enum": ["function", "class", "api_handler", "cli", "react_component"], "default": "function"},
                },
                "required": ["description"],
            },
            "function": code_generator,
        },
        {
            "name": "db_schema_designer",
            "description": "Generate database schema SQL from table definitions. Supports PostgreSQL, MySQL, SQLite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tables": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of table defs: [{name, columns: [{name, type, primary, not_null, unique, references, index}]}]",
                    },
                    "dialect": {"type": "string", "enum": ["postgresql", "mysql", "sqlite"], "default": "postgresql"},
                },
                "required": ["tables"],
            },
            "function": db_schema_designer,
        },
        {
            "name": "test_generator",
            "description": "Generate unit test scaffolding for a function in Python, JavaScript, or Go.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {"type": "string"},
                    "language": {"type": "string", "enum": ["python", "javascript", "go"], "default": "python"},
                    "test_cases": {"type": "array", "items": {"type": "object"},
                                   "description": "List of {name, input, expected, description}"},
                    "description": {"type": "string", "default": ""},
                },
                "required": ["function_name"],
            },
            "function": test_generator,
        },
        {
            "name": "doc_writer",
            "description": "Generate project documentation: README, API docs, or contributing guide.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "components": {"type": "array", "items": {"type": "string"}, "description": "List of features/components"},
                    "doc_type": {"type": "string", "enum": ["readme", "api", "contributing"], "default": "readme"},
                    "api_endpoints": {"type": "array", "items": {"type": "object"}, "description": "For API docs: [{method, path, description}]"},
                },
                "required": ["project_name"],
            },
            "function": doc_writer,
        },
        {
            "name": "deployment_script",
            "description": "Generate deployment configs: Docker, GitHub Actions, systemd, nginx.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["docker", "github_actions", "systemd", "nginx", "all"], "default": "docker"},
                    "project_name": {"type": "string", "default": "app"},
                    "language": {"type": "string", "default": "python"},
                    "port": {"type": "integer", "default": 8000},
                },
            },
            "function": deployment_script,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

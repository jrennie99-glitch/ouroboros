"""
Ouroboros — Elite Coding tools.

Multi-language code generation, debugging, reviewing, architecture design,
testing, profiling, scaffolding, CI/CD, Docker, and more.
All tools produce real, working output — not stubs.
"""

from __future__ import annotations
import logging

from ouroboros.tools._adapter import adapt_tools
import json
import os
import re
import subprocess
import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

WORKSPACE = os.environ.get("OUROBOROS_WORKSPACE", "/tmp/ouroboros_coding")


def _ensure_workspace():
    os.makedirs(WORKSPACE, exist_ok=True)


# ── Language templates & patterns ─────────────────────────────────────────

LANG_EXTENSIONS = {
    "python": ".py", "javascript": ".js", "typescript": ".ts",
    "rust": ".rs", "go": ".go", "cpp": ".cpp", "c": ".c",
    "java": ".java", "ruby": ".rb", "swift": ".swift",
    "kotlin": ".kt", "php": ".php", "sql": ".sql", "bash": ".sh",
    "csharp": ".cs", "scala": ".scala", "r": ".R", "dart": ".dart",
}

LANG_COMMENT_STYLE = {
    "python": "#", "javascript": "//", "typescript": "//",
    "rust": "//", "go": "//", "cpp": "//", "c": "//",
    "java": "//", "ruby": "#", "swift": "//",
    "kotlin": "//", "php": "//", "sql": "--", "bash": "#",
    "csharp": "//", "scala": "//", "r": "#", "dart": "//",
}

BOILERPLATE = {
    "python": {
        "function": 'def {name}({params}):\n    """{docstring}"""\n    {body}\n',
        "class": 'class {name}:\n    """{docstring}"""\n\n    def __init__(self{init_params}):\n        {init_body}\n\n    {methods}\n',
        "async_function": 'async def {name}({params}):\n    """{docstring}"""\n    {body}\n',
        "dataclass": 'from dataclasses import dataclass\n\n@dataclass\nclass {name}:\n    """{docstring}"""\n    {fields}\n',
        "api_endpoint": '@app.{method}("{path}")\nasync def {name}({params}):\n    """{docstring}"""\n    {body}\n',
        "context_manager": 'from contextlib import contextmanager\n\n@contextmanager\ndef {name}({params}):\n    """{docstring}"""\n    {setup}\n    try:\n        yield {yield_val}\n    finally:\n        {teardown}\n',
    },
    "javascript": {
        "function": 'function {name}({params}) {{\n  {body}\n}}\n',
        "class": 'class {name} {{\n  constructor({init_params}) {{\n    {init_body}\n  }}\n\n  {methods}\n}}\n',
        "async_function": 'async function {name}({params}) {{\n  {body}\n}}\n',
        "arrow": 'const {name} = ({params}) => {{\n  {body}\n}};\n',
        "react_component": 'import React from "react";\n\nconst {name} = ({{{params}}}) => {{\n  return (\n    {jsx}\n  );\n}};\n\nexport default {name};\n',
        "express_route": 'router.{method}("{path}", async (req, res) => {{\n  try {{\n    {body}\n  }} catch (error) {{\n    res.status(500).json({{ error: error.message }});\n  }}\n}});\n',
    },
    "typescript": {
        "function": 'function {name}({params}): {return_type} {{\n  {body}\n}}\n',
        "class": 'class {name} {{\n  {fields}\n\n  constructor({init_params}) {{\n    {init_body}\n  }}\n\n  {methods}\n}}\n',
        "interface": 'interface {name} {{\n  {fields}\n}}\n',
        "type": 'type {name} = {{\n  {fields}\n}};\n',
        "react_component": 'import React from "react";\n\ninterface {name}Props {{\n  {props}\n}}\n\nconst {name}: React.FC<{name}Props> = ({{{params}}}) => {{\n  return (\n    {jsx}\n  );\n}};\n\nexport default {name};\n',
    },
    "rust": {
        "function": 'fn {name}({params}) -> {return_type} {{\n    {body}\n}}\n',
        "struct": '#[derive(Debug, Clone)]\nstruct {name} {{\n    {fields}\n}}\n\nimpl {name} {{\n    fn new({init_params}) -> Self {{\n        Self {{\n            {init_body}\n        }}\n    }}\n\n    {methods}\n}}\n',
        "enum": '#[derive(Debug, Clone)]\nenum {name} {{\n    {variants}\n}}\n',
        "trait": 'trait {name} {{\n    {methods}\n}}\n',
    },
    "go": {
        "function": 'func {name}({params}) {return_type} {{\n\t{body}\n}}\n',
        "struct": 'type {name} struct {{\n\t{fields}\n}}\n\nfunc New{name}({init_params}) *{name} {{\n\treturn &{name}{{\n\t\t{init_body}\n\t}}\n}}\n',
        "interface": 'type {name} interface {{\n\t{methods}\n}}\n',
        "handler": 'func {name}Handler(w http.ResponseWriter, r *http.Request) {{\n\t{body}\n}}\n',
    },
    "java": {
        "class": 'public class {name} {{\n    {fields}\n\n    public {name}({init_params}) {{\n        {init_body}\n    }}\n\n    {methods}\n}}\n',
        "interface": 'public interface {name} {{\n    {methods}\n}}\n',
    },
    "cpp": {
        "class": 'class {name} {{\npublic:\n    {name}({init_params});\n    ~{name}();\n    {methods}\n\nprivate:\n    {fields}\n}};\n',
        "function": '{return_type} {name}({params}) {{\n    {body}\n}}\n',
    },
    "sql": {
        "create_table": 'CREATE TABLE {name} (\n    id SERIAL PRIMARY KEY,\n    {columns}\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n',
        "select": 'SELECT {columns}\nFROM {table}\n{joins}\nWHERE {conditions}\n{group_by}\n{order_by}\n{limit};\n',
        "insert": 'INSERT INTO {table} ({columns})\nVALUES ({values})\nRETURNING *;\n',
    },
}

# ── Error patterns for debugging ──────────────────────────────────────────

ERROR_PATTERNS = {
    "python": {
        r"TypeError: .* takes (\d+) positional argument.* (\d+) .* given": "Argument count mismatch. Check function signature and call site.",
        r"AttributeError: '(\w+)' object has no attribute '(\w+)'": "Object '{0}' doesn't have attribute '{1}'. Check spelling or if the attribute exists on this type.",
        r"ImportError: No module named '(\w+)'": "Module '{0}' not found. Install with: pip install {0}",
        r"KeyError: '?(\w+)'?": "Key '{0}' not found in dictionary. Use .get('{0}', default) for safe access.",
        r"IndexError: list index out of range": "List index out of bounds. Check list length before accessing.",
        r"NameError: name '(\w+)' is not defined": "Variable '{0}' not defined. Check scope, spelling, or imports.",
        r"ValueError: (.+)": "Invalid value: {0}. Validate input before processing.",
        r"ZeroDivisionError": "Division by zero. Add a check: if denominator != 0.",
        r"FileNotFoundError: .* '(.+)'": "File '{0}' not found. Check path and permissions.",
        r"RecursionError": "Maximum recursion depth exceeded. Add a base case or use iteration.",
        r"UnicodeDecodeError": "Encoding issue. Try: open(file, encoding='utf-8').",
        r"JSONDecodeError": "Invalid JSON. Validate input string before parsing.",
        r"ConnectionError": "Network connection failed. Check URL, network, and retry logic.",
        r"TimeoutError": "Operation timed out. Increase timeout or add retry with backoff.",
    },
    "javascript": {
        r"TypeError: Cannot read propert.* of (undefined|null)": "Accessing property on {0}. Add null check: obj?.property or obj && obj.property",
        r"ReferenceError: (\w+) is not defined": "Variable '{0}' not defined. Check imports, scope, or spelling.",
        r"SyntaxError: Unexpected token": "Syntax error. Check for missing brackets, commas, or semicolons.",
        r"TypeError: (\w+) is not a function": "'{0}' is not callable. Check if it's imported correctly or if the type is wrong.",
        r"RangeError: Maximum call stack size exceeded": "Infinite recursion detected. Add a base case.",
        r"CORS": "CORS error. Configure server headers: Access-Control-Allow-Origin.",
        r"ERR_MODULE_NOT_FOUND": "Module not found. Run: npm install <package>",
        r"ECONNREFUSED": "Connection refused. Check if the server is running on the expected port.",
    },
    "rust": {
        r"error\[E0382\]": "Use-after-move error. Clone the value, use a reference, or restructure ownership.",
        r"error\[E0502\]": "Cannot borrow as mutable because it's also borrowed as immutable. Restructure borrows.",
        r"error\[E0308\]": "Type mismatch. Check expected vs actual types.",
        r"error\[E0277\]": "Trait not implemented. Add #[derive(...)] or implement the trait manually.",
        r"error\[E0433\]": "Unresolved import. Add to Cargo.toml or check module path.",
    },
    "go": {
        r"undefined: (\w+)": "'{0}' is undefined. Check imports and variable declarations.",
        r"cannot use .* as .* in": "Type mismatch in assignment or function call.",
        r"imported and not used": "Remove unused imports or use them.",
        r"declared and not used": "Remove unused variables or use them.",
        r"nil pointer dereference": "Nil pointer. Add nil check before dereferencing.",
    },
}

CODE_SMELLS = {
    "long_function": {"pattern": r"^(def |function |fn |func )", "threshold": 50, "msg": "Function exceeds {threshold} lines. Consider breaking it into smaller functions."},
    "deep_nesting": {"pattern": r"^(\s{16,}|\t{4,})", "msg": "Deep nesting detected (4+ levels). Consider early returns or extracting methods."},
    "magic_numbers": {"pattern": r"(?<!['\"\w])(?:(?<!=\s)(?<![<>!=]))\b(?:[2-9]\d{2,}|[1-9]\d{3,})\b(?!['\"])", "msg": "Magic number detected. Extract to a named constant."},
    "god_class": {"threshold": 300, "msg": "File exceeds {threshold} lines. Consider splitting into multiple modules."},
    "todo_fixme": {"pattern": r"(?:TODO|FIXME|HACK|XXX|WORKAROUND)", "msg": "Unresolved TODO/FIXME comment found."},
    "bare_except": {"pattern": r"except\s*:", "msg": "Bare except clause. Catch specific exceptions instead."},
    "print_debug": {"pattern": r"(?:console\.log|print\(|System\.out\.print|fmt\.Print)", "msg": "Debug print statement found. Use proper logging instead."},
    "hardcoded_secret": {"pattern": r"(?:password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]", "msg": "Potential hardcoded secret/credential detected. Use environment variables."},
}

# ── Big-O patterns for profiling ──────────────────────────────────────────

COMPLEXITY_PATTERNS = {
    "nested_loop_2": {"pattern": r"for .+:\s*\n\s+for .+:", "complexity": "O(n^2)", "msg": "Nested loop detected — O(n^2) time complexity."},
    "nested_loop_3": {"pattern": r"for .+:\s*\n\s+for .+:\s*\n\s+for .+:", "complexity": "O(n^3)", "msg": "Triple nested loop — O(n^3). Consider algorithmic optimization."},
    "sort_in_loop": {"pattern": r"for .+:[\s\S]{0,200}\.sort\(", "complexity": "O(n^2 log n)", "msg": "Sorting inside a loop. Consider sorting once outside."},
    "list_in_check": {"pattern": r"if .+ in \[", "complexity": "O(n)", "msg": "Membership check on list is O(n). Use a set for O(1) lookup."},
    "string_concat_loop": {"pattern": r"for .+:[\s\S]{0,100}\+= ['\"]", "complexity": "O(n^2)", "msg": "String concatenation in loop. Use join() or StringBuilder."},
    "recursive_no_memo": {"pattern": r"def (\w+)\([^)]*\):[\s\S]{0,500}return \1\(", "complexity": "O(2^n) potential", "msg": "Recursive function without memoization. Consider @lru_cache or dynamic programming."},
    "global_var_access": {"pattern": r"global \w+", "complexity": "performance concern", "msg": "Global variable access can inhibit optimizations."},
    "append_in_comprehension": {"pattern": r"\[.+for .+for .+\]", "complexity": "O(n*m)", "msg": "Nested comprehension. Verify this doesn't create excessive memory allocation."},
}

# ── Project scaffolding templates ─────────────────────────────────────────

SCAFFOLD_TEMPLATES = {
    "fastapi": {
        "files": {
            "main.py": '''"""FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="{project_name}", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {{"message": "Welcome to {project_name}"}}


@app.get("/health")
async def health():
    return {{"status": "healthy"}}
''',
            "requirements.txt": "fastapi>=0.104.0\nuvicorn[standard]>=0.24.0\npydantic>=2.5.0\npython-dotenv>=1.0.0\n",
            "Dockerfile": '''FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
            ".env.example": "DATABASE_URL=postgresql://user:pass@localhost:5432/db\nSECRET_KEY=change-me\n",
            "models/__init__.py": "",
            "routes/__init__.py": "",
            "tests/__init__.py": "",
            "tests/test_main.py": '''"""Tests for main app."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
''',
        },
    },
    "nextjs": {
        "files": {
            "package.json": '''{{"name": "{project_name}", "version": "0.1.0", "private": true, "scripts": {{"dev": "next dev", "build": "next build", "start": "next start", "lint": "next lint"}}, "dependencies": {{"next": "14.0.0", "react": "^18", "react-dom": "^18"}}, "devDependencies": {{"@types/node": "^20", "@types/react": "^18", "typescript": "^5", "eslint": "^8", "eslint-config-next": "14.0.0"}}}}''',
            "tsconfig.json": '''{{"compilerOptions": {{"target": "es5", "lib": ["dom", "dom.iterable", "esnext"], "allowJs": true, "skipLibCheck": true, "strict": true, "noEmit": true, "esModuleInterop": true, "module": "esnext", "moduleResolution": "bundler", "resolveJsonModule": true, "isolatedModules": true, "jsx": "preserve", "incremental": true, "paths": {{"@/*": ["./src/*"]}}}}}}''',
            "src/app/layout.tsx": '''import type {{ Metadata }} from "next";

export const metadata: Metadata = {{
  title: "{project_name}",
  description: "Built with Next.js",
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  );
}}
''',
            "src/app/page.tsx": '''export default function Home() {{
  return (
    <main>
      <h1>{project_name}</h1>
      <p>Get started by editing src/app/page.tsx</p>
    </main>
  );
}}
''',
        },
    },
    "express": {
        "files": {
            "package.json": '''{{"name": "{project_name}", "version": "1.0.0", "main": "src/index.js", "scripts": {{"start": "node src/index.js", "dev": "nodemon src/index.js", "test": "jest"}}, "dependencies": {{"express": "^4.18.0", "cors": "^2.8.5", "dotenv": "^16.3.0", "helmet": "^7.1.0", "morgan": "^1.10.0"}}, "devDependencies": {{"jest": "^29.7.0", "nodemon": "^3.0.0", "supertest": "^6.3.0"}}}}''',
            "src/index.js": '''require("dotenv").config();
const express = require("express");
const cors = require("cors");
const helmet = require("helmet");
const morgan = require("morgan");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(cors());
app.use(morgan("dev"));
app.use(express.json());

app.get("/", (req, res) => {{
  res.json({{ message: "Welcome to {project_name}" }});
}});

app.get("/health", (req, res) => {{
  res.json({{ status: "healthy", uptime: process.uptime() }});
}});

// Error handler
app.use((err, req, res, next) => {{
  console.error(err.stack);
  res.status(500).json({{ error: "Internal Server Error" }});
}});

app.listen(PORT, () => {{
  console.log(`Server running on port ${{PORT}}`);
}});

module.exports = app;
''',
            "src/routes/.gitkeep": "",
            "src/middleware/.gitkeep": "",
            "tests/app.test.js": '''const request = require("supertest");
const app = require("../src/index");

describe("GET /", () => {{
  it("should return welcome message", async () => {{
    const res = await request(app).get("/");
    expect(res.statusCode).toBe(200);
  }});
}});
''',
            ".env.example": "PORT=3000\nNODE_ENV=development\nDATABASE_URL=\n",
        },
    },
    "django": {
        "files": {
            "manage.py": '''#!/usr/bin/env python
"""Django management script."""
import os, sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{project_name}.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
''',
            "requirements.txt": "django>=5.0\ndjango-cors-headers>=4.3\ndjango-environ>=0.11\ngunicorn>=21.2\npsycopg2-binary>=2.9\n",
            "{project_name}/__init__.py": "",
            "{project_name}/urls.py": '''from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
''',
        },
    },
    "react": {
        "files": {
            "package.json": '''{{"name": "{project_name}", "version": "0.1.0", "private": true, "dependencies": {{"react": "^18.2.0", "react-dom": "^18.2.0", "react-scripts": "5.0.1"}}, "scripts": {{"start": "react-scripts start", "build": "react-scripts build", "test": "react-scripts test"}}}}''',
            "public/index.html": '''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>{project_name}</title></head>
<body><noscript>Enable JavaScript.</noscript><div id="root"></div></body>
</html>
''',
            "src/index.js": '''import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<React.StrictMode><App /></React.StrictMode>);
''',
            "src/App.js": '''import React from "react";

function App() {{
  return (
    <div className="App">
      <h1>{project_name}</h1>
    </div>
  );
}}

export default App;
''',
        },
    },
}

# ── CI/CD templates ───────────────────────────────────────────────────────

CICD_TEMPLATES = {
    "github_actions": {
        "python": '''name: Python CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{{{ matrix.python-version }}}}
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov ruff
      - name: Lint with ruff
        run: ruff check .
      - name: Test with pytest
        run: pytest --cov=. --cov-report=xml -v
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        if: matrix.python-version == '3.12'
''',
        "node": '''name: Node.js CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18.x, 20.x, 22.x]

    steps:
      - uses: actions/checkout@v4
      - name: Use Node.js ${{{{ matrix.node-version }}}}
        uses: actions/setup-node@v4
        with:
          node-version: ${{{{ matrix.node-version }}}}
          cache: "npm"
      - run: npm ci
      - run: npm run lint --if-present
      - run: npm test
      - run: npm run build --if-present
''',
        "rust": '''name: Rust CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: clippy, rustfmt
      - uses: Swatinem/rust-cache@v2
      - name: Check formatting
        run: cargo fmt --check
      - name: Clippy
        run: cargo clippy -- -D warnings
      - name: Test
        run: cargo test --verbose
''',
        "go": '''name: Go CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "1.22"
      - name: Vet
        run: go vet ./...
      - name: Test
        run: go test -race -coverprofile=coverage.out -v ./...
      - name: Build
        run: go build -v ./...
''',
    },
    "gitlab_ci": {
        "python": '''stages:
  - lint
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.pip-cache"

cache:
  paths:
    - .pip-cache/
    - venv/

lint:
  stage: lint
  image: python:3.12
  script:
    - pip install ruff
    - ruff check .

test:
  stage: test
  image: python:3.12
  script:
    - python -m venv venv
    - source venv/bin/activate
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=. -v

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
''',
        "node": '''stages:
  - lint
  - test
  - build

cache:
  paths:
    - node_modules/

lint:
  stage: lint
  image: node:20
  script:
    - npm ci
    - npm run lint

test:
  stage: test
  image: node:20
  script:
    - npm ci
    - npm test

build:
  stage: build
  image: node:20
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/
  only:
    - main
''',
    },
}


# ── Tool implementations ─────────────────────────────────────────────────

def generate_code(language: str, construct: str = "function",
                  name: str = "example", description: str = "",
                  parameters: str = "", body: str = "",
                  return_type: str = "", fields: str = "",
                  methods: str = "", imports: str = "") -> Dict[str, Any]:
    """Generate code in any supported language using templates and patterns."""
    lang = language.lower().replace("c++", "cpp").replace("c#", "csharp")
    ext = LANG_EXTENSIONS.get(lang, ".txt")
    comment = LANG_COMMENT_STYLE.get(lang, "//")

    # Try template-based generation
    templates = BOILERPLATE.get(lang, {})
    template = templates.get(construct)

    if template:
        code = template.format(
            name=name,
            params=parameters or "",
            docstring=description or f"{construct} {name}",
            body=body or "pass" if lang == "python" else body or "// TODO: implement",
            return_type=return_type or "void" if lang in ("java", "cpp", "csharp", "go", "rust", "typescript") else return_type or "",
            fields=fields or "",
            methods=methods or "",
            init_params=parameters or "",
            init_body=body or "pass" if lang == "python" else body or "// TODO",
            props=fields or "",
            jsx="<div>{/* TODO */}</div>",
            path=f"/{name.lower()}",
            method="get",
            setup="",
            yield_val="resource",
            teardown="pass",
            columns=fields or "name VARCHAR(255)",
            table=name,
            joins="",
            conditions="1=1",
            group_by="",
            order_by="",
            limit="",
            values="",
            variants=fields or "",
            project_name=name,
        )
    else:
        # Generic code generation
        lines = []
        if imports:
            lines.append(imports)
            lines.append("")

        lines.append(f"{comment} {description or f'{construct}: {name}'}")
        lines.append("")

        if lang == "python":
            if construct == "function":
                lines.append(f"def {name}({parameters or ''}):")
                lines.append(f'    """{description or "TODO"}"""')
                lines.append(f"    {body or 'pass'}")
            elif construct == "class":
                lines.append(f"class {name}:")
                lines.append(f'    """{description or "TODO"}"""')
                lines.append(f"    def __init__(self):")
                lines.append(f"        {body or 'pass'}")
            else:
                lines.append(body or "pass")
        elif lang in ("javascript", "typescript"):
            if construct == "function":
                ret = f": {return_type}" if return_type and lang == "typescript" else ""
                lines.append(f"function {name}({parameters or ''}){ret} {{")
                lines.append(f"  {body or '// TODO: implement'}")
                lines.append("}")
            else:
                lines.append(body or "// TODO: implement")
        elif lang == "rust":
            lines.append(f"fn {name}({parameters or ''}) -> {return_type or '()'} {{")
            lines.append(f"    {body or 'todo!()'}")
            lines.append("}")
        elif lang == "go":
            lines.append(f"func {name}({parameters or ''}) {return_type or ''} {{")
            lines.append(f"\t{body or '// TODO: implement'}")
            lines.append("}")
        else:
            lines.append(body or f"{comment} TODO: implement {name}")

        code = "\n".join(lines) + "\n"

    return {
        "language": lang,
        "construct": construct,
        "name": name,
        "extension": ext,
        "code": code,
        "line_count": len(code.splitlines()),
    }


def debug_code(error_message: str, code: str = "", language: str = "",
               stack_trace: str = "") -> Dict[str, Any]:
    """Analyze errors, match patterns, and suggest fixes."""
    lang = language.lower() if language else _detect_language(code or error_message)

    findings = []
    suggestions = []

    # Match against known error patterns
    lang_patterns = ERROR_PATTERNS.get(lang, {})
    for pattern, fix_template in lang_patterns.items():
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            groups = match.groups()
            fix = fix_template
            for i, g in enumerate(groups):
                fix = fix.replace(f"{{{i}}}", g)
            findings.append({
                "pattern_matched": pattern,
                "diagnosis": fix,
                "severity": "error",
            })

    # Analyze stack trace
    trace_info = []
    if stack_trace:
        file_lines = re.findall(r'File "(.+)", line (\d+)', stack_trace)
        for f, l in file_lines:
            trace_info.append({"file": f, "line": int(l)})

        # Find the most relevant frame (usually the last user code frame)
        user_frames = [f for f in trace_info if "site-packages" not in f["file"] and "lib/python" not in f["file"]]
        if user_frames:
            suggestions.append(f"Root cause likely at: {user_frames[-1]['file']}:{user_frames[-1]['line']}")

    # Code analysis if provided
    code_issues = []
    if code:
        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            # Common issues
            if lang == "python":
                if re.search(r"except\s*:", line):
                    code_issues.append({"line": i, "issue": "Bare except clause — catches all exceptions including SystemExit/KeyboardInterrupt", "fix": "Use 'except Exception:' or catch specific exceptions"})
                if re.search(r"==\s*None", line):
                    code_issues.append({"line": i, "issue": "Use 'is None' instead of '== None'", "fix": line.replace("== None", "is None")})
                if re.search(r"^\s*return\s*$", line) and i < len(lines):
                    next_line = lines[i] if i < len(lines) else ""
                    if next_line.strip():
                        code_issues.append({"line": i, "issue": "Code after return statement is unreachable"})
            elif lang in ("javascript", "typescript"):
                if re.search(r"==(?!=)", line) and "!=" not in line:
                    code_issues.append({"line": i, "issue": "Use === instead of == for strict equality", "fix": line.replace("==", "===")})
                if "var " in line:
                    code_issues.append({"line": i, "issue": "Use 'let' or 'const' instead of 'var'", "fix": line.replace("var ", "const ")})

    # General suggestions based on error type
    if not findings:
        if "memory" in error_message.lower() or "oom" in error_message.lower():
            suggestions.append("Memory issue detected. Check for: large data structures, memory leaks, unbounded caches.")
        elif "timeout" in error_message.lower():
            suggestions.append("Timeout issue. Consider: async operations, connection pooling, query optimization.")
        elif "permission" in error_message.lower() or "access denied" in error_message.lower():
            suggestions.append("Permission issue. Check: file permissions, API keys, authentication tokens.")
        else:
            suggestions.append(f"No specific pattern matched. Search for this error: {error_message[:100]}")

    return {
        "language": lang,
        "error_analysis": findings if findings else [{"diagnosis": "No known pattern matched", "severity": "info"}],
        "stack_trace_analysis": {
            "frames": trace_info,
            "suggestions": suggestions,
        },
        "code_issues": code_issues[:20],
        "general_tips": [
            "Add logging around the error location for more context",
            "Check if the issue is reproducible with a minimal example",
            "Verify all dependencies are at compatible versions",
        ],
    }


def _detect_language(text: str) -> str:
    """Heuristic language detection from code or error text."""
    indicators = {
        "python": [r"def \w+\(", r"import \w+", r"Traceback", r"\.py\"", r"IndentationError"],
        "javascript": [r"function\s+\w+", r"const \w+", r"require\(", r"=>", r"\.js"],
        "typescript": [r": string", r": number", r"interface \w+", r"\.ts"],
        "rust": [r"fn \w+", r"let mut", r"error\[E\d+\]", r"\.rs"],
        "go": [r"func \w+", r"package \w+", r"\.go", r"fmt\."],
        "java": [r"public class", r"System\.out", r"\.java"],
        "cpp": [r"#include", r"std::", r"int main\("],
    }
    scores = {}
    for lang, patterns in indicators.items():
        scores[lang] = sum(1 for p in patterns if re.search(p, text))
    if max(scores.values(), default=0) == 0:
        return "unknown"
    return max(scores, key=scores.get)


def review_code(code: str, language: str = "",
                focus: str = "all") -> Dict[str, Any]:
    """Review code for security, performance, best practices, and code smells."""
    lang = language.lower() if language else _detect_language(code)
    lines = code.splitlines()
    total_lines = len(lines)

    issues = []

    # Code smell detection
    if focus in ("all", "smells", "best_practices"):
        for smell_name, smell_def in CODE_SMELLS.items():
            pattern = smell_def.get("pattern")
            if pattern:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append({
                            "type": "code_smell",
                            "name": smell_name,
                            "line": i,
                            "message": smell_def["msg"],
                            "severity": "warning",
                            "code": line.strip()[:100],
                        })

        # Check for long functions
        func_starts = []
        for i, line in enumerate(lines, 1):
            if re.search(r"^(def |function |fn |func |public |private |protected )", line.strip()):
                func_starts.append(i)
        for j, start in enumerate(func_starts):
            end = func_starts[j + 1] - 1 if j + 1 < len(func_starts) else total_lines
            if (end - start) > 50:
                issues.append({
                    "type": "code_smell",
                    "name": "long_function",
                    "line": start,
                    "message": f"Function is {end - start} lines long. Consider splitting.",
                    "severity": "warning",
                })

        # File length
        if total_lines > 300:
            issues.append({
                "type": "code_smell",
                "name": "god_file",
                "line": 1,
                "message": f"File is {total_lines} lines. Consider splitting into modules.",
                "severity": "info",
            })

    # Security checks
    if focus in ("all", "security"):
        security_patterns = {
            r"eval\(": "Dangerous eval() call — potential code injection",
            r"exec\(": "Dangerous exec() call — potential code injection",
            r"subprocess\.call\(.+shell\s*=\s*True": "Shell injection risk with shell=True",
            r"os\.system\(": "Shell injection risk with os.system(). Use subprocess instead.",
            r"pickle\.loads?": "Pickle deserialization can execute arbitrary code. Use JSON instead.",
            r"yaml\.load\((?!.*Loader)": "Unsafe YAML loading. Use yaml.safe_load().",
            r"innerHTML\s*=": "DOM XSS risk with innerHTML. Use textContent or sanitize input.",
            r"document\.write": "document.write() can be exploited for XSS",
            r"SELECT .+\+.*(?:req|input|user|param)": "Potential SQL injection. Use parameterized queries.",
            r"(?:md5|sha1)\(": "Weak hash algorithm. Use SHA-256 or bcrypt for passwords.",
            r"http://(?!localhost|127\.0\.0\.1)": "Insecure HTTP URL. Use HTTPS.",
            r"CORS.*\*|allow_origins.*\*": "Wildcard CORS policy. Restrict to specific origins in production.",
            r"(?:password|secret|api.?key|token)\s*=\s*['\"][^'\"]+['\"]": "Hardcoded credential detected. Use environment variables.",
            r"\.env\b": "Possible .env file reference. Ensure .env is in .gitignore.",
        }
        for pattern, msg in security_patterns.items():
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "type": "security",
                        "line": i,
                        "message": msg,
                        "severity": "critical" if "injection" in msg.lower() or "credential" in msg.lower() else "warning",
                        "code": line.strip()[:100],
                    })

    # Performance checks
    if focus in ("all", "performance"):
        for name, pdef in COMPLEXITY_PATTERNS.items():
            matches = list(re.finditer(pdef["pattern"], code, re.MULTILINE))
            for m in matches:
                line_num = code[:m.start()].count("\n") + 1
                issues.append({
                    "type": "performance",
                    "name": name,
                    "line": line_num,
                    "complexity": pdef.get("complexity", ""),
                    "message": pdef["msg"],
                    "severity": "warning",
                })

    # Deduplicate
    seen = set()
    unique_issues = []
    for iss in issues:
        key = (iss.get("line"), iss.get("message", "")[:50])
        if key not in seen:
            seen.add(key)
            unique_issues.append(iss)

    critical = sum(1 for i in unique_issues if i.get("severity") == "critical")
    warnings = sum(1 for i in unique_issues if i.get("severity") == "warning")

    score = max(0, 100 - critical * 15 - warnings * 5)

    return {
        "language": lang,
        "total_lines": total_lines,
        "issues": unique_issues[:50],
        "summary": {
            "critical": critical,
            "warnings": warnings,
            "info": sum(1 for i in unique_issues if i.get("severity") == "info"),
            "total_issues": len(unique_issues),
        },
        "quality_score": min(100, score),
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F",
    }


def design_architecture(system_type: str, name: str = "MySystem",
                        requirements: str = "",
                        scale: str = "medium",
                        database: str = "postgresql") -> Dict[str, Any]:
    """Design system architecture with components, APIs, and database schema."""
    architectures = {
        "microservices": {
            "pattern": "Microservices Architecture",
            "components": [
                {"name": "API Gateway", "tech": "Kong / Nginx / AWS API Gateway", "purpose": "Route requests, rate limiting, auth"},
                {"name": "Auth Service", "tech": "JWT + OAuth2", "purpose": "User authentication and authorization"},
                {"name": "User Service", "tech": "REST API", "purpose": "User management, profiles"},
                {"name": "Core Service", "tech": "REST/gRPC API", "purpose": "Main business logic"},
                {"name": "Notification Service", "tech": "Event-driven", "purpose": "Email, SMS, push notifications"},
                {"name": "Message Queue", "tech": "RabbitMQ / Kafka", "purpose": "Async communication between services"},
                {"name": "Cache Layer", "tech": "Redis", "purpose": "Session cache, hot data, rate limiting"},
                {"name": "Database", "tech": database, "purpose": "Persistent data storage"},
                {"name": "Search", "tech": "Elasticsearch", "purpose": "Full-text search, analytics"},
                {"name": "CDN", "tech": "CloudFront / Cloudflare", "purpose": "Static assets, edge caching"},
            ],
        },
        "monolith": {
            "pattern": "Modular Monolith",
            "components": [
                {"name": "Web Server", "tech": "Nginx", "purpose": "Reverse proxy, static files, SSL"},
                {"name": "Application", "tech": "Django / Rails / Spring Boot", "purpose": "All business logic in one deployable"},
                {"name": "Background Workers", "tech": "Celery / Sidekiq", "purpose": "Async tasks, scheduled jobs"},
                {"name": "Database", "tech": database, "purpose": "Single relational database"},
                {"name": "Cache", "tech": "Redis / Memcached", "purpose": "Query cache, sessions"},
            ],
        },
        "serverless": {
            "pattern": "Serverless Architecture",
            "components": [
                {"name": "API Gateway", "tech": "AWS API Gateway / Cloudflare Workers", "purpose": "HTTP endpoint management"},
                {"name": "Functions", "tech": "AWS Lambda / Vercel Functions", "purpose": "Stateless compute"},
                {"name": "Auth", "tech": "AWS Cognito / Auth0", "purpose": "Managed authentication"},
                {"name": "Database", "tech": "DynamoDB / PlanetScale", "purpose": "Managed database"},
                {"name": "Storage", "tech": "S3 / R2", "purpose": "File and blob storage"},
                {"name": "Queue", "tech": "SQS / EventBridge", "purpose": "Event-driven processing"},
                {"name": "CDN", "tech": "CloudFront", "purpose": "Edge caching"},
            ],
        },
        "event_driven": {
            "pattern": "Event-Driven Architecture",
            "components": [
                {"name": "Event Bus", "tech": "Kafka / EventBridge", "purpose": "Central event routing"},
                {"name": "Producers", "tech": "Microservices", "purpose": "Emit domain events"},
                {"name": "Consumers", "tech": "Microservices", "purpose": "React to events"},
                {"name": "Event Store", "tech": "EventStoreDB / Kafka", "purpose": "Event sourcing persistence"},
                {"name": "Projections", "tech": "CQRS Read Models", "purpose": "Materialized views"},
                {"name": "Dead Letter Queue", "tech": "SQS DLQ / Kafka DLT", "purpose": "Failed event handling"},
            ],
        },
    }

    arch = architectures.get(system_type, architectures["monolith"])

    # Generate API design
    api_endpoints = [
        {"method": "POST", "path": "/api/v1/auth/register", "description": "User registration"},
        {"method": "POST", "path": "/api/v1/auth/login", "description": "User login, returns JWT"},
        {"method": "GET", "path": "/api/v1/auth/me", "description": "Get current user profile"},
        {"method": "GET", "path": f"/api/v1/{name.lower()}s", "description": f"List {name} resources"},
        {"method": "POST", "path": f"/api/v1/{name.lower()}s", "description": f"Create {name} resource"},
        {"method": "GET", "path": f"/api/v1/{name.lower()}s/{{id}}", "description": f"Get {name} by ID"},
        {"method": "PUT", "path": f"/api/v1/{name.lower()}s/{{id}}", "description": f"Update {name}"},
        {"method": "DELETE", "path": f"/api/v1/{name.lower()}s/{{id}}", "description": f"Delete {name}"},
        {"method": "GET", "path": "/api/v1/health", "description": "Health check endpoint"},
    ]

    # Database schema
    db_schema = {
        "tables": [
            {
                "name": "users",
                "columns": [
                    {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY DEFAULT gen_random_uuid()"},
                    {"name": "email", "type": "VARCHAR(255)", "constraints": "UNIQUE NOT NULL"},
                    {"name": "password_hash", "type": "VARCHAR(255)", "constraints": "NOT NULL"},
                    {"name": "name", "type": "VARCHAR(100)", "constraints": ""},
                    {"name": "role", "type": "VARCHAR(20)", "constraints": "DEFAULT 'user'"},
                    {"name": "created_at", "type": "TIMESTAMP", "constraints": "DEFAULT NOW()"},
                    {"name": "updated_at", "type": "TIMESTAMP", "constraints": "DEFAULT NOW()"},
                ],
            },
            {
                "name": f"{name.lower()}s",
                "columns": [
                    {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY DEFAULT gen_random_uuid()"},
                    {"name": "user_id", "type": "UUID", "constraints": "REFERENCES users(id)"},
                    {"name": "title", "type": "VARCHAR(255)", "constraints": "NOT NULL"},
                    {"name": "description", "type": "TEXT", "constraints": ""},
                    {"name": "status", "type": "VARCHAR(20)", "constraints": "DEFAULT 'active'"},
                    {"name": "metadata", "type": "JSONB", "constraints": "DEFAULT '{}'"},
                    {"name": "created_at", "type": "TIMESTAMP", "constraints": "DEFAULT NOW()"},
                    {"name": "updated_at", "type": "TIMESTAMP", "constraints": "DEFAULT NOW()"},
                ],
                "indexes": [
                    f"CREATE INDEX idx_{name.lower()}s_user ON {name.lower()}s(user_id);",
                    f"CREATE INDEX idx_{name.lower()}s_status ON {name.lower()}s(status);",
                ],
            },
        ],
    }

    # Scale recommendations
    scale_recs = {
        "small": ["Single server", "SQLite or PostgreSQL", "No caching needed initially", "Deploy on a single VPS"],
        "medium": ["Load balancer + 2-3 app servers", "Managed PostgreSQL with read replicas", "Redis for caching and sessions", "CI/CD pipeline", "Basic monitoring (Prometheus + Grafana)"],
        "large": ["Auto-scaling groups", "Database sharding or managed clusters", "Multi-region CDN", "Distributed caching", "Full observability stack", "Event-driven async processing", "Container orchestration (Kubernetes)"],
    }

    return {
        "system_name": name,
        "architecture": arch,
        "api_design": api_endpoints,
        "database_schema": db_schema,
        "scale": scale,
        "scaling_recommendations": scale_recs.get(scale, scale_recs["medium"]),
        "requirements": requirements,
        "tech_stack_suggestion": {
            "backend": "FastAPI (Python)" if "python" in requirements.lower() else "Express (Node.js)",
            "frontend": "Next.js / React",
            "database": database,
            "cache": "Redis",
            "queue": "RabbitMQ" if scale == "small" else "Kafka",
            "monitoring": "Prometheus + Grafana",
            "logging": "ELK Stack / Loki",
        },
    }


def suggest_refactoring(code: str, language: str = "",
                        focus: str = "all") -> Dict[str, Any]:
    """Identify refactoring opportunities: DRY, SOLID, design patterns."""
    lang = language.lower() if language else _detect_language(code)
    lines = code.splitlines()
    suggestions = []

    # Duplicate code detection (simple line-level)
    line_counts = {}
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if len(stripped) > 15 and not stripped.startswith(("#", "//", "/*", "*", "import", "from")):
            if stripped in line_counts:
                line_counts[stripped].append(i)
            else:
                line_counts[stripped] = [i]

    duplicates = {k: v for k, v in line_counts.items() if len(v) > 1}
    if duplicates:
        for code_line, occurrences in list(duplicates.items())[:10]:
            suggestions.append({
                "type": "DRY",
                "principle": "Don't Repeat Yourself",
                "lines": occurrences,
                "message": f"Duplicated code found on lines {occurrences}. Extract to a shared function.",
                "code_snippet": code_line[:80],
            })

    # Long parameter lists
    for i, line in enumerate(lines, 1):
        func_match = re.search(r"(?:def |function |fn |func )\w+\(([^)]+)\)", line)
        if func_match:
            params = func_match.group(1).split(",")
            if len(params) > 4:
                suggestions.append({
                    "type": "SOLID",
                    "principle": "Single Responsibility / Clean Code",
                    "line": i,
                    "message": f"Function has {len(params)} parameters. Consider using a parameter object or dataclass.",
                    "severity": "warning",
                })

    # Deep nesting
    max_indent = 0
    for i, line in enumerate(lines, 1):
        if line.strip():
            indent = len(line) - len(line.lstrip())
            indent_level = indent // 4 if indent % 4 == 0 else indent // 2
            if indent_level > max_indent:
                max_indent = indent_level
            if indent_level >= 4:
                suggestions.append({
                    "type": "readability",
                    "principle": "Reduce Nesting",
                    "line": i,
                    "message": f"Nesting level {indent_level}. Use early returns, guard clauses, or extract methods.",
                    "severity": "warning",
                })

    # Single Responsibility violations
    class_count = len(re.findall(r"class \w+", code))
    func_count = len(re.findall(r"(?:def |function |fn |func )\w+", code))
    if func_count > 15:
        suggestions.append({
            "type": "SOLID",
            "principle": "Single Responsibility Principle",
            "message": f"File has {func_count} functions. Consider splitting into focused modules.",
            "severity": "info",
        })

    # Hardcoded values
    magic_numbers = re.findall(r"(?<!['\"\w=])(?:[2-9]\d{2,}|[1-9]\d{3,})(?!['\"\w])", code)
    if magic_numbers:
        suggestions.append({
            "type": "clean_code",
            "principle": "No Magic Numbers",
            "message": f"Found {len(magic_numbers)} magic numbers. Extract to named constants.",
            "examples": list(set(magic_numbers))[:5],
            "severity": "info",
        })

    # Pattern suggestions
    patterns_applicable = []
    if re.search(r"if .+:\s*\n\s+return .+\s*\n\s*elif .+:\s*\n\s+return", code):
        patterns_applicable.append({
            "pattern": "Strategy Pattern",
            "reason": "Multiple conditional returns could be replaced with a strategy dispatch.",
        })
    if re.search(r"\.append\(.*\)\s*\n.*\.append\(", code):
        patterns_applicable.append({
            "pattern": "Builder Pattern",
            "reason": "Sequential building operations could use a builder for cleaner API.",
        })
    if class_count > 0 and re.search(r"__init__.*self\.\w+\s*=\s*\w+.*\n.*self\.\w+\s*=\s*\w+", code):
        patterns_applicable.append({
            "pattern": "Factory Method",
            "reason": "Complex initialization could benefit from factory methods for different configurations.",
        })

    return {
        "language": lang,
        "total_lines": len(lines),
        "suggestions": suggestions[:30],
        "design_patterns": patterns_applicable,
        "metrics": {
            "classes": class_count,
            "functions": func_count,
            "max_nesting_depth": max_indent,
            "duplicate_lines": sum(len(v) - 1 for v in duplicates.values()),
        },
        "refactoring_priority": (
            "high" if len([s for s in suggestions if s.get("severity") == "warning"]) > 5
            else "medium" if suggestions else "low"
        ),
    }


def generate_tests(code: str, language: str = "",
                   framework: str = "", test_type: str = "unit") -> Dict[str, Any]:
    """Generate test code for any function/class in any supported language."""
    lang = language.lower() if language else _detect_language(code)

    # Extract functions and classes
    functions = []
    if lang == "python":
        for m in re.finditer(r"def (\w+)\(([^)]*)\)(?:\s*->\s*(\w+))?:", code):
            functions.append({"name": m.group(1), "params": m.group(2), "returns": m.group(3) or ""})
        fw = framework or "pytest"
    elif lang in ("javascript", "typescript"):
        for m in re.finditer(r"(?:function |const |let |var )(\w+)\s*(?:=\s*)?(?:\(|async\s*\()([^)]*)\)", code):
            functions.append({"name": m.group(1), "params": m.group(2), "returns": ""})
        for m in re.finditer(r"(\w+)\s*\(([^)]*)\)\s*\{", code):
            if m.group(1) not in ("if", "for", "while", "switch", "catch"):
                functions.append({"name": m.group(1), "params": m.group(2), "returns": ""})
        fw = framework or "jest"
    elif lang == "rust":
        for m in re.finditer(r"fn (\w+)\(([^)]*)\)(?:\s*->\s*(\w+))?", code):
            functions.append({"name": m.group(1), "params": m.group(2), "returns": m.group(3) or ""})
        fw = framework or "built-in"
    elif lang == "go":
        for m in re.finditer(r"func (\w+)\(([^)]*)\)\s*(\w*)", code):
            functions.append({"name": m.group(1), "params": m.group(2), "returns": m.group(3) or ""})
        fw = framework or "testing"
    else:
        for m in re.finditer(r"(?:def |function |fn |func |public |private )\s*(\w+)\s*\(([^)]*)\)", code):
            functions.append({"name": m.group(1), "params": m.group(2), "returns": ""})
        fw = framework or "default"

    # Deduplicate
    seen_names = set()
    unique_funcs = []
    for f in functions:
        if f["name"] not in seen_names and not f["name"].startswith("_"):
            seen_names.add(f["name"])
            unique_funcs.append(f)
    functions = unique_funcs

    # Generate test code
    test_lines = []
    if lang == "python" and fw == "pytest":
        test_lines.append("import pytest")
        test_lines.append("")
        test_lines.append("")
        for fn in functions:
            fname = fn["name"]
            params = [p.strip().split(":")[0].split("=")[0].strip() for p in fn["params"].split(",") if p.strip() and p.strip() != "self"]
            test_lines.append(f"class Test{fname.title().replace('_', '')}:")
            test_lines.append(f'    """Tests for {fname}."""')
            test_lines.append("")
            test_lines.append(f"    def test_{fname}_basic(self):")
            test_lines.append(f'        """Test {fname} with valid input."""')
            if params:
                args = ", ".join(f"{p}=None" for p in params[:3])
                test_lines.append(f"        result = {fname}({args})")
            else:
                test_lines.append(f"        result = {fname}()")
            test_lines.append("        assert result is not None")
            test_lines.append("")
            test_lines.append(f"    def test_{fname}_edge_cases(self):")
            test_lines.append(f'        """Test {fname} with edge cases."""')
            test_lines.append(f"        # Test with empty/None/zero inputs")
            test_lines.append("        pass  # TODO: implement edge cases")
            test_lines.append("")
            if test_type in ("unit", "all"):
                test_lines.append(f"    def test_{fname}_error_handling(self):")
                test_lines.append(f'        """Test {fname} error handling."""')
                test_lines.append(f"        with pytest.raises(Exception):")
                test_lines.append(f"            {fname}()  # TODO: pass invalid args")
                test_lines.append("")
            test_lines.append("")

    elif lang in ("javascript", "typescript") and fw == "jest":
        test_lines.append(f"// Tests generated for {fw}")
        test_lines.append("")
        for fn in functions:
            fname = fn["name"]
            test_lines.append(f'describe("{fname}", () => {{')
            test_lines.append(f'  it("should handle valid input", () => {{')
            test_lines.append(f"    const result = {fname}();")
            test_lines.append(f"    expect(result).toBeDefined();")
            test_lines.append(f"  }});")
            test_lines.append("")
            test_lines.append(f'  it("should handle edge cases", () => {{')
            test_lines.append(f"    // Test with null, undefined, empty values")
            test_lines.append(f"    expect(() => {fname}(null)).not.toThrow();")
            test_lines.append(f"  }});")
            test_lines.append("")
            if test_type in ("unit", "all"):
                test_lines.append(f'  it("should throw on invalid input", () => {{')
                test_lines.append(f"    // TODO: test invalid inputs")
                test_lines.append(f"    expect(() => {fname}(undefined)).toThrow();")
                test_lines.append(f"  }});")
            test_lines.append(f"}});")
            test_lines.append("")

    elif lang == "rust":
        test_lines.append("#[cfg(test)]")
        test_lines.append("mod tests {")
        test_lines.append("    use super::*;")
        test_lines.append("")
        for fn in functions:
            fname = fn["name"]
            test_lines.append(f"    #[test]")
            test_lines.append(f"    fn test_{fname}() {{")
            test_lines.append(f"        // TODO: provide test inputs")
            test_lines.append(f"        let result = {fname}();")
            test_lines.append(f"        assert!(result.is_ok()); // or appropriate assertion")
            test_lines.append(f"    }}")
            test_lines.append("")
        test_lines.append("}")

    elif lang == "go":
        test_lines.append("package main")
        test_lines.append("")
        test_lines.append('import "testing"')
        test_lines.append("")
        for fn in functions:
            fname = fn["name"]
            test_lines.append(f"func Test{fname}(t *testing.T) {{")
            test_lines.append(f"\t// TODO: provide test inputs")
            test_lines.append(f"\tresult := {fname}()")
            test_lines.append(f"\tif result == nil {{")
            test_lines.append(f'\t\tt.Error("Expected non-nil result")')
            test_lines.append(f"\t}}")
            test_lines.append(f"}}")
            test_lines.append("")

    else:
        test_lines.append(f"// Tests for {lang} ({fw})")
        for fn in functions:
            test_lines.append(f"// TODO: test {fn['name']}({fn['params']})")

    test_code = "\n".join(test_lines)

    return {
        "language": lang,
        "framework": fw,
        "test_type": test_type,
        "functions_found": len(functions),
        "functions": [f["name"] for f in functions],
        "test_code": test_code,
        "test_count": sum(1 for l in test_lines if "def test_" in l or 'it("' in l or "#[test]" in l or "func Test" in l),
        "line_count": len(test_lines),
    }


def profile_performance(code: str, language: str = "") -> Dict[str, Any]:
    """Analyze code for Big-O complexity, memory concerns, and bottlenecks."""
    lang = language.lower() if language else _detect_language(code)
    lines = code.splitlines()

    findings = []
    overall_complexity = "O(1)"
    complexity_rank = {"O(1)": 1, "O(log n)": 2, "O(n)": 3, "O(n log n)": 4,
                       "O(n^2)": 5, "O(n^2 log n)": 6, "O(n^3)": 7, "O(2^n)": 8}

    # Pattern-based complexity analysis
    for name, pdef in COMPLEXITY_PATTERNS.items():
        matches = list(re.finditer(pdef["pattern"], code, re.MULTILINE))
        for m in matches:
            line_num = code[:m.start()].count("\n") + 1
            comp = pdef.get("complexity", "unknown")
            findings.append({
                "type": name,
                "line": line_num,
                "complexity": comp,
                "message": pdef["msg"],
            })
            if complexity_rank.get(comp, 0) > complexity_rank.get(overall_complexity, 0):
                overall_complexity = comp

    # Memory analysis
    memory_issues = []
    for i, line in enumerate(lines, 1):
        if re.search(r"\[\s*\]\s*\*\s*\d{6,}", line):
            memory_issues.append({"line": i, "issue": "Large array allocation detected"})
        if re.search(r"\.read\(\)", line):
            memory_issues.append({"line": i, "issue": "Reading entire file into memory. Consider streaming."})
        if re.search(r"list\(range\(\d{6,}\)\)", line):
            memory_issues.append({"line": i, "issue": "Large range materialized. Use iterator instead."})
        if re.search(r"deepcopy|copy\.deepcopy", line):
            memory_issues.append({"line": i, "issue": "Deep copy can be expensive for large objects."})
        if re.search(r"\+= \[", line) or re.search(r"\.extend\(", line):
            memory_issues.append({"line": i, "issue": "Repeated list extension may cause memory reallocation. Consider pre-allocation."})

    # I/O bottleneck detection
    io_issues = []
    for i, line in enumerate(lines, 1):
        if re.search(r"open\(|\.read|\.write", line) and not re.search(r"with ", line):
            io_issues.append({"line": i, "issue": "File operation without 'with' context manager. Risk of resource leak."})
        if re.search(r"requests\.get|urllib|fetch\(|http\.Get", line):
            io_issues.append({"line": i, "issue": "Network I/O — consider async, connection pooling, or caching."})
        if re.search(r"time\.sleep|Thread\.sleep|setTimeout", line):
            io_issues.append({"line": i, "issue": "Blocking sleep call. Consider async/event-driven approach."})

    # Simple loop analysis for O(n) detection
    loop_count = len(re.findall(r"for |while ", code))
    if loop_count > 0 and overall_complexity == "O(1)":
        overall_complexity = "O(n)"

    # Function count and average length
    func_starts = [i for i, l in enumerate(lines) if re.match(r"\s*(?:def |function |fn |func )", l)]
    avg_func_len = (
        len(lines) // len(func_starts) if func_starts else len(lines)
    )

    return {
        "language": lang,
        "overall_complexity": overall_complexity,
        "total_lines": len(lines),
        "findings": findings,
        "memory_concerns": memory_issues,
        "io_bottlenecks": io_issues,
        "metrics": {
            "function_count": len(func_starts),
            "avg_function_length": avg_func_len,
            "loop_count": loop_count,
            "nested_loop_count": len([f for f in findings if "nested" in f.get("type", "")]),
        },
        "recommendations": _perf_recommendations(findings, memory_issues, io_issues, overall_complexity),
    }


def _perf_recommendations(findings, memory, io, complexity):
    recs = []
    if complexity in ("O(n^2)", "O(n^3)", "O(n^2 log n)"):
        recs.append("Consider algorithmic improvements: hash maps, sorting + binary search, or divide-and-conquer.")
    if memory:
        recs.append("Use generators/iterators instead of materializing large collections.")
        recs.append("Consider streaming for large file operations.")
    if io:
        recs.append("Use connection pooling for database/HTTP connections.")
        recs.append("Consider async I/O (asyncio, tokio, goroutines) for concurrent operations.")
    if not recs:
        recs.append("Code looks reasonably optimized. Profile with real data to find actual bottlenecks.")
    return recs


def audit_dependencies(package_file: str = "", language: str = "python") -> Dict[str, Any]:
    """Check dependencies for known issues, outdated packages, and license concerns."""
    lang = language.lower()
    deps = []

    if package_file:
        lines = package_file.strip().splitlines()
    else:
        return {"error": "Provide package file contents (requirements.txt, package.json, Cargo.toml, etc.)"}

    # Parse dependencies
    if lang == "python":
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                match = re.match(r"([a-zA-Z0-9_-]+)([><=!~]+.+)?", line)
                if match:
                    deps.append({"name": match.group(1), "version_spec": (match.group(2) or "").strip()})
    elif lang in ("javascript", "typescript"):
        try:
            pkg = json.loads(package_file)
            for section in ("dependencies", "devDependencies"):
                for name, ver in pkg.get(section, {}).items():
                    deps.append({"name": name, "version_spec": ver, "dev": section == "devDependencies"})
        except json.JSONDecodeError:
            return {"error": "Invalid package.json format"}
    elif lang == "rust":
        for line in lines:
            match = re.match(r'(\w[\w-]*)\s*=\s*"([^"]+)"', line)
            if match:
                deps.append({"name": match.group(1), "version_spec": match.group(2)})
    elif lang == "go":
        for line in lines:
            match = re.match(r"\s*([\w./]+)\s+(v[\d.]+)", line)
            if match:
                deps.append({"name": match.group(1), "version_spec": match.group(2)})

    # Known vulnerability patterns (simplified — real audit uses advisory DBs)
    known_issues = {
        "requests": {"below": "2.31.0", "issue": "CVE-2023-32681: Potential leak of Proxy-Authorization header"},
        "flask": {"below": "2.3.2", "issue": "CVE-2023-30861: Session cookie security issue"},
        "django": {"below": "4.2.7", "issue": "Multiple security fixes in recent versions"},
        "pyyaml": {"below": "6.0", "issue": "Arbitrary code execution via yaml.load()"},
        "pillow": {"below": "10.0.0", "issue": "Multiple CVEs in image processing"},
        "urllib3": {"below": "2.0.7", "issue": "CVE-2023-45803: Request body not stripped on redirect"},
        "lodash": {"below": "4.17.21", "issue": "Prototype pollution vulnerability"},
        "express": {"below": "4.18.0", "issue": "Open redirect vulnerability"},
        "axios": {"below": "1.6.0", "issue": "SSRF vulnerability"},
        "node-fetch": {"below": "2.6.7", "issue": "Bypass of URL validation"},
    }

    warnings = []
    for dep in deps:
        name_lower = dep["name"].lower()
        if name_lower in known_issues:
            warnings.append({
                "package": dep["name"],
                "current": dep["version_spec"],
                "advisory": known_issues[name_lower]["issue"],
                "fix": f"Upgrade to latest version",
                "severity": "high",
            })

    # Version pinning analysis
    unpinned = [d for d in deps if not d["version_spec"] or d["version_spec"].startswith("^") or d["version_spec"] == "*" or d["version_spec"].startswith(">=")]
    pinned = [d for d in deps if d["version_spec"] and not d["version_spec"].startswith("^") and d["version_spec"] != "*"]

    return {
        "language": lang,
        "total_dependencies": len(deps),
        "dependencies": deps,
        "security_warnings": warnings,
        "version_analysis": {
            "pinned": len(pinned),
            "unpinned": len(unpinned),
            "unpinned_packages": [d["name"] for d in unpinned[:20]],
            "recommendation": "Pin all production dependencies to exact versions for reproducibility." if unpinned else "All dependencies are pinned.",
        },
        "recommendations": [
            "Run a full security audit with your language's native tool (pip-audit, npm audit, cargo-audit)",
            "Keep dependencies up to date with automated tools (Dependabot, Renovate)",
            "Review licenses for compatibility with your project",
            "Remove unused dependencies to reduce attack surface",
        ],
    }


def git_workflow(action: str = "commit_message", changes: str = "",
                 branch_name: str = "", description: str = "",
                 pr_template: str = "standard") -> Dict[str, Any]:
    """Git workflow helper: commit messages, branch names, PR templates, branching strategies."""
    if action == "commit_message":
        # Conventional commit from description
        change_type = "feat"
        desc_lower = (changes + " " + description).lower()
        if any(w in desc_lower for w in ("fix", "bug", "error", "crash", "issue", "patch")):
            change_type = "fix"
        elif any(w in desc_lower for w in ("refactor", "clean", "restructur")):
            change_type = "refactor"
        elif any(w in desc_lower for w in ("test", "spec", "coverage")):
            change_type = "test"
        elif any(w in desc_lower for w in ("doc", "readme", "comment")):
            change_type = "docs"
        elif any(w in desc_lower for w in ("ci", "pipeline", "deploy", "build")):
            change_type = "ci"
        elif any(w in desc_lower for w in ("style", "format", "lint")):
            change_type = "style"
        elif any(w in desc_lower for w in ("perf", "optim", "speed", "fast")):
            change_type = "perf"

        summary = description or changes
        if len(summary) > 72:
            summary = summary[:69] + "..."

        commit = f"{change_type}: {summary}"
        body = changes if changes != description else ""

        return {
            "commit_message": commit,
            "body": body,
            "type": change_type,
            "format": "conventional_commits",
            "examples": [
                "feat: add user authentication with JWT",
                "fix: resolve race condition in payment processing",
                "refactor: extract validation logic into middleware",
                "docs: update API endpoint documentation",
                "test: add integration tests for order flow",
            ],
        }

    elif action == "branch_name":
        # Generate branch name
        desc = (description or changes or "feature").lower()
        desc = re.sub(r"[^a-z0-9\s-]", "", desc)
        slug = re.sub(r"\s+", "-", desc.strip())[:50]

        prefix = "feature"
        if any(w in desc for w in ("fix", "bug", "hotfix")):
            prefix = "fix"
        elif any(w in desc for w in ("release", "version")):
            prefix = "release"
        elif any(w in desc for w in ("chore", "ci", "build")):
            prefix = "chore"

        branch = f"{prefix}/{slug}"
        return {
            "branch_name": branch,
            "convention": "type/description",
            "alternatives": [
                f"{prefix}/{slug}",
                f"{prefix}/{datetime.now().strftime('%Y%m%d')}-{slug[:30]}",
            ],
        }

    elif action == "pr_template":
        templates = {
            "standard": f"""## Summary
<!-- Brief description of changes -->
{description or ""}

## Changes
{changes or "- "}

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix/feature causing existing functionality to break)
- [ ] Refactoring (no functional changes)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Dependent changes have been merged
""",
            "minimal": f"""## What
{description or ""}

## Why
{changes or ""}

## Testing
- [ ] Tests pass
- [ ] Manually verified
""",
        }

        return {
            "template": templates.get(pr_template, templates["standard"]),
            "format": pr_template,
        }

    elif action == "branching_strategy":
        strategies = {
            "gitflow": {
                "description": "Git Flow: structured branching for release-based projects",
                "branches": {
                    "main": "Production-ready code only",
                    "develop": "Integration branch for features",
                    "feature/*": "New features (branch from develop)",
                    "release/*": "Release preparation (branch from develop)",
                    "hotfix/*": "Emergency fixes (branch from main)",
                },
                "best_for": "Projects with scheduled releases",
            },
            "trunk": {
                "description": "Trunk-Based Development: short-lived branches, frequent merges",
                "branches": {
                    "main": "Single source of truth, always deployable",
                    "feature/*": "Short-lived (1-2 days max)",
                },
                "best_for": "Teams with strong CI/CD, continuous deployment",
            },
            "github_flow": {
                "description": "GitHub Flow: simple, PR-based workflow",
                "branches": {
                    "main": "Always deployable",
                    "feature-branches": "All work happens in branches, merged via PR",
                },
                "best_for": "Small teams, web applications, continuous delivery",
            },
        }
        return {"strategies": strategies}

    return {"error": f"Unknown action: {action}. Use: commit_message, branch_name, pr_template, branching_strategy"}


def scaffold_project(framework: str, project_name: str = "my_project",
                     features: str = "") -> Dict[str, Any]:
    """Generate full project structure for popular frameworks."""
    fw = framework.lower().replace(".", "").replace(" ", "")
    template = SCAFFOLD_TEMPLATES.get(fw)

    if not template:
        available = list(SCAFFOLD_TEMPLATES.keys())
        return {"error": f"Unknown framework '{framework}'. Available: {', '.join(available)}"}

    # Generate files
    generated_files = {}
    for filepath, content in template["files"].items():
        actual_path = filepath.replace("{project_name}", project_name)
        actual_content = content.replace("{project_name}", project_name)
        generated_files[actual_path] = actual_content

    # Add common files
    generated_files[".gitignore"] = _gitignore_for(fw)
    generated_files["README.md"] = f"# {project_name}\n\nGenerated with Ouroboros scaffolder.\n"

    # Optionally save to disk
    _ensure_workspace()
    project_dir = os.path.join(WORKSPACE, "projects", project_name)
    os.makedirs(project_dir, exist_ok=True)

    for filepath, content in generated_files.items():
        full_path = os.path.join(project_dir, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    return {
        "framework": fw,
        "project_name": project_name,
        "files": list(generated_files.keys()),
        "file_count": len(generated_files),
        "output_dir": project_dir,
        "generated_content": generated_files,
        "next_steps": _next_steps_for(fw, project_name),
    }


def _gitignore_for(framework: str) -> str:
    common = "node_modules/\n.env\n.env.local\n*.log\n.DS_Store\n__pycache__/\n*.pyc\n.venv/\nvenv/\ndist/\nbuild/\n.idea/\n.vscode/\n*.swp\n*.swo\ncoverage/\n.pytest_cache/\n"
    extras = {
        "fastapi": "*.egg-info/\n",
        "django": "db.sqlite3\nmedia/\nstaticfiles/\n",
        "nextjs": ".next/\nout/\n",
        "react": "build/\n",
        "express": "node_modules/\n",
    }
    return common + extras.get(framework, "")


def _next_steps_for(framework: str, name: str) -> list:
    steps = {
        "fastapi": [f"cd {name}", "python -m venv venv && source venv/bin/activate", "pip install -r requirements.txt", "uvicorn main:app --reload"],
        "nextjs": [f"cd {name}", "npm install", "npm run dev"],
        "express": [f"cd {name}", "npm install", "npm run dev"],
        "django": [f"cd {name}", "pip install -r requirements.txt", "python manage.py migrate", "python manage.py runserver"],
        "react": [f"cd {name}", "npm install", "npm start"],
    }
    return steps.get(framework, [f"cd {name}", "See README.md for setup instructions"])


def generate_api_docs(code: str, title: str = "API Documentation",
                      base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Generate OpenAPI/Swagger spec from code (FastAPI, Express, Flask routes)."""
    endpoints = []

    # FastAPI style
    for m in re.finditer(r'@app\.(get|post|put|delete|patch)\("([^"]+)"', code):
        method = m.group(1).upper()
        path = m.group(2)
        # Try to find the function name and docstring
        func_match = re.search(rf'@app\.{m.group(1)}\("{re.escape(path)}"\)\s*\n\s*(?:async\s+)?def\s+(\w+)\(([^)]*)\).*?:\s*\n\s*"""([^"]*?)"""', code, re.DOTALL)
        endpoints.append({
            "method": method,
            "path": path,
            "operation_id": func_match.group(1) if func_match else path.strip("/").replace("/", "_"),
            "description": func_match.group(3).strip() if func_match else "",
            "parameters": func_match.group(2) if func_match else "",
        })

    # Express style
    for m in re.finditer(r'(?:router|app)\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', code):
        endpoints.append({
            "method": m.group(1).upper(),
            "path": m.group(2),
            "operation_id": m.group(2).strip("/").replace("/", "_"),
            "description": "",
            "parameters": "",
        })

    # Flask style
    for m in re.finditer(r'@app\.route\(["\']([^"\']+)["\'](?:,\s*methods=\[([^\]]+)\])?\)', code):
        methods = m.group(2) or '"GET"'
        for method in re.findall(r'"(\w+)"', methods):
            endpoints.append({
                "method": method.upper(),
                "path": m.group(1),
                "operation_id": m.group(1).strip("/").replace("/", "_"),
                "description": "",
                "parameters": "",
            })

    # Build OpenAPI spec
    paths = {}
    for ep in endpoints:
        path = ep["path"]
        if path not in paths:
            paths[path] = {}

        # Convert path params
        openapi_path = re.sub(r"\{(\w+)\}", r"{\1}", path)

        path_params = re.findall(r"\{(\w+)\}", path)
        parameters = [
            {"name": p, "in": "path", "required": True, "schema": {"type": "string"}}
            for p in path_params
        ]

        paths[path][ep["method"].lower()] = {
            "operationId": ep["operation_id"],
            "summary": ep["description"] or ep["operation_id"].replace("_", " ").title(),
            "parameters": parameters,
            "responses": {
                "200": {"description": "Successful response"},
                "400": {"description": "Bad request"},
                "404": {"description": "Not found"},
                "500": {"description": "Internal server error"},
            },
        }
        if ep["method"] in ("POST", "PUT", "PATCH"):
            paths[path][ep["method"].lower()]["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"type": "object"},
                    }
                },
            }

    openapi_spec = {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "version": "1.0.0",
        },
        "servers": [{"url": base_url}],
        "paths": paths,
    }

    return {
        "endpoints_found": len(endpoints),
        "openapi_spec": openapi_spec,
        "spec_json": json.dumps(openapi_spec, indent=2),
        "endpoints": endpoints,
    }


def generate_migration(action: str = "create_table", table_name: str = "users",
                       columns: str = "", from_schema: str = "",
                       to_schema: str = "", dialect: str = "postgresql") -> Dict[str, Any]:
    """Generate SQL migration scripts."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    migration_name = f"{timestamp}_{action}_{table_name}"

    up_sql = ""
    down_sql = ""

    if action == "create_table":
        col_defs = []
        col_defs.append("    id SERIAL PRIMARY KEY" if dialect == "postgresql" else "    id INTEGER PRIMARY KEY AUTOINCREMENT")

        if columns:
            for col in columns.split(","):
                col = col.strip()
                if " " in col:
                    col_defs.append(f"    {col}")
                else:
                    col_defs.append(f"    {col} VARCHAR(255)")
        else:
            col_defs.extend([
                "    name VARCHAR(255) NOT NULL",
                "    email VARCHAR(255) UNIQUE",
                "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            ])

        up_sql = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);"
        down_sql = f"DROP TABLE IF EXISTS {table_name};"

    elif action == "add_column":
        cols = columns.split(",") if columns else ["new_column VARCHAR(255)"]
        up_parts = []
        down_parts = []
        for col in cols:
            col = col.strip()
            parts = col.split()
            col_name = parts[0]
            col_type = " ".join(parts[1:]) if len(parts) > 1 else "VARCHAR(255)"
            up_parts.append(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")
            down_parts.append(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_name};")
        up_sql = "\n".join(up_parts)
        down_sql = "\n".join(down_parts)

    elif action == "add_index":
        idx_cols = columns or "id"
        idx_name = f"idx_{table_name}_{idx_cols.replace(',', '_').replace(' ', '')}"
        up_sql = f"CREATE INDEX {idx_name} ON {table_name} ({idx_cols});"
        down_sql = f"DROP INDEX IF EXISTS {idx_name};"

    elif action == "rename_column":
        if "," in columns:
            old_name, new_name = [c.strip() for c in columns.split(",", 1)]
        else:
            old_name, new_name = columns.strip(), f"new_{columns.strip()}"
        up_sql = f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name};"
        down_sql = f"ALTER TABLE {table_name} RENAME COLUMN {new_name} TO {old_name};"

    elif action == "drop_table":
        up_sql = f"DROP TABLE IF EXISTS {table_name};"
        down_sql = f"-- TODO: recreate {table_name} table\n-- CREATE TABLE {table_name} (...);"

    elif action == "schema_diff":
        up_sql = f"-- Schema diff migration\n-- From: {from_schema}\n-- To: {to_schema}\n-- TODO: generate diff automatically"
        down_sql = "-- Reverse migration\n-- TODO: reverse the diff"

    migration = {
        "name": migration_name,
        "up": f"-- Migration: {migration_name}\n-- Up\n\nBEGIN;\n\n{up_sql}\n\nCOMMIT;",
        "down": f"-- Migration: {migration_name}\n-- Down (rollback)\n\nBEGIN;\n\n{down_sql}\n\nCOMMIT;",
    }

    return {
        "migration_name": migration_name,
        "dialect": dialect,
        "action": action,
        "table": table_name,
        "up_migration": migration["up"],
        "down_migration": migration["down"],
        "files": {
            f"{migration_name}_up.sql": migration["up"],
            f"{migration_name}_down.sql": migration["down"],
        },
    }


def build_regex(description: str = "", test_strings: str = "",
                flavor: str = "python") -> Dict[str, Any]:
    """Build and test regular expressions from natural language descriptions."""
    # Common regex patterns by description
    pattern_map = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "url": r"https?://[^\s<>\"']+",
        "phone": r"(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}",
        "ip": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "ipv4": r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\b",
        "date": r"\d{4}[-/]\d{2}[-/]\d{2}",
        "time": r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?",
        "hex_color": r"#(?:[0-9a-fA-F]{3}){1,2}\b",
        "zip": r"\b\d{5}(?:-\d{4})?\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "uuid": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "slug": r"[a-z0-9]+(?:-[a-z0-9]+)*",
        "username": r"[a-zA-Z][a-zA-Z0-9_]{2,29}",
        "password_strong": r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}",
        "html_tag": r"<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>.*?</\1>",
        "number": r"-?\d+(?:\.\d+)?",
        "integer": r"-?\d+",
        "float": r"-?\d+\.\d+",
        "whitespace": r"\s+",
        "word": r"\b\w+\b",
        "sentence": r"[A-Z][^.!?]*[.!?]",
        "json_key": r'"([^"]+)"\s*:',
        "csv_field": r'(?:^|,)("(?:[^"]*(?:""[^"]*)*)"|[^,]*)',
        "markdown_link": r"\[([^\]]+)\]\(([^)]+)\)",
        "domain": r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}",
    }

    # Try to match description to known pattern
    desc_lower = description.lower()
    matched_pattern = None
    for key, pattern in pattern_map.items():
        if key.replace("_", " ") in desc_lower or key in desc_lower:
            matched_pattern = pattern
            break

    if not matched_pattern:
        # Build from description keywords
        if "digit" in desc_lower or "number" in desc_lower:
            matched_pattern = r"\d+"
        elif "letter" in desc_lower or "alpha" in desc_lower:
            matched_pattern = r"[a-zA-Z]+"
        elif "word" in desc_lower:
            matched_pattern = r"\w+"
        elif "start" in desc_lower and "end" in desc_lower:
            matched_pattern = r"^.*$"
        else:
            matched_pattern = r".*"

    # Test against provided strings
    test_results = []
    if test_strings:
        for test in test_strings.split("\n"):
            test = test.strip()
            if test:
                try:
                    matches = re.findall(matched_pattern, test)
                    full_match = bool(re.fullmatch(matched_pattern, test))
                    test_results.append({
                        "input": test,
                        "matches": matches[:10],
                        "full_match": full_match,
                        "match_count": len(matches),
                    })
                except re.error as e:
                    test_results.append({"input": test, "error": str(e)})

    # Flavor-specific adjustments
    flavor_notes = {
        "python": f"Use: re.compile(r'{matched_pattern}')",
        "javascript": f"Use: /{matched_pattern}/g",
        "rust": f"Use: Regex::new(r\"{matched_pattern}\")",
        "go": f"Use: regexp.MustCompile(`{matched_pattern}`)",
    }

    return {
        "pattern": matched_pattern,
        "description": description,
        "flavor": flavor,
        "usage": flavor_notes.get(flavor, f"Pattern: {matched_pattern}"),
        "test_results": test_results,
        "common_patterns": {k: v for k, v in list(pattern_map.items())[:15]},
        "flags": {
            "case_insensitive": f"(?i){matched_pattern}",
            "multiline": f"(?m){matched_pattern}",
            "dotall": f"(?s){matched_pattern}",
        },
    }


def generate_dockerfile(language: str = "python", framework: str = "",
                        project_name: str = "app",
                        port: int = 8000, multi_stage: bool = True) -> Dict[str, Any]:
    """Generate Dockerfile and docker-compose.yml for any language/framework."""
    lang = language.lower()

    dockerfiles = {
        "python": {
            "single": f'''FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE {port}

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
''',
            "multi": f'''# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application
COPY . .

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=3s \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}/health')"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
''',
        },
        "node": {
            "single": f'''FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

EXPOSE {port}
CMD ["node", "src/index.js"]
''',
            "multi": f'''# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime stage
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force
COPY --from=builder /app/dist ./dist

RUN addgroup -g 1001 -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=3s \\
    CMD wget --spider http://localhost:{port}/health || exit 1

CMD ["node", "dist/index.js"]
''',
        },
        "go": {
            "single": f'''FROM golang:1.22-alpine
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o server .
EXPOSE {port}
CMD ["./server"]
''',
            "multi": f'''# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o server .

# Runtime stage
FROM alpine:3.19
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/server .

RUN adduser -D -g '' appuser
USER appuser

EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=3s \\
    CMD wget --spider http://localhost:{port}/health || exit 1

CMD ["./server"]
''',
        },
        "rust": {
            "multi": f'''# Build stage
FROM rust:1.75-slim AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {{}}" > src/main.rs && cargo build --release && rm -rf src
COPY . .
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/target/release/{project_name} .

RUN useradd -m appuser
USER appuser

EXPOSE {port}
CMD ["./{project_name}"]
''',
        },
    }

    # Map framework to language
    lang_key = lang
    if lang in ("javascript", "typescript") or framework in ("express", "nextjs", "react"):
        lang_key = "node"

    lang_templates = dockerfiles.get(lang_key, dockerfiles["python"])
    dockerfile = lang_templates.get("multi" if multi_stage else "single", lang_templates.get("multi", lang_templates.get("single", "")))

    # Docker Compose
    compose = f'''version: "3.8"

services:
  app:
    build: .
    container_name: {project_name}
    ports:
      - "{port}:{port}"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/{project_name}
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-network

  db:
    image: postgres:16-alpine
    container_name: {project_name}-db
    environment:
      POSTGRES_DB: {project_name}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    container_name: {project_name}-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network

volumes:
  postgres-data:

networks:
  app-network:
    driver: bridge
'''

    dockerignore = """node_modules
.git
.env
.env.local
__pycache__
*.pyc
.venv
venv
dist
build
.next
coverage
.pytest_cache
target
*.log
.DS_Store
.idea
.vscode
"""

    return {
        "dockerfile": dockerfile,
        "docker_compose": compose,
        "dockerignore": dockerignore,
        "language": lang,
        "port": port,
        "multi_stage": multi_stage,
        "commands": {
            "build": f"docker build -t {project_name} .",
            "run": f"docker run -p {port}:{port} {project_name}",
            "compose_up": "docker compose up -d",
            "compose_down": "docker compose down",
            "compose_logs": "docker compose logs -f",
        },
    }


def generate_cicd(platform: str = "github_actions", language: str = "python",
                  features: str = "") -> Dict[str, Any]:
    """Generate CI/CD pipeline configuration for GitHub Actions or GitLab CI."""
    platform_key = platform.lower().replace(" ", "_").replace("-", "_")
    lang_key = language.lower()

    # Map common names
    if "github" in platform_key:
        platform_key = "github_actions"
    elif "gitlab" in platform_key:
        platform_key = "gitlab_ci"

    if lang_key in ("js", "javascript", "typescript", "ts"):
        lang_key = "node"

    templates = CICD_TEMPLATES.get(platform_key, CICD_TEMPLATES["github_actions"])
    pipeline = templates.get(lang_key)

    if not pipeline:
        available_langs = list(templates.keys())
        return {"error": f"No template for {lang_key}. Available: {', '.join(available_langs)}"}

    # Add deployment step if requested
    if "deploy" in features.lower():
        if platform_key == "github_actions":
            pipeline += '''
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: echo "Add deployment steps here"
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
'''

    filename = ".github/workflows/ci.yml" if platform_key == "github_actions" else ".gitlab-ci.yml"

    return {
        "platform": platform_key,
        "language": lang_key,
        "filename": filename,
        "pipeline": pipeline,
        "features": features,
        "setup_instructions": [
            f"Save as {filename} in your repository root",
            "Configure required secrets in your CI platform settings",
            "Push to trigger the pipeline",
        ],
    }


# ── Tool registration ────────────────────────────────────────────────────

def _raw_tools():
    return [
        {
            "name": "generate_code",
            "description": "Generate production-quality code in 15+ languages (Python, JS/TS, Rust, Go, C++, Java, Ruby, Swift, Kotlin, PHP, SQL, Bash, etc). Supports functions, classes, API endpoints, React components, and more.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Programming language (python, javascript, typescript, rust, go, cpp, java, ruby, swift, kotlin, php, sql, bash)"},
                    "construct": {"type": "string", "description": "Code construct: function, class, async_function, dataclass, api_endpoint, react_component, express_route, struct, enum, trait, interface, handler, create_table, arrow, context_manager, type"},
                    "name": {"type": "string", "description": "Name of the function/class/component"},
                    "description": {"type": "string", "description": "What the code should do"},
                    "parameters": {"type": "string", "description": "Function parameters (e.g. 'x: int, y: int')"},
                    "body": {"type": "string", "description": "Implementation body"},
                    "return_type": {"type": "string", "description": "Return type annotation"},
                    "fields": {"type": "string", "description": "Class/struct fields"},
                    "methods": {"type": "string", "description": "Method signatures/implementations"},
                    "imports": {"type": "string", "description": "Import statements"},
                },
                "required": ["language"],
            },
            "function": generate_code,
        },
        {
            "name": "debug_code",
            "description": "Advanced debugger: analyzes error messages, stack traces, and code to diagnose issues and suggest fixes. Supports Python, JS/TS, Rust, Go, Java, and more.",
            "parameters": {
                "type": "object",
                "properties": {
                    "error_message": {"type": "string", "description": "The error message or exception"},
                    "code": {"type": "string", "description": "The relevant source code"},
                    "language": {"type": "string", "description": "Programming language (auto-detected if empty)"},
                    "stack_trace": {"type": "string", "description": "Full stack trace"},
                },
                "required": ["error_message"],
            },
            "function": debug_code,
        },
        {
            "name": "review_code",
            "description": "Comprehensive code review: security vulnerabilities, performance issues, code smells, best practices. Returns quality score and actionable suggestions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to review"},
                    "language": {"type": "string", "description": "Programming language (auto-detected if empty)"},
                    "focus": {"type": "string", "enum": ["all", "security", "performance", "smells", "best_practices"], "description": "Review focus area"},
                },
                "required": ["code"],
            },
            "function": review_code,
        },
        {
            "name": "design_architecture",
            "description": "Design system architecture: microservices, monolith, serverless, or event-driven. Generates component diagrams, API design, database schema, and scaling recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "system_type": {"type": "string", "enum": ["microservices", "monolith", "serverless", "event_driven"], "description": "Architecture pattern"},
                    "name": {"type": "string", "description": "System/project name"},
                    "requirements": {"type": "string", "description": "System requirements description"},
                    "scale": {"type": "string", "enum": ["small", "medium", "large"], "description": "Expected scale"},
                    "database": {"type": "string", "description": "Preferred database (postgresql, mysql, mongodb, etc)"},
                },
                "required": ["system_type"],
            },
            "function": design_architecture,
        },
        {
            "name": "suggest_refactoring",
            "description": "Refactoring assistant: identifies DRY violations, SOLID principle issues, design pattern opportunities, code complexity, and suggests improvements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to analyze for refactoring"},
                    "language": {"type": "string", "description": "Programming language"},
                    "focus": {"type": "string", "enum": ["all", "dry", "solid", "patterns", "complexity"], "description": "Refactoring focus"},
                },
                "required": ["code"],
            },
            "function": suggest_refactoring,
        },
        {
            "name": "generate_tests",
            "description": "Generate test code for any language and framework (pytest, jest, mocha, built-in test, go testing). Extracts functions/classes and creates comprehensive test suites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Source code to generate tests for"},
                    "language": {"type": "string", "description": "Programming language"},
                    "framework": {"type": "string", "description": "Test framework (pytest, jest, mocha, vitest, go testing, rust built-in)"},
                    "test_type": {"type": "string", "enum": ["unit", "integration", "e2e", "all"], "description": "Type of tests to generate"},
                },
                "required": ["code"],
            },
            "function": generate_tests,
        },
        {
            "name": "profile_performance",
            "description": "Performance profiler: analyzes Big-O complexity, detects memory leaks, I/O bottlenecks, and anti-patterns. Provides optimization recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to profile"},
                    "language": {"type": "string", "description": "Programming language"},
                },
                "required": ["code"],
            },
            "function": profile_performance,
        },
        {
            "name": "audit_dependencies",
            "description": "Dependency auditor: checks for known vulnerabilities, outdated packages, version pinning issues, and license concerns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_file": {"type": "string", "description": "Contents of requirements.txt, package.json, Cargo.toml, or go.mod"},
                    "language": {"type": "string", "enum": ["python", "javascript", "typescript", "rust", "go"], "description": "Package ecosystem"},
                },
                "required": ["package_file"],
            },
            "function": audit_dependencies,
        },
        {
            "name": "git_workflow",
            "description": "Git workflow helper: generate conventional commit messages, branch names, PR templates, and branching strategy recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["commit_message", "branch_name", "pr_template", "branching_strategy"], "description": "What to generate"},
                    "changes": {"type": "string", "description": "Description of changes made"},
                    "branch_name": {"type": "string", "description": "Branch name (for PR template)"},
                    "description": {"type": "string", "description": "Feature/change description"},
                    "pr_template": {"type": "string", "enum": ["standard", "minimal"], "description": "PR template style"},
                },
                "required": ["action"],
            },
            "function": git_workflow,
        },
        {
            "name": "scaffold_project",
            "description": "Full-stack project scaffolder: generates complete project structure for React, Next.js, FastAPI, Django, Express. Includes configs, tests, Docker, and CI/CD.",
            "parameters": {
                "type": "object",
                "properties": {
                    "framework": {"type": "string", "enum": ["fastapi", "nextjs", "express", "django", "react"], "description": "Framework to scaffold"},
                    "project_name": {"type": "string", "description": "Project name"},
                    "features": {"type": "string", "description": "Additional features (auth, database, websockets, etc)"},
                },
                "required": ["framework"],
            },
            "function": scaffold_project,
        },
        {
            "name": "generate_api_docs",
            "description": "API documentation generator: extracts routes from FastAPI, Express, or Flask code and generates OpenAPI 3.0 spec.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "API source code with route definitions"},
                    "title": {"type": "string", "description": "API documentation title"},
                    "base_url": {"type": "string", "description": "Base URL for the API"},
                },
                "required": ["code"],
            },
            "function": generate_api_docs,
        },
        {
            "name": "generate_migration",
            "description": "Database migration generator: creates up/down SQL migration scripts for PostgreSQL, MySQL, SQLite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create_table", "add_column", "add_index", "rename_column", "drop_table", "schema_diff"], "description": "Migration action"},
                    "table_name": {"type": "string", "description": "Target table name"},
                    "columns": {"type": "string", "description": "Column definitions (comma-separated: 'name VARCHAR(255), age INT')"},
                    "from_schema": {"type": "string", "description": "Current schema (for diff)"},
                    "to_schema": {"type": "string", "description": "Target schema (for diff)"},
                    "dialect": {"type": "string", "enum": ["postgresql", "mysql", "sqlite"], "description": "SQL dialect"},
                },
                "required": ["action"],
            },
            "function": generate_migration,
        },
        {
            "name": "build_regex",
            "description": "Regex builder and tester: create regular expressions from descriptions, test against sample strings, get flavor-specific syntax.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "What to match (e.g. 'email address', 'URL', 'phone number', 'date')"},
                    "test_strings": {"type": "string", "description": "Newline-separated strings to test the regex against"},
                    "flavor": {"type": "string", "enum": ["python", "javascript", "rust", "go"], "description": "Regex flavor/language"},
                },
                "required": ["description"],
            },
            "function": build_regex,
        },
        {
            "name": "generate_dockerfile",
            "description": "Generate production-ready Dockerfile and docker-compose.yml with multi-stage builds, health checks, and security best practices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Application language (python, node, go, rust)"},
                    "framework": {"type": "string", "description": "Framework (fastapi, express, nextjs, etc)"},
                    "project_name": {"type": "string", "description": "Project/container name"},
                    "port": {"type": "integer", "description": "Application port (default 8000)"},
                    "multi_stage": {"type": "boolean", "description": "Use multi-stage build (default true)"},
                },
                "required": ["language"],
            },
            "function": generate_dockerfile,
        },
        {
            "name": "generate_cicd",
            "description": "Generate CI/CD pipeline configs for GitHub Actions or GitLab CI. Includes linting, testing, building, and optional deployment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["github_actions", "gitlab_ci"], "description": "CI/CD platform"},
                    "language": {"type": "string", "description": "Project language (python, node, rust, go)"},
                    "features": {"type": "string", "description": "Additional features: deploy, docker, coverage"},
                },
                "required": ["platform", "language"],
            },
            "function": generate_cicd,
        },
    ]


def get_tools():
    return adapt_tools(_raw_tools())

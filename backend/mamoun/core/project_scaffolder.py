"""
BABSHARQII v50.0 — Project Scaffolder
منشئ المشاريع — يحول وصف لغوي إلى مشروع كامل قابل للتنفيذ

One of the biggest gaps identified in the audit: Mamoun could not build
complete projects from scratch. This module closes that gap.

The ProjectScaffolder:
  1. Takes a natural language description + project type
  2. Uses LLM to design the directory structure and file list
  3. Generates each file via LLM (real, functional code)
  4. Validates each file before writing (syntax, safety, completeness)
  5. Writes files incrementally: generate → validate → write → test → next
  6. Tracks project state in the unified database
  7. Produces Docker configs, README, and entry points automatically

Supported Project Types:
  - python_fastapi   : FastAPI REST API with uvicorn, pydantic, Docker
  - python_cli       : CLI tool with argparse/click, setup.py, Docker
  - python_data      : Data processing pipeline with pandas, Docker
  - nextjs_react     : Next.js 14+ App Router with TypeScript, Tailwind
  - nodejs_api       : Express/Fastify API with TypeScript, Docker
  - fullstack        : Next.js frontend + FastAPI backend, docker-compose

Design Principles:
  - Follows singleton pattern like other Mamoun modules
  - Uses mamoun.core.llm_client for ALL LLM calls
  - Uses mamoun.core.unified_db for ALL persistence
  - Leverages CodeGenerationEngine for individual file generation + review
  - Proper error handling and logging throughout
  - Async-compatible (all heavy work is async)

Based on:
  - CodeGenerationEngine: dual-model writer+reviewer pattern
  - ProjectOrchestrator: project lifecycle management
  - LiveSelfModifier: safety-first code generation
"""

import asyncio
import ast
import json
import time
import logging
import os
import hashlib
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH
from mamoun.core.llm_client import get_llm_client, LLMMessage

logger = logging.getLogger("mamoun.core.project_scaffolder")


# ═══════════════════════════════════════════════════════════════════════════════
#  Enums & Data Classes
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectType(str, Enum):
    """أنواع المشاريع المدعومة — Supported project types"""
    PYTHON_FASTAPI = "python_fastapi"
    PYTHON_CLI = "python_cli"
    PYTHON_DATA = "python_data"
    NEXTJS_REACT = "nextjs_react"
    NODEJS_API = "nodejs_api"
    FULLSTACK = "fullstack"


class ScaffolderPhase(str, Enum):
    """مراحل البناء — Scaffolding phases"""
    PLANNING = "planning"           # LLM designs the structure
    GENERATING = "generating"       # Generating each file
    VALIDATING = "validating"       # Validating generated files
    WRITING = "writing"             # Writing files to disk
    COMPLETED = "completed"         # All done
    FAILED = "failed"               # Something went wrong


@dataclass
class ScaffolderFile:
    """ملف ضمن المشروع — A file within the scaffolded project"""
    path: str = ""                  # Relative path within project (e.g. "src/app/main.tsx")
    description: str = ""           # Natural language description of what the file should contain
    language: str = "python"        # Programming language for LLM prompt
    content: str = ""               # Generated content (populated after LLM generation)
    confidence: float = 0.0         # Review confidence score
    validated: bool = False         # Whether the file passed validation
    written: bool = False           # Whether the file was written to disk
    error: str = ""                 # Error message if generation/validation/writing failed
    generation_time_ms: float = 0.0 # How long LLM took to generate this file

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScaffoldedProject:
    """مشروع منشأ — A scaffolded project"""
    id: str = ""
    name: str = ""
    description: str = ""
    project_type: str = ProjectType.PYTHON_FASTAPI.value
    phase: str = ScaffolderPhase.PLANNING.value
    project_dir: str = ""
    files: List[ScaffolderFile] = field(default_factory=list)
    total_files: int = 0
    files_generated: int = 0
    files_written: int = 0
    total_lines: int = 0
    errors: List[str] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    completed_at: float = 0.0
    llm_tokens_used: int = 0
    llm_calls: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = f"scaffold_{hashlib.md5(f'{self.name}{time.time()}'.encode()).hexdigest()[:12]}"
        if not self.created_at:
            self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "phase": self.phase,
            "project_dir": self.project_dir,
            "total_files": self.total_files,
            "files_generated": self.files_generated,
            "files_written": self.files_written,
            "total_lines": self.total_lines,
            "errors": self.errors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "llm_tokens_used": self.llm_tokens_used,
            "llm_calls": self.llm_calls,
            "files": [f.to_dict() for f in self.files],
        }
        return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Project Type Templates — baseline structures for each project type
# ═══════════════════════════════════════════════════════════════════════════════

PROJECT_TYPE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    ProjectType.PYTHON_FASTAPI.value: {
        "display_name": "Python FastAPI Project",
        "display_name_ar": "مشروع بايثون FastAPI",
        "default_files": {
            "app/__init__.py": "Empty init file for the app package",
            "app/main.py": "FastAPI application entry point with CORS, routers, health check, and startup/shutdown lifecycle",
            "app/routers/__init__.py": "Empty init file for routers package",
            "app/routers/api.py": "Primary API router with CRUD endpoints and request/response models",
            "app/models.py": "Pydantic models for request/response schemas with validation",
            "app/database.py": "Database connection setup with SQLAlchemy async engine and session management",
            "app/config.py": "Configuration module using pydantic-settings with environment variable support",
            "app/services/__init__.py": "Empty init file for services package",
            "app/services/service.py": "Business logic service layer with dependency injection",
            "tests/__init__.py": "Empty init file for tests package",
            "tests/test_api.py": "API endpoint tests using pytest and httpx async client",
            "requirements.txt": "Python dependencies: fastapi, uvicorn, pydantic, sqlalchemy, etc.",
            "Dockerfile": "Multi-stage Docker build for production FastAPI deployment",
            "docker-compose.yml": "Docker Compose with app service, PostgreSQL database, and Redis cache",
            ".env.example": "Example environment variables file",
            ".gitignore": "Python gitignore patterns",
            "README.md": "Project README with setup instructions, API docs link, and Docker usage",
        },
        "language": "python",
    },

    ProjectType.PYTHON_CLI.value: {
        "display_name": "Python CLI Tool",
        "display_name_ar": "أداة سطر أوامر بايثون",
        "default_files": {
            "src/__init__.py": "Empty init file for the src package",
            "src/cli.py": "CLI entry point using Click or argparse with subcommands and help text",
            "src/commands/__init__.py": "Empty init file for commands package",
            "src/commands/main.py": "Main command implementations with argument parsing and validation",
            "src/config.py": "Configuration management with YAML/TOML file support and defaults",
            "src/utils.py": "Utility functions: logging setup, file I/O, formatting helpers",
            "tests/__init__.py": "Empty init file for tests package",
            "tests/test_cli.py": "CLI tests using pytest and Click testing utilities",
            "setup.py": "Package setup with entry_points for console_scripts installation",
            "pyproject.toml": "PEP 621 project metadata and build system configuration",
            "requirements.txt": "Python dependencies: click, rich, pyyaml, etc.",
            "Dockerfile": "Docker build for CLI tool with minimal base image",
            ".gitignore": "Python gitignore patterns",
            "README.md": "README with installation, usage examples, and command reference",
        },
        "language": "python",
    },

    ProjectType.PYTHON_DATA.value: {
        "display_name": "Python Data Processing",
        "display_name_ar": "معالجة بيانات بايثون",
        "default_files": {
            "src/__init__.py": "Empty init file for the src package",
            "src/pipeline.py": "Data pipeline orchestrator with ETL stages and error recovery",
            "src/extract.py": "Data extraction module: API clients, file readers, database connectors",
            "src/transform.py": "Data transformation: cleaning, normalization, feature engineering",
            "src/load.py": "Data loading: database writers, file exporters, API pushers",
            "src/models.py": "Data models using Pydantic or dataclasses for type-safe processing",
            "src/config.py": "Pipeline configuration with environment variables and YAML support",
            "notebooks/exploration.ipynb": "Jupyter notebook placeholder for data exploration",
            "tests/__init__.py": "Empty init file for tests package",
            "tests/test_pipeline.py": "Pipeline tests with sample data fixtures",
            "requirements.txt": "Python dependencies: pandas, numpy, pydantic, sqlalchemy, etc.",
            "Dockerfile": "Docker build for data pipeline with cron scheduling support",
            "docker-compose.yml": "Docker Compose with pipeline service and PostgreSQL database",
            ".env.example": "Example environment variables for data sources and destinations",
            ".gitignore": "Python + data gitignore patterns (csv, parquet, etc.)",
            "README.md": "README with pipeline architecture, data flow diagram, and configuration guide",
        },
        "language": "python",
    },

    ProjectType.NEXTJS_REACT.value: {
        "display_name": "Next.js React Application",
        "display_name_ar": "تطبيق Next.js React",
        "default_files": {
            "src/app/layout.tsx": "Root layout with HTML structure, fonts, global providers, and metadata",
            "src/app/page.tsx": "Home page with hero section, features, and call-to-action",
            "src/app/globals.css": "Global CSS with Tailwind directives and custom CSS variables",
            "src/app/api/health/route.ts": "Health check API route handler",
            "src/components/ui/Button.tsx": "Reusable Button component with variants, sizes, and accessibility",
            "src/components/ui/Card.tsx": "Reusable Card component with header, content, and footer slots",
            "src/components/ui/Input.tsx": "Reusable Input component with validation and error states",
            "src/lib/api.ts": "API client utility with fetch wrapper, error handling, and type safety",
            "src/lib/config.ts": "Frontend configuration: API URL, feature flags, environment settings",
            "src/types/index.ts": "TypeScript type definitions and interfaces for the application",
            "package.json": "NPM package with Next.js, React, TypeScript, Tailwind dependencies",
            "tsconfig.json": "TypeScript configuration with path aliases and strict mode",
            "tailwind.config.ts": "Tailwind CSS configuration with custom theme and plugins",
            "next.config.js": "Next.js configuration with rewrites, redirects, and image optimization",
            "Dockerfile": "Multi-stage Docker build for Next.js production deployment",
            "docker-compose.yml": "Docker Compose with Next.js app service",
            ".env.local.example": "Example environment variables for Next.js",
            ".gitignore": "Next.js gitignore patterns",
            "README.md": "README with setup, development, deployment, and environment instructions",
        },
        "language": "typescript",
    },

    ProjectType.NODEJS_API.value: {
        "display_name": "Node.js API Server",
        "display_name_ar": "خادم API Node.js",
        "default_files": {
            "src/index.ts": "API server entry point with Express/Fastify setup and graceful shutdown",
            "src/routes/index.ts": "Route definitions and registration with middleware",
            "src/routes/api.ts": "API route handlers with request validation and response formatting",
            "src/middleware/auth.ts": "Authentication middleware: JWT verification and role checking",
            "src/middleware/errorHandler.ts": "Global error handler middleware with logging and safe responses",
            "src/models/index.ts": "Data models and interfaces for the API",
            "src/services/service.ts": "Business logic service layer with dependency injection",
            "src/config/index.ts": "Configuration module with environment variable validation using zod",
            "src/database/connection.ts": "Database connection setup with Prisma or Knex",
            "src/types/index.ts": "TypeScript type definitions for request/response interfaces",
            "package.json": "NPM package with Express, TypeScript, and dev dependencies",
            "tsconfig.json": "TypeScript configuration for Node.js API server",
            "Dockerfile": "Multi-stage Docker build for Node.js API production deployment",
            "docker-compose.yml": "Docker Compose with API service and PostgreSQL database",
            ".env.example": "Example environment variables for API configuration",
            ".gitignore": "Node.js gitignore patterns",
            "README.md": "README with API documentation, setup, and deployment guide",
        },
        "language": "typescript",
    },

    ProjectType.FULLSTACK.value: {
        "display_name": "Full-Stack (Next.js + FastAPI)",
        "display_name_ar": "مكدس كامل (Next.js + FastAPI)",
        "default_files": {
            # Frontend — Next.js
            "frontend/src/app/layout.tsx": "Root layout with HTML structure, fonts, global providers",
            "frontend/src/app/page.tsx": "Home page with data fetching from backend API",
            "frontend/src/app/globals.css": "Global CSS with Tailwind directives",
            "frontend/src/app/api/health/route.ts": "Frontend health check API route",
            "frontend/src/components/ui/Button.tsx": "Reusable Button component with variants",
            "frontend/src/components/ui/Card.tsx": "Reusable Card component",
            "frontend/src/lib/api.ts": "API client utility pointing to FastAPI backend",
            "frontend/src/types/index.ts": "TypeScript type definitions",
            "frontend/package.json": "Frontend NPM package with Next.js, React, TypeScript",
            "frontend/tsconfig.json": "Frontend TypeScript configuration",
            "frontend/tailwind.config.ts": "Tailwind CSS configuration",
            "frontend/Dockerfile": "Frontend Docker build",
            # Backend — FastAPI
            "backend/app/__init__.py": "Empty init file for backend app package",
            "backend/app/main.py": "FastAPI application with CORS for frontend, routers, health check",
            "backend/app/routers/__init__.py": "Empty init file for routers package",
            "backend/app/routers/api.py": "API router with CRUD endpoints",
            "backend/app/models.py": "Pydantic models for request/response schemas",
            "backend/app/database.py": "Database connection with SQLAlchemy async",
            "backend/app/config.py": "Backend configuration with pydantic-settings",
            "backend/app/services/__init__.py": "Empty init file for services package",
            "backend/app/services/service.py": "Business logic service layer",
            "backend/requirements.txt": "Backend Python dependencies",
            "backend/Dockerfile": "Backend Docker build",
            # Root — Docker Compose + docs
            "docker-compose.yml": "Root Docker Compose orchestrating frontend, backend, database, and Redis",
            ".env.example": "Example environment variables for full-stack setup",
            ".gitignore": "Full-stack gitignore patterns",
            "README.md": "Full-stack README with architecture diagram and setup instructions",
        },
        "language": "python",  # Mixed — will use per-file language detection
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
#  File Validation Helpers
# ═══════════════════════════════════════════════════════════════════════════════

# Dangerous patterns that should NEVER appear in generated code
FORBIDDEN_PATTERNS = [
    "rm -rf",
    "del /f",
    "format c:",
    "DROP TABLE",
    "GRANT ALL",
    "chmod 777",
    "os.system(",
    "subprocess.call(",
    "subprocess.Popen(",
    "exec(",
    "eval(",
    "__import__(",
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
]

# File extensions mapped to their language for syntax validation
EXT_LANGUAGE_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".css": "css",
    ".dockerfile": "dockerfile",
    ".txt": "text",
    ".env": "env",
    ".gitignore": "gitignore",
}


def _detect_language_from_path(file_path: str) -> str:
    """Detect the programming language from a file path's extension."""
    # Special filename cases
    basename = Path(file_path).name.lower()
    if basename == "dockerfile":
        return "dockerfile"
    if basename == "docker-compose.yml" or basename == "docker-compose.yaml":
        return "yaml"
    if basename.startswith(".env"):
        return "env"
    if basename == ".gitignore":
        return "gitignore"

    ext = Path(file_path).suffix.lower()
    return EXT_LANGUAGE_MAP.get(ext, "text")


def _validate_file_content(content: str, language: str) -> Tuple[float, str]:
    """
    Validate generated file content — returns (confidence, feedback).

    Checks:
      1. Not empty / too short
      2. No forbidden dangerous patterns
      3. Language-specific syntax validation (Python: ast.parse, JSON: json.loads, etc.)
      4. Structural completeness checks
    """
    confidence = 1.0
    feedback_parts: List[str] = []

    # ── 1. Non-empty check ─────────────────────────────────────────────────
    stripped = content.strip()
    if not stripped:
        return 0.0, "File content is empty"
    if len(stripped) < 10:
        return 0.1, "File content is suspiciously short (< 10 chars)"

    lines = stripped.split("\n")
    if len(lines) < 2:
        confidence *= 0.6
        feedback_parts.append("File is very short (1 line)")

    # ── 2. Forbidden patterns check ────────────────────────────────────────
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in content.lower():
            confidence = 0.1
            feedback_parts.append(f"DANGEROUS pattern detected: {pattern}")
            # Don't break — report ALL dangerous patterns found

    # ── 3. Language-specific validation ────────────────────────────────────
    if language == "python":
        try:
            tree = ast.parse(content)
            funcs = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            if funcs == 0 and classes == 0 and len(lines) > 5:
                confidence *= 0.8
                feedback_parts.append("No functions or classes defined in non-trivial Python file")
        except SyntaxError as e:
            confidence *= 0.5
            feedback_parts.append(f"Python syntax error: {str(e)[:100]}")
        except Exception as e:
            confidence *= 0.85
            feedback_parts.append(f"Python parse warning: {str(e)[:80]}")

    elif language == "json":
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            confidence *= 0.3
            feedback_parts.append(f"Invalid JSON: {str(e)[:100]}")

    elif language in ("yaml", "toml"):
        # Basic YAML/TOML validation — check for common issues
        if "\t" in content and language == "yaml":
            confidence *= 0.7
            feedback_parts.append("YAML file contains tabs (should use spaces)")

    elif language in ("typescript", "javascript"):
        # Basic TS/JS structural checks
        has_exports = "export " in content
        has_imports = "import " in content or "require(" in content
        has_functions = "function " in content or "const " in content or "=>" in content
        if not has_exports and not has_functions and len(lines) > 5:
            confidence *= 0.75
            feedback_parts.append("No exports or function definitions found")

    elif language == "dockerfile":
        if "FROM" not in content.upper():
            confidence *= 0.5
            feedback_parts.append("Dockerfile missing FROM instruction")

    elif language == "markdown":
        # Minimal markdown validation
        if not any(line.startswith("#") for line in lines):
            confidence *= 0.8
            feedback_parts.append("Markdown file has no headings")

    # ── 4. Overall quality check ───────────────────────────────────────────
    # Check for common placeholder patterns that indicate incomplete generation
    placeholder_patterns = ["TODO:", "FIXME:", "PLACEHOLDER", "___", "...", "your_code_here"]
    placeholder_count = sum(1 for p in placeholder_patterns if p.lower() in content.lower())
    if placeholder_count > 3:
        confidence *= 0.7
        feedback_parts.append(f"Found {placeholder_count} placeholder patterns — generation may be incomplete")

    confidence = max(0.0, min(1.0, confidence))

    if not feedback_parts:
        feedback_parts.append("Validation passed")

    return round(confidence, 3), " | ".join(feedback_parts)


def _clean_llm_output(text: str) -> str:
    """Clean LLM output — remove markdown code blocks and leading/trailing whitespace."""
    code = text.strip()
    # Remove markdown code blocks
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first line (```python, ```typescript, etc.)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    return code.strip()


# ═══════════════════════════════════════════════════════════════════════════════
#  The ProjectScaffolder
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectScaffolder:
    """
    منشئ المشاريع — Project Scaffolder

    Builds complete, runnable projects from natural language descriptions.
    One of the biggest gaps identified in the audit — Mamoun could NOT build
    projects from scratch. This module closes that gap.

    Pipeline:
      1. User provides: description (natural language) + project_type
      2. _generate_structure() → LLM designs directory structure
      3. For each file:
         a. _generate_file() → LLM generates real, functional code
         b. _validate_file() → syntax + safety + completeness validation
         c. Write to disk if validation passes
      4. _validate_project() → overall project validation
      5. Track state in unified DB

    Usage:
        scaffolder = ProjectScaffolder()
        result = await scaffolder.scaffold_project({
            "name": "my_api",
            "description": "A REST API for managing tasks",
            "project_type": "python_fastapi",
        })
    """

    CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence to auto-write a file

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or UNIFIED_DB_PATH
        self._llm_client = None
        self._code_gen_engine = None
        self._initialized = False
        self._projects: Dict[str, ScaffoldedProject] = {}
        self._total_projects_scaffolded: int = 0
        self._total_files_generated: int = 0
        self._total_lines_generated: int = 0

    def initialize(self) -> bool:
        """
        تهيئة منشئ المشاريع — Initialize the scaffolder.

        Connects to LLM client and CodeGenerationEngine.
        Creates database schema if needed.
        """
        try:
            self._ensure_schema()

            # Connect LLM client
            try:
                self._llm_client = get_llm_client()
                logger.info("ProjectScaffolder: Connected to LLM client ✓")
            except Exception as e:
                logger.warning("ProjectScaffolder: Could not connect LLM client: %s", e)

            # Connect CodeGenerationEngine for per-file generation
            try:
                from mamoun.core.code_generation_engine import CodeGenerationEngine
                self._code_gen_engine = CodeGenerationEngine()
                self._code_gen_engine.set_llm_client(self._llm_client)
                self._code_gen_engine.initialize()
                logger.info("ProjectScaffolder: Connected to CodeGenerationEngine ✓")
            except Exception as e:
                logger.warning("ProjectScaffolder: Could not connect CodeGenerationEngine: %s", e)

            self._initialized = True
            logger.info("ProjectScaffolder initialized — llm=%s, codegen=%s",
                        self._llm_client is not None,
                        self._code_gen_engine is not None)
            return True

        except Exception as e:
            logger.error("ProjectScaffolder initialization failed: %s", e)
            return False

    def _ensure_schema(self):
        """Ensure the database schema for project scaffolding exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS ps_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                project_type TEXT DEFAULT 'python_fastapi',
                phase TEXT DEFAULT 'planning',
                project_dir TEXT DEFAULT '',
                total_files INTEGER DEFAULT 0,
                files_generated INTEGER DEFAULT 0,
                files_written INTEGER DEFAULT 0,
                total_lines INTEGER DEFAULT 0,
                errors TEXT DEFAULT '[]',
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0,
                completed_at REAL DEFAULT 0,
                llm_tokens_used INTEGER DEFAULT 0,
                llm_calls INTEGER DEFAULT 0,
                files_json TEXT DEFAULT '[]'
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ps_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                path TEXT NOT NULL,
                description TEXT DEFAULT '',
                language TEXT DEFAULT 'python',
                confidence REAL DEFAULT 0,
                validated INTEGER DEFAULT 0,
                written INTEGER DEFAULT 0,
                error TEXT DEFAULT '',
                generation_time_ms REAL DEFAULT 0,
                created_at REAL DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES ps_projects(id)
            )""")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ps_projects_type ON ps_projects(project_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ps_projects_phase ON ps_projects(phase)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ps_files_project ON ps_files(project_id)"
            )
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════════════
    #  Main Entry Point
    # ═══════════════════════════════════════════════════════════════════════

    async def scaffold_project(self, spec: dict) -> dict:
        """
        نقطة الدخول الرئيسية — Main entry point for project scaffolding.

        Takes a specification dict and builds a complete project from scratch.

        Args:
            spec: {
                "name": "my_project",             # Required: project name (filesystem-safe)
                "description": "A REST API...",    # Required: natural language description
                "project_type": "python_fastapi",  # Optional: defaults to python_fastapi
                "project_dir": "/path/to/dir",     # Optional: defaults to /download/projects/{name}
                "extra_files": {                   # Optional: additional files beyond template
                    "app/utils.py": "Utility functions"
                }
            }

        Returns:
            Dict with project info, files created, and status.
        """
        # ── Validate input ──────────────────────────────────────────────────
        name = spec.get("name", "").strip()
        description = spec.get("description", "").strip()
        project_type = spec.get("project_type", ProjectType.PYTHON_FASTAPI.value)
        project_dir = spec.get("project_dir", "")
        extra_files = spec.get("extra_files", {})

        if not name:
            return {"success": False, "error": "Project name is required"}
        if not description:
            return {"success": False, "error": "Project description is required"}

        # Sanitize project name for filesystem safety
        name = re.sub(r'[^\w\-]', '_', name).strip('_')
        if not name:
            return {"success": False, "error": "Project name is invalid after sanitization"}

        # Validate project type
        valid_types = [pt.value for pt in ProjectType]
        if project_type not in valid_types:
            return {"success": False, "error": f"Invalid project_type '{project_type}'. Must be one of: {valid_types}"}

        # Auto-initialize if needed
        if not self._initialized:
            self.initialize()

        # Default project directory
        if not project_dir:
            project_dir = str(Path(os.getcwd()) / "download" / "projects" / name)

        # ── Create project object ───────────────────────────────────────────
        project = ScaffoldedProject(
            name=name,
            description=description,
            project_type=project_type,
            project_dir=project_dir,
            phase=ScaffolderPhase.PLANNING.value,
        )

        self._projects[project.id] = project
        self._persist_project(project)

        logger.info("ProjectScaffolder: Starting project '%s' (type=%s, dir=%s)",
                     name, project_type, project_dir)

        try:
            # ── Phase 1: Generate directory structure via LLM ───────────────
            project.phase = ScaffolderPhase.PLANNING.value
            self._persist_project(project)

            structure = await self._generate_structure(description, project_type, extra_files)

            if not structure or not structure.get("files"):
                project.phase = ScaffolderPhase.FAILED.value
                project.errors.append("Failed to generate project structure — LLM returned empty")
                self._persist_project(project)
                return {
                    "success": False,
                    "project_id": project.id,
                    "error": "Failed to generate project structure",
                }

            # Build file list from structure
            files_dict = structure.get("files", {})
            project.files = []
            for file_path, file_desc in files_dict.items():
                lang = _detect_language_from_path(file_path)
                project.files.append(ScaffolderFile(
                    path=file_path,
                    description=file_desc,
                    language=lang,
                ))
            project.total_files = len(project.files)

            logger.info("ProjectScaffolder: Structure planned — %d files to generate", project.total_files)

            # ── Phase 2 & 3: Generate + Validate + Write each file ──────────
            project.phase = ScaffolderPhase.GENERATING.value
            self._persist_project(project)

            # Create the project directory
            Path(project_dir).mkdir(parents=True, exist_ok=True)

            for i, sfile in enumerate(project.files):
                try:
                    # ── Generate file content via LLM ───────────────────────
                    gen_start = time.time()
                    project.phase = ScaffolderPhase.GENERATING.value

                    content = await self._generate_file(
                        file_path=sfile.path,
                        description=sfile.description,
                        language=sfile.language,
                        project_name=name,
                        project_description=description,
                        project_type=project_type,
                        all_files=files_dict,
                    )

                    gen_time = (time.time() - gen_start) * 1000
                    sfile.content = content
                    sfile.generation_time_ms = gen_time
                    project.llm_calls += 1

                    if not content or len(content.strip()) < 5:
                        sfile.error = "LLM returned empty or too-short content"
                        project.errors.append(f"{sfile.path}: {sfile.error}")
                        logger.warning("ProjectScaffolder: Empty content for %s", sfile.path)
                        continue

                    # ── Validate generated content ───────────────────────────
                    project.phase = ScaffolderPhase.VALIDATING.value

                    confidence, feedback = _validate_file_content(content, sfile.language)
                    sfile.confidence = confidence

                    if confidence >= self.CONFIDENCE_THRESHOLD:
                        sfile.validated = True
                    else:
                        sfile.error = f"Validation failed (confidence={confidence:.2f}): {feedback}"
                        project.errors.append(f"{sfile.path}: {sfile.error}")
                        logger.warning("ProjectScaffolder: Validation failed for %s — %s",
                                       sfile.path, feedback)

                        # Try one regeneration for low-confidence files
                        if confidence > 0.2:
                            logger.info("ProjectScaffolder: Retrying generation for %s", sfile.path)
                            retry_content = await self._generate_file(
                                file_path=sfile.path,
                                description=f"{sfile.description}\n\nIMPORTANT: Previous attempt had issues: {feedback}. Please generate a more complete and correct version.",
                                language=sfile.language,
                                project_name=name,
                                project_description=description,
                                project_type=project_type,
                                all_files=files_dict,
                            )
                            if retry_content and len(retry_content.strip()) > len(content.strip()):
                                retry_conf, retry_fb = _validate_file_content(retry_content, sfile.language)
                                if retry_conf > confidence:
                                    sfile.content = retry_content
                                    sfile.confidence = retry_conf
                                    if retry_conf >= self.CONFIDENCE_THRESHOLD:
                                        sfile.validated = True
                                        sfile.error = ""
                                        project.llm_calls += 1

                    # ── Write file to disk ────────────────────────────────────
                    if sfile.validated:
                        project.phase = ScaffolderPhase.WRITING.value
                        write_ok = self._write_file(project_dir, sfile)
                        if write_ok:
                            sfile.written = True
                            project.files_written += 1
                            project.total_lines += sfile.content.count("\n") + 1
                        else:
                            project.errors.append(f"{sfile.path}: Failed to write to disk")

                    project.files_generated += 1

                except Exception as e:
                    sfile.error = str(e)
                    project.errors.append(f"{sfile.path}: {str(e)}")
                    logger.error("ProjectScaffolder: Error generating file %s: %s", sfile.path, e)

                # Update project state after each file (incremental tracking)
                project.updated_at = time.time()
                self._persist_project(project)

                logger.info("ProjectScaffolder: [%d/%d] %s — confidence=%.2f, written=%s, lines=%d",
                            i + 1, project.total_files, sfile.path,
                            sfile.confidence, sfile.written,
                            sfile.content.count("\n") + 1 if sfile.content else 0)

            # ── Phase 4: Final project validation ───────────────────────────
            project.phase = ScaffolderPhase.VALIDATING.value
            validation_result = await self._validate_project(project_dir)

            # ── Phase 5: Complete ───────────────────────────────────────────
            project.phase = ScaffolderPhase.COMPLETED.value
            project.completed_at = time.time()
            project.updated_at = time.time()

            self._total_projects_scaffolded += 1
            self._total_files_generated += project.files_generated
            self._total_lines_generated += project.total_lines

            self._persist_project(project)

            logger.info("ProjectScaffolder: Project '%s' completed — %d/%d files written, %d lines, %d errors",
                        name, project.files_written, project.total_files,
                        project.total_lines, len(project.errors))

            return {
                "success": project.files_written > 0,
                "project_id": project.id,
                "name": project.name,
                "project_type": project.project_type,
                "project_dir": project.project_dir,
                "total_files": project.total_files,
                "files_generated": project.files_generated,
                "files_written": project.files_written,
                "total_lines": project.total_lines,
                "errors": project.errors,
                "validation": validation_result,
                "files": [f.to_dict() for f in project.files],
            }

        except Exception as e:
            project.phase = ScaffolderPhase.FAILED.value
            project.errors.append(f"Fatal error: {str(e)}")
            self._persist_project(project)
            logger.error("ProjectScaffolder: Fatal error for project '%s': %s", name, e)
            return {
                "success": False,
                "project_id": project.id,
                "error": str(e),
            }

    # ═══════════════════════════════════════════════════════════════════════
    #  Structure Generation
    # ═══════════════════════════════════════════════════════════════════════

    async def _generate_structure(self, description: str, project_type: str,
                                  extra_files: dict = None) -> dict:
        """
        توليد هيكل المشروع عبر LLM — Generate directory structure via LLM.

        Uses the project type template as a baseline, then asks the LLM
        to customize and enhance the structure based on the description.

        Returns a dict with:
          {
            "files": {
              "path/to/file.ext": "description of what this file should contain",
              ...
            }
          }
        """
        template = PROJECT_TYPE_TEMPLATES.get(project_type, {})
        default_files = dict(template.get("default_files", {}))
        display_name = template.get("display_name", project_type)

        # Merge extra files from the user
        if extra_files:
            default_files.update(extra_files)

        if not self._llm_client:
            logger.warning("ProjectScaffolder: No LLM client — returning template structure only")
            return {"files": default_files}

        # Ask LLM to customize the structure based on the description
        system_prompt = f"""أنت مهندس برمجيات خبير. مهمتك هي تصميم هيكل مشروع كامل بناءً على وصف المستخدم.

نوع المشروع: {display_name}
القالب الأساسي يحتوي على {len(default_files)} ملف.

قواعد صارمة:
1. احتفظ بجميع ملفات القالب الأساسي — لا تحذف أي ملف
2. يمكنك إضافة ملفات جديدة إذا كان الوصف يتطلب ذلك
3. قم بتحسين وصف كل ملف ليكون أكثر تحديداً بناءً على وصف المشروع
4. أجب بصيغة JSON فقط
5. المفتاح هو مسار الملف والقيمة هي وصف ما يجب أن يحتويه

صيغة الإجابة:
{{
    "files": {{
        "path/to/file.ext": "وصف تفصيلي لمحتوى الملف",
        ...
    }}
}}"""

        user_prompt = f"""صمّم هيكل مشروع {display_name} بناءً على الوصف التالي:

الوصف: {description}

الملفات الأساسية المتوفرة:
{json.dumps(default_files, ensure_ascii=False, indent=2)}

قم بتحسين أوصاف الملفات وإضافة أي ملفات إضافية يحتاجها المشروع بناءً على الوصف."""

        try:
            response = await self._llm_client.chat(
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt),
                ],
                model="glm-5.1",
                temperature=0.3,
                json_mode=True,
                max_tokens=4096,
            )

            if response and response.text:
                parsed = response.extract_json()
                if parsed and "files" in parsed and isinstance(parsed["files"], dict):
                    # Merge: start with defaults, overlay LLM customizations
                    merged_files = dict(default_files)
                    for path, desc in parsed["files"].items():
                        if isinstance(desc, str) and len(desc) > 5:
                            merged_files[path] = desc
                    logger.info("ProjectScaffolder: LLM enhanced structure — %d files (was %d in template)",
                                len(merged_files), len(default_files))
                    return {"files": merged_files}
                else:
                    logger.warning("ProjectScaffolder: LLM structure response missing 'files' key — using template")
            else:
                logger.warning("ProjectScaffolder: LLM returned empty structure response — using template")

        except Exception as e:
            logger.error("ProjectScaffolder: LLM structure generation failed: %s — using template", e)

        # Fallback to template
        return {"files": default_files}

    # ═══════════════════════════════════════════════════════════════════════
    #  File Generation
    # ═══════════════════════════════════════════════════════════════════════

    async def _generate_file(self, file_path: str, description: str, language: str,
                             project_name: str = "", project_description: str = "",
                             project_type: str = "", all_files: dict = None) -> str:
        """
        توليد محتوى ملف عبر LLM — Generate file content via LLM.

        Uses the LLM client to generate real, functional code for the specified file.
        Falls back to CodeGenerationEngine if direct LLM call fails.
        """
        # Try CodeGenerationEngine first (it has dual-model writer+reviewer)
        if self._code_gen_engine:
            try:
                gen = await self._code_gen_engine.generate_code(
                    description=f"{project_name}: {description}",
                    target_file=file_path,
                    context=self._build_file_context(project_name, project_description,
                                                     project_type, file_path, all_files),
                    language=language,
                )
                if gen.generated_code and len(gen.generated_code.strip()) > 10:
                    logger.info("ProjectScaffolder: Generated %s via CodeGenEngine (confidence=%.2f)",
                                file_path, gen.confidence)
                    return gen.generated_code
            except Exception as e:
                logger.warning("ProjectScaffolder: CodeGenEngine failed for %s: %s", file_path, e)

        # Fallback: Direct LLM call
        if self._llm_client:
            try:
                lang_config = self._get_language_prompt_config(language)
                system_prompt = f"""أنت مبرمج خبير. اكتب محتوى الملف التالي كاملاً وجاهزاً للتنفيذ.

قواعد صارمة:
1. اكتب محتوى كامل وصالح — لا حشو ولا تعليقات فارغة
2. أضف docstrings/comments عند الحاجة
3. أضف معالجة أخطاء (try/except أو try/catch) عند الحاجة
4. لا تستخدم os.system أو exec() أو eval() — أنماط محظورة
5. المحتوى يجب أن يعمل مباشرة بدون تعديل
6. أجب بالمحتوى فقط — بدون شرح إضافي قبل أو بعد
7. لا تضع المحتوى في markdown code blocks

{lang_config['prompt_suffix']}"""

                user_prompt = f"""اكتب محتوى الملف: {file_path}

المشروع: {project_name}
الوصف: {project_description}
نوع المشروع: {project_type}

وصف هذا الملف: {description}"""

                if all_files:
                    other_files = [f"  - {p}: {d[:80]}" for p, d in all_files.items() if p != file_path]
                    if other_files:
                        user_prompt += f"\n\nملفات أخرى في المشروع:\n" + "\n".join(other_files[:15])

                response = await self._llm_client.chat(
                    messages=[
                        LLMMessage(role="system", content=system_prompt),
                        LLMMessage(role="user", content=user_prompt),
                    ],
                    model="glm-5.1",
                    temperature=0.2,
                    max_tokens=4096,
                )

                if response and response.text:
                    code = _clean_llm_output(response.text)
                    if code and len(code) > 10:
                        logger.info("ProjectScaffolder: Generated %s via direct LLM call (%d lines)",
                                    file_path, code.count("\n") + 1)
                        return code

            except Exception as e:
                logger.error("ProjectScaffolder: Direct LLM call failed for %s: %s", file_path, e)

        # Last resort: Generate a basic template
        logger.warning("ProjectScaffolder: All LLM methods failed for %s — using basic template", file_path)
        return self._generate_basic_file_template(file_path, description, language, project_name)

    def _build_file_context(self, project_name: str, project_description: str,
                            project_type: str, current_file: str,
                            all_files: dict = None) -> str:
        """Build context string for file generation that describes the overall project."""
        parts = [
            f"Project: {project_name}",
            f"Type: {project_type}",
            f"Description: {project_description}",
            f"Current file: {current_file}",
        ]
        if all_files:
            other_files = [f"  {p}" for p in all_files.keys() if p != current_file]
            if other_files:
                parts.append(f"Other project files:\n" + "\n".join(other_files[:20]))
        return "\n".join(parts)

    def _get_language_prompt_config(self, language: str) -> dict:
        """Get language-specific prompt configuration."""
        configs = {
            "python": {
                "prompt_suffix": "Write clean Python with type hints, docstrings, error handling, and logging. Use dataclasses/Pydantic where appropriate.",
            },
            "typescript": {
                "prompt_suffix": "Write clean TypeScript with proper interfaces, types, and JSDoc comments. Use modern ES6+ syntax.",
            },
            "javascript": {
                "prompt_suffix": "Write clean JavaScript with JSDoc comments. Use modern ES6+ syntax (async/await, destructuring, etc).",
            },
            "json": {
                "prompt_suffix": "Return valid JSON only. No markdown, no comments, no explanation — just the JSON object.",
            },
            "yaml": {
                "prompt_suffix": "Return valid YAML only. Use spaces (not tabs) for indentation. No markdown wrappers.",
            },
            "toml": {
                "prompt_suffix": "Return valid TOML only. No markdown wrappers.",
            },
            "dockerfile": {
                "prompt_suffix": "Write a production-ready Dockerfile with multi-stage build, proper .dockerignore, and security best practices.",
            },
            "markdown": {
                "prompt_suffix": "Write professional Markdown with proper headings, code examples, and clear structure.",
            },
            "css": {
                "prompt_suffix": "Write clean CSS with proper selectors, variables, and responsive design considerations.",
            },
        }
        return configs.get(language, configs.get("python", {"prompt_suffix": ""}))

    def _generate_basic_file_template(self, file_path: str, description: str,
                                       language: str, project_name: str = "") -> str:
        """Generate a basic template as last resort when all LLM methods fail."""
        basename = Path(file_path).stem
        ext = Path(file_path).suffix.lower()

        # Empty __init__.py files
        if basename == "__init__" and ext == ".py":
            return ""

        # README
        if ext == ".md":
            return f"""# {project_name or basename}

{description}

## Setup

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run the project
python -m app.main
```

## Project Structure

```
{project_name or basename}/
├── app/
│   ├── main.py
│   ├── models.py
│   └── config.py
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

## License

MIT
"""

        # requirements.txt
        if file_path == "requirements.txt":
            return """fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
sqlalchemy>=2.0.0
httpx>=0.25.0
python-dotenv>=1.0.0
"""

        # Dockerfile
        if basename.lower() == "dockerfile" or file_path.lower() == "dockerfile":
            return f"""FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

        # docker-compose.yml
        if "docker-compose" in file_path:
            return f"""version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/{project_name or 'app'}
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: {project_name or 'app'}
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
"""

        # .env.example
        if basename.startswith(".env"):
            return """# Application
APP_NAME=MyApp
APP_ENV=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/app

# Security
SECRET_KEY=change-me-in-production
"""

        # .gitignore
        if basename == ".gitignore":
            return """# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg

# Virtual environments
venv/
.venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment variables
.env
.env.local

# Database
*.db
*.sqlite3

# OS
.DS_Store
Thumbs.db

# Node (for full-stack)
node_modules/
.next/
out/
"""

        # package.json
        if basename == "package":
            return json.dumps({
                "name": project_name or basename,
                "version": "1.0.0",
                "private": True,
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                    "lint": "next lint"
                },
                "dependencies": {
                    "next": "14.1.0",
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                    "typescript": "^5.3.0"
                },
                "devDependencies": {
                    "@types/node": "^20.0.0",
                    "@types/react": "^18.2.0",
                    "tailwindcss": "^3.4.0",
                    "autoprefixer": "^10.4.0",
                    "postcss": "^8.4.0"
                }
            }, indent=2)

        # tsconfig.json
        if basename == "tsconfig":
            return json.dumps({
                "compilerOptions": {
                    "target": "es5",
                    "lib": ["dom", "dom.iterable", "esnext"],
                    "allowJs": True,
                    "skipLibCheck": True,
                    "strict": True,
                    "noEmit": True,
                    "esModuleInterop": True,
                    "module": "esnext",
                    "moduleResolution": "bundler",
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "jsx": "preserve",
                    "incremental": True,
                    "paths": {"@/*": ["./src/*"]}
                },
                "include": ["src/**/*"],
                "exclude": ["node_modules"]
            }, indent=2)

        # Python files
        if ext == ".py":
            return f'''"""
{project_name or basename} — {description}

Auto-generated by ProjectScaffolder
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class {basename.title().replace("_", "")}:
    """{description}"""

    def __init__(self):
        self._initialized = False
        logger.info("{basename}: Initialized")

    async def execute(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a task."""
        context = context or {{}}
        try:
            # TODO: Implement actual logic for: {description}
            result = {{"task": task, "status": "completed"}}
            return result
        except Exception as e:
            logger.error("Execution failed: %s", e)
            return {{"status": "error", "error": str(e)}}
'''

        # TypeScript files
        if ext in (".ts", ".tsx"):
            return f'''/**
 * {project_name or basename} — {description}
 *
 * Auto-generated by ProjectScaffolder
 */

import {{ Logger }} from "winston";

const logger = Logger.createLogger({{ level: "info" }});

export class {basename.title().replace("_", "")} {{
  private initialized: boolean = false;

  constructor() {{
    this.initialized = true;
    logger.info("{basename}: Initialized");
  }}

  async execute(task: string, context: Record<string, any> = {{}}): Promise<Record<string, any>> {{
    try {{
      // TODO: Implement actual logic for: {description}
      return {{ task, status: "completed" }};
    }} catch (error) {{
      logger.error("Execution failed:", error);
      return {{ status: "error", error: String(error) }};
    }}
  }}
}}
'''

        # CSS files
        if ext == ".css":
            return """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground: #000000;
  --background: #ffffff;
}

body {
  color: var(--foreground);
  background: var(--background);
  font-family: system-ui, -apple-system, sans-serif;
}
"""

        # Generic fallback
        return f"# {project_name or basename} — {description}\n# Auto-generated by ProjectScaffolder\n"

    # ═══════════════════════════════════════════════════════════════════════
    #  File Writing
    # ═══════════════════════════════════════════════════════════════════════

    def _write_file(self, project_dir: str, sfile: ScaffolderFile) -> bool:
        """
        كتابة ملف إلى القرص — Write a generated file to disk.

        Creates parent directories as needed.
        Returns True on success, False on failure.
        """
        try:
            full_path = Path(project_dir) / sfile.path

            # Security: Ensure the resolved path is within the project directory
            resolved = full_path.resolve()
            project_resolved = Path(project_dir).resolve()
            try:
                resolved.relative_to(project_resolved)
            except ValueError:
                logger.error("ProjectScaffolder: Path traversal attempt blocked: %s", sfile.path)
                sfile.error = "Path traversal blocked"
                return False

            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file content
            content = sfile.content
            if not content and full_path.name == "__init__.py":
                content = ""  # Empty __init__.py is valid

            full_path.write_text(content, encoding="utf-8")
            logger.debug("ProjectScaffolder: Wrote %s (%d bytes)", sfile.path, len(content))
            return True

        except Exception as e:
            logger.error("ProjectScaffolder: Failed to write %s: %s", sfile.path, e)
            sfile.error = str(e)
            return False

    # ═══════════════════════════════════════════════════════════════════════
    #  Project Validation
    # ═══════════════════════════════════════════════════════════════════════

    async def _validate_project(self, project_dir: str) -> dict:
        """
        التحقق من صحة المشروع الكامل — Validate the generated project as a whole.

        Checks:
          1. Project directory exists and is non-empty
          2. Key files exist (README, entry point, config)
          3. No obviously broken files (empty critical files)
          4. Docker files are valid (if present)
          5. Package files are valid (if present)

        Returns a dict with validation results.
        """
        result = {
            "valid": True,
            "checks": [],
            "warnings": [],
            "errors": [],
        }

        project_path = Path(project_dir)

        # ── 1. Directory exists and non-empty ──────────────────────────────
        if not project_path.exists():
            result["valid"] = False
            result["errors"].append("Project directory does not exist")
            return result

        all_files = list(project_path.rglob("*"))
        file_count = len([f for f in all_files if f.is_file()])
        result["checks"].append(f"Project has {file_count} files")

        if file_count == 0:
            result["valid"] = False
            result["errors"].append("Project directory is empty")
            return result

        # ── 2. README exists ───────────────────────────────────────────────
        readme_candidates = ["README.md", "README.rst", "README.txt", "README"]
        has_readme = any((project_path / r).exists() for r in readme_candidates)
        if has_readme:
            result["checks"].append("README file found ✓")
        else:
            result["warnings"].append("No README file found — consider adding one")

        # ── 3. Check for empty critical files ──────────────────────────────
        critical_patterns = [
            "main.py", "app/main.py", "index.ts", "src/index.ts",
            "src/app/page.tsx", "src/app/layout.tsx",
        ]
        for pattern in critical_patterns:
            candidate = project_path / pattern
            if candidate.exists():
                try:
                    content = candidate.read_text(encoding="utf-8")
                    if len(content.strip()) < 5:
                        result["warnings"].append(f"Critical file {pattern} is nearly empty")
                    else:
                        result["checks"].append(f"Entry point {pattern} has content ✓")
                except Exception as e:
                    result["warnings"].append(f"Could not read {pattern}: {e}")

        # ── 4. Validate Docker files ──────────────────────────────────────
        dockerfile = project_path / "Dockerfile"
        if dockerfile.exists():
            try:
                content = dockerfile.read_text(encoding="utf-8")
                if "FROM" in content.upper():
                    result["checks"].append("Dockerfile has FROM instruction ✓")
                else:
                    result["warnings"].append("Dockerfile missing FROM instruction")
            except Exception:
                result["warnings"].append("Could not read Dockerfile")

        docker_compose = project_path / "docker-compose.yml"
        if not docker_compose.exists():
            docker_compose = project_path / "docker-compose.yaml"
        if docker_compose.exists():
            try:
                content = docker_compose.read_text(encoding="utf-8")
                if "services:" in content:
                    result["checks"].append("docker-compose.yml has services ✓")
                else:
                    result["warnings"].append("docker-compose.yml missing services section")
            except Exception:
                result["warnings"].append("Could not read docker-compose.yml")

        # ── 5. Validate package files ──────────────────────────────────────
        package_json = project_path / "package.json"
        if package_json.exists():
            try:
                content = package_json.read_text(encoding="utf-8")
                pkg = json.loads(content)
                if "name" in pkg and "scripts" in pkg:
                    result["checks"].append("package.json is valid ✓")
                else:
                    result["warnings"].append("package.json missing name or scripts")
            except json.JSONDecodeError:
                result["errors"].append("package.json is invalid JSON")
            except Exception:
                result["warnings"].append("Could not read package.json")

        requirements_txt = project_path / "requirements.txt"
        if requirements_txt.exists():
            try:
                content = requirements_txt.read_text(encoding="utf-8")
                lines = [l.strip() for l in content.strip().split("\n") if l.strip() and not l.startswith("#")]
                if len(lines) > 0:
                    result["checks"].append(f"requirements.txt has {len(lines)} dependencies ✓")
                else:
                    result["warnings"].append("requirements.txt is empty")
            except Exception:
                result["warnings"].append("Could not read requirements.txt")

        # ── 6. LLM-based project review (if available) ────────────────────
        if self._llm_client and file_count >= 3:
            try:
                file_list_str = "\n".join(
                    f"  {f.relative_to(project_path)} ({f.stat().st_size} bytes)"
                    for f in sorted(all_files)[:30]
                    if f.is_file()
                )

                review_response = await self._llm_client.think(
                    prompt=f"""Review this project structure and identify any issues:

Project files:
{file_list_str}

Is this a valid, well-structured project? What's missing?

Answer in JSON:
{{
    "score": 0.0-1.0,
    "missing_critical": ["file1", "file2"],
    "suggestions": ["suggestion1", "suggestion2"]
}}""",
                    system="You are a senior software architect reviewing project structures. Answer in JSON only.",
                    model="deepseek-chat",
                    temperature=0.2,
                )

                review_data = review_response.extract_json()
                if review_data:
                    score = review_data.get("score", 0.5)
                    if score < 0.5:
                        result["valid"] = False
                    missing = review_data.get("missing_critical", [])
                    if missing:
                        result["warnings"].extend([f"Missing: {m}" for m in missing[:5]])
                    suggestions = review_data.get("suggestions", [])
                    if suggestions:
                        result["checks"].extend([f"💡 {s}" for s in suggestions[:3]])

            except Exception as e:
                logger.debug("ProjectScaffolder: LLM project review failed: %s", e)

        return result

    # ═══════════════════════════════════════════════════════════════════════
    #  Status & Persistence
    # ═══════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """
        معلومات الحالة — Status information about the scaffolder.
        """
        return {
            "initialized": self._initialized,
            "has_llm_client": self._llm_client is not None,
            "has_code_gen_engine": self._code_gen_engine is not None,
            "total_projects_scaffolded": self._total_projects_scaffolded,
            "total_files_generated": self._total_files_generated,
            "total_lines_generated": self._total_lines_generated,
            "active_projects": len(self._projects),
            "supported_project_types": [pt.value for pt in ProjectType],
            "confidence_threshold": self.CONFIDENCE_THRESHOLD,
        }

    def get_project(self, project_id: str) -> Optional[dict]:
        """Get a scaffolded project by ID."""
        if project_id in self._projects:
            return self._projects[project_id].to_dict()
        # Try loading from DB
        return self._load_project_from_db(project_id)

    def list_projects(self) -> List[dict]:
        """List all scaffolded projects (in-memory + from DB)."""
        projects = []

        # In-memory projects
        for project in self._projects.values():
            projects.append({
                "id": project.id,
                "name": project.name,
                "project_type": project.project_type,
                "phase": project.phase,
                "files_written": project.files_written,
                "total_files": project.total_files,
                "created_at": project.created_at,
            })

        # DB projects not in memory
        try:
            conn = get_db_connection(self._db_path)
            try:
                cursor = conn.execute("""
                    SELECT id, name, project_type, phase, files_written, total_files, created_at
                    FROM ps_projects
                    ORDER BY created_at DESC
                """)
                for row in cursor.fetchall():
                    if row["id"] not in self._projects:
                        projects.append({
                            "id": row["id"],
                            "name": row["name"],
                            "project_type": row["project_type"],
                            "phase": row["phase"],
                            "files_written": row["files_written"],
                            "total_files": row["total_files"],
                            "created_at": row["created_at"],
                        })
            finally:
                conn.close()
        except Exception as e:
            logger.warning("ProjectScaffolder: Failed to load projects from DB: %s", e)

        return projects

    def _persist_project(self, project: ScaffoldedProject):
        """Persist project state to the unified database."""
        try:
            conn = get_db_connection(self._db_path)
            try:
                files_json = json.dumps(
                    [f.to_dict() for f in project.files],
                    ensure_ascii=False,
                )
                errors_json = json.dumps(project.errors, ensure_ascii=False)

                conn.execute("""
                    INSERT OR REPLACE INTO ps_projects
                    (id, name, description, project_type, phase, project_dir,
                     total_files, files_generated, files_written, total_lines,
                     errors, created_at, updated_at, completed_at,
                     llm_tokens_used, llm_calls, files_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project.id, project.name, project.description,
                    project.project_type, project.phase, project.project_dir,
                    project.total_files, project.files_generated,
                    project.files_written, project.total_lines,
                    errors_json, project.created_at, project.updated_at,
                    project.completed_at, project.llm_tokens_used,
                    project.llm_calls, files_json,
                ))
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("ProjectScaffolder: Failed to persist project %s: %s", project.id, e)

    def _load_project_from_db(self, project_id: str) -> Optional[dict]:
        """Load a project from the database by ID."""
        try:
            conn = get_db_connection(self._db_path)
            try:
                cursor = conn.execute(
                    "SELECT * FROM ps_projects WHERE id = ?",
                    (project_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None

                result = dict(row)
                # Parse JSON fields
                try:
                    result["errors"] = json.loads(result.get("errors", "[]"))
                except (json.JSONDecodeError, TypeError):
                    result["errors"] = []
                try:
                    result["files"] = json.loads(result.get("files_json", "[]"))
                except (json.JSONDecodeError, TypeError):
                    result["files"] = []

                return result
            finally:
                conn.close()
        except Exception as e:
            logger.warning("ProjectScaffolder: Failed to load project %s from DB: %s", project_id, e)
            return None

    def delete_project(self, project_id: str) -> bool:
        """
        حذف مشروع — Delete a scaffolded project from the database.

        Note: This does NOT delete the generated files on disk.
        """
        try:
            # Remove from memory
            if project_id in self._projects:
                del self._projects[project_id]

            # Remove from database
            conn = get_db_connection(self._db_path)
            try:
                conn.execute("DELETE FROM ps_files WHERE project_id = ?", (project_id,))
                conn.execute("DELETE FROM ps_projects WHERE id = ?", (project_id,))
                conn.commit()
            finally:
                conn.close()

            logger.info("ProjectScaffolder: Deleted project %s", project_id)
            return True
        except Exception as e:
            logger.error("ProjectScaffolder: Failed to delete project %s: %s", project_id, e)
            return False

    def get_supported_types(self) -> List[dict]:
        """Get all supported project types with their descriptions."""
        result = []
        for pt in ProjectType:
            template = PROJECT_TYPE_TEMPLATES.get(pt.value, {})
            result.append({
                "type": pt.value,
                "display_name": template.get("display_name", pt.value),
                "display_name_ar": template.get("display_name_ar", ""),
                "default_file_count": len(template.get("default_files", {})),
                "language": template.get("language", "python"),
            })
        return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_project_scaffolder: Optional[ProjectScaffolder] = None


def get_project_scaffolder() -> ProjectScaffolder:
    """
    الحصول على منشئ المشاريع (Singleton) — Get the ProjectScaffolder singleton.
    """
    global _project_scaffolder
    if _project_scaffolder is None:
        _project_scaffolder = ProjectScaffolder()
        _project_scaffolder.initialize()
    return _project_scaffolder

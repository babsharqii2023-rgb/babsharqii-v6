#!/usr/bin/env python3
"""
BABSHARQII v40.0 "Mamoun" — Standalone Runner
Quick-start script for running the FastAPI backend directly.

Usage:
    python run.py                  # Start backend on 0.0.0.0:8000
    python run.py --port 9000      # Use custom port
    python run.py --host 127.0.0.1 # Bind to localhost only
    python run.py --reload         # Enable auto-reload (development)
    python run.py --workers 4      # Run with multiple workers
    python run.py --check          # Only check configuration
"""

import argparse
import sys
import os
from pathlib import Path

# Ensure backend directory is in Python path
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))


def check_configuration():
    """Validate that the system is properly configured."""
    errors = []
    warnings = []

    # Check .env file
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        # Check project root .env as well
        root_env = BACKEND_DIR.parent / ".env"
        if not root_env.exists():
            errors.append(".env file not found — copy .env.example to .env and configure")
        else:
            print(f"  [OK] Using .env from project root")
    else:
        print(f"  [OK] .env file found")

    # Check laws.yaml
    laws_file = BACKEND_DIR / "laws.yaml"
    if not laws_file.exists():
        errors.append("laws.yaml not found — critical safety file missing!")
    else:
        print(f"  [OK] laws.yaml found")

    # Check required Python packages
    required_packages = ["fastapi", "uvicorn", "pydantic", "pydantic_settings", "yaml"]
    for pkg in required_packages:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg} installed")
        except ImportError:
            import_name = pkg.replace("_", "-")
            if pkg == "yaml":
                import_name = "pyyaml"
            elif pkg == "pydantic_settings":
                import_name = "pydantic-settings"
            errors.append(f"{pkg} not installed — run: pip install {import_name}")

    # Check optional Python packages
    optional_packages = {
        "chromadb": "chromadb (Episodic Memory vector store)",
        "neo4j": "neo4j (Semantic Memory graph)",
        "psycopg2": "psycopg2-binary (PostgreSQL for Episodic Memory)",
        "whisper": "openai-whisper (STT Engine)",
    }
    for pkg, desc in optional_packages.items():
        try:
            __import__(pkg)
            print(f"  [OK] {desc}")
        except ImportError:
            warnings.append(f"{desc} not installed (optional)")

    # Check directories
    for d in ["data", "logs", "sandbox", "backups"]:
        dir_path = BACKEND_DIR / d
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  [OK] Created directory: {d}/")
        else:
            print(f"  [OK] Directory exists: {d}/")

    # Print results
    if warnings:
        print("\n  Warnings:")
        for w in warnings:
            print(f"    [!] {w}")

    if errors:
        print("\n  Errors:")
        for e in errors:
            print(f"    [X] {e}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="BABSHARQII v40.0 'Mamoun' — FastAPI Backend Runner"
    )
    parser.add_argument(
        "--host", default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Port to bind (default: 8000)"
    )
    parser.add_argument(
        "--reload", action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Number of uvicorn workers (default: 1)"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Only check configuration and exit"
    )
    parser.add_argument(
        "--log-level", default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)"
    )

    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  BABSHARQII v40.0 \"Mamoun\" — Backend Runner")
    print("  7 AGI Pathways | Self-Evolving Digital Organism")
    print("=" * 60)
    print()

    # Check configuration
    print("Checking configuration...")
    if not check_configuration():
        print("\nConfiguration check failed. Fix the errors above and try again.")
        sys.exit(1)

    if args.check:
        print("\nConfiguration check passed!")
        sys.exit(0)

    print("\nConfiguration OK. Starting server...")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Reload: {args.reload}")
    print(f"  Workers: {args.workers}")
    print(f"  Log level: {args.log_level}")
    print()

    # Import and run uvicorn
    import uvicorn

    uvicorn.run(
        "mamoun.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level,
        app_dir=str(BACKEND_DIR),
    )


if __name__ == "__main__":
    main()

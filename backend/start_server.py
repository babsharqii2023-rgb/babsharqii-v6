#!/usr/bin/env python3
"""
Mamoun Backend — Quick-Start Script (v62 FIXED)

v62 FIX: Now uses the canonical main.py FastAPI app with full initialization.
The old version created a SEPARATE FastAPI app without any lifespan logic,
resulting in broken routes that reference uninitialized singletons.

This script now properly delegates to `python3 backend/run.py`.
"""

import subprocess
import sys
import os

def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    run_py = os.path.join(backend_dir, "run.py")
    
    if not os.path.isfile(run_py):
        print(f"[ERROR] run.py not found at {run_py}", file=sys.stderr)
        sys.exit(1)
    
    # Delegate to the proper run.py with full initialization
    print("[Mamoun v62] Starting via run.py (full initialization)...")
    subprocess.run(
        [sys.executable, run_py, "--host", "0.0.0.0", "--port", "8000"],
        cwd=backend_dir,
    )


if __name__ == '__main__':
    main()

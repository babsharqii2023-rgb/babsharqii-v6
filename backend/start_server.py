#!/usr/bin/env python3
"""Quick-start script for Mamoun Backend"""
import uvicorn
import signal
import sys
import os

def main():
    # Add backend dir to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from mamoun.api.routes import api_router
    from fastapi import FastAPI

    app = FastAPI(title='Mamoun v40.0')
    app.include_router(api_router, prefix='/api')

    # Handle signals gracefully
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

    print(f"[Mamoun] Starting backend on 0.0.0.0:8000 with {len(api_router.routes)} routes", flush=True)
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')

if __name__ == '__main__':
    main()

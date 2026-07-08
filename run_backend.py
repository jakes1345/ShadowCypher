#!/usr/bin/env python3
"""Standalone chat backend runner - bypasses Fly deployment issues."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    import uvicorn
    from shadowcypher.main_chat import app

    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"🚀 Starting ShadowCypher Chat Backend on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

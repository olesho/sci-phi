#!/usr/bin/env python3
"""
Uvicorn configuration for development with hot reload exclusions.
Run with: uv run python uvicorn_config.py
"""
import subprocess
import sys

def main():
    """Start uvicorn with configuration using uv run."""
    cmd = [
        "uv", "run", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        "--reload-exclude", "data/*",
        "--reload-exclude", "*.db", 
        "--reload-exclude", "__pycache__/*",
        "--reload-exclude", "*.pyc",
        "--reload-exclude", "*.pyo",
        "--log-level", "info"
    ]
    
    print("Starting FastAPI development server with hot reload...")
    print("Excluding: data/, *.db, __pycache__/, *.pyc, *.pyo")
    print("Server will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main() 
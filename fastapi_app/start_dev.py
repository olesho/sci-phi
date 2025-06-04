#!/usr/bin/env python3
"""
Development server script that starts FastAPI with hot reload but excludes the data directory.
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    # Get the current directory (fastapi_app)
    current_dir = Path(__file__).parent
    
    # Change to the fastapi_app directory
    os.chdir(current_dir)
    
    # Use uv run uvicorn with reload-excludes to exclude the data directory
    cmd = [
        "uv", "run", "uvicorn",
        "main:app",
        "--reload",
        "--reload-exclude", "data/*",
        "--reload-exclude", "*.db",
        "--reload-exclude", "__pycache__/*",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]
    
    print("Starting FastAPI development server with hot reload...")
    print("Excluding: data/, *.db, __pycache__/")
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
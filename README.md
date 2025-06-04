# SCI-AI

A FastAPI application for processing PDF files with hot reload functionality that excludes the data directory.

## Quick Start

**Development (with hot reload, excluding data directory):**
```bash
make dev
# or
make dev-script
# or
cd fastapi_app && python start_dev.py
```

**Production:**
```bash
make prod
```

**Using Docker:**
```bash
# Development
make docker-dev

# Production  
make docker-prod
```

See `fastapi_app/README.md` for detailed API documentation.

## FastAPI
- Using make: ```make dev```
- Or run: ```cd fastapi_app && python start_dev.py```.
- Or: ```cd fastapi_app && uv run uvicorn main:app --reload --reload-exclude "data/*" --reload-exclude "*.db"```

## Streamlit
Run: ```uv tool run streamlit run streamlit_app/main.py```
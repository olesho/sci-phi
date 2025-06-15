# SCI-PHI

A FastAPI application for processing scientific papers in PDF format.

**Requires Python 3.12 or newer.**

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
The full OpenAPI specification can be found at `docs/openapi.yaml`.

## FastAPI
- Using make: ```make dev```
- Or run: ```cd fastapi_app && python start_dev.py```.
- Or: ```cd fastapi_app && uv run uvicorn main:app --reload --reload-exclude "data/*" --reload-exclude "*.db"```

## Streamlit
Run: ```uv tool run streamlit run streamlit_app/main.py```

Run `pytest` to execute the API tests.

FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /fastapi_app

# Install the application dependencies.
WORKDIR /fastapi_app
RUN uv sync --frozen --no-cache

# Run the application.
CMD ["/fastapi_app/.venv/bin/fastapi", "run", "fastapi_app/main.py", "--port", "80", "--host", "0.0.0.0"]
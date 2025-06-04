.PHONY: dev prod install clean test docker-dev docker-prod

# Development server with hot reload (excluding data directory)
dev:
	cd fastapi_app && uv run uvicorn main:app --reload --reload-exclude "data/*" --reload-exclude "*.db" --reload-exclude "__pycache__/*" --host 0.0.0.0 --port 8000

# Development server using the Python script
dev-script:
	cd fastapi_app && python start_dev.py

# Development server using uvicorn config
dev-config:
	cd fastapi_app && python uvicorn_config.py

# Production server (no hot reload)
prod:
	cd fastapi_app && uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Install dependencies
install:
	uv sync

# Clean cache and temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Run tests (if you have any)
test:
	pytest

# Docker development
docker-dev:
	docker-compose --profile development up fastapi-app-dev

# Docker production
docker-prod:
	docker-compose --profile production up fastapi-app

# Build docker image
docker-build:
	docker-compose build

# Help
help:
	@echo "Available commands:"
	@echo "  dev          - Start development server with hot reload (excludes data/)"
	@echo "  dev-script   - Start development server using Python script"
	@echo "  dev-config   - Start development server using uvicorn config"
	@echo "  prod         - Start production server"
	@echo "  install      - Install dependencies using uv"
	@echo "  clean        - Clean cache and temporary files"
	@echo "  test         - Run tests"
	@echo "  docker-dev   - Start development server using Docker"
	@echo "  docker-prod  - Start production server using Docker"
	@echo "  docker-build - Build Docker image"
	@echo "  help         - Show this help message" 
# FileWallBall Development Makefile
# =================================

.PHONY: help install test lint run clean docker-build docker-run

# Default target
help:
	@echo "FileWallBall Development Commands:"
	@echo "=================================="
	@echo "install     - Install dependencies using uv"
	@echo "test        - Run tests with pytest"
	@echo "test-cov    - Run tests with coverage"
	@echo "test-integration - Run comprehensive integration tests"
	@echo "test-performance - Run performance tests only"
	@echo "test-stress - Run stress tests only"
	@echo "lint        - Run linting tools (black, isort, flake8, mypy)"
	@echo "format      - Format code with black and isort"
	@echo "run         - Run development server"
	@echo "run-prod    - Run production server"
	@echo "clean       - Clean Python cache files"
	@echo "docker-build- Build Docker image"
	@echo "docker-run  - Run with Docker Compose"
	@echo "verify      - Verify project structure"
	@echo "setup       - Complete development setup"

# Install dependencies
install:
	@echo "Installing dependencies..."
	uv sync

# Run tests
test:
	@echo "Running tests..."
	uv run pytest tests/ -v

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	uv run pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	uv run python tests/integration/run_integration_tests.py

# Run integration tests with specific file
test-integration-file:
	@echo "Running specific integration test file..."
	uv run python tests/integration/run_integration_tests.py --test-file $(FILE)

# Run performance tests only
test-performance:
	@echo "Running performance tests only..."
	uv run python tests/integration/run_integration_tests.py --performance-only

# Run stress tests only
test-stress:
	@echo "Running stress tests only..."
	uv run python tests/integration/run_integration_tests.py --stress-only

# Run linting tools
lint:
	@echo "Running linting tools..."
	uv run black --check app/ tests/ scripts/
	uv run isort --check-only app/ tests/ scripts/
	uv run flake8 app/ tests/ scripts/
	uv run mypy app/

# Format code
format:
	@echo "Formatting code..."
	uv run black app/ tests/ scripts/
	uv run isort app/ tests/ scripts/

# Run development server
run:
	@echo "Starting development server..."
	uv run python -m app.main

# Run production server
run-prod:
	@echo "Starting production server..."
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Clean Python cache files
clean:
	@echo "Cleaning Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete

# Build Docker image
docker-build:
	@echo "Building Docker image..."
	docker build -t filewallball:latest .

# Run with Docker Compose
docker-run:
	@echo "Starting services with Docker Compose..."
	docker-compose up -d

# Verify project structure
verify:
	@echo "Verifying project structure..."
	uv run python scripts/verify_structure.py

# Complete development setup
setup: install verify
	@echo "Setting up pre-commit hooks..."
	uv run pre-commit install
	@echo "Development setup complete!"

# Database operations
db-migrate:
	@echo "Running database migrations..."
	uv run alembic upgrade head

db-rollback:
	@echo "Rolling back database migration..."
	uv run alembic downgrade -1

# Async database operations
db-migrate-async:
	@echo "Running async database migrations..."
	uv run python scripts/async_alembic.py upgrade

db-rollback-async:
	@echo "Rolling back async database migration..."
	uv run python scripts/async_alembic.py downgrade

db-revision-async:
	@echo "Creating async database migration..."
	uv run python scripts/async_alembic.py revision

db-current-async:
	@echo "Showing current async database revision..."
	uv run python scripts/async_alembic.py current

db-history-async:
	@echo "Showing async database migration history..."
	uv run python scripts/async_alembic.py history

# Redis operations
redis-start:
	@echo "Starting Redis server..."
	docker run -d --name redis-filewallball -p 6379:6379 redis:7-alpine

redis-stop:
	@echo "Stopping Redis server..."
	docker stop redis-filewallball
	docker rm redis-filewallball

# Development utilities
logs:
	@echo "Showing application logs..."
	tail -f logs/app.log

shell:
	@echo "Starting Python shell..."
	uv run python -i -c "from app.main import app; from app.config import get_settings; settings = get_settings()"

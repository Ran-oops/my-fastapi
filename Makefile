.PHONY: help build test test-fast test-cov lint fmt clean run cli init sync dev pre-commit

APP_NAME := enterprise-fastapi
.DEFAULT_GOAL := help

# Init the venv
init: sync
	@uvx prek install --hook-type commit-msg --hook-type pre-commit --hook-type pre-push

# Sync the project with the venv
sync:
	@uv sync

# Sync the project with dev dependencies
dev:
	@uv sync --all-extras --all-groups

# Build wheel
build:
	@uv build

# Test all
test:
	@uv run pytest tests -v

# Test fast
test-fast:
	@uv run pytest tests -v -m "not slow"

# Test with coverage
test-cov:
	@uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml

# Lint only
lint:
	@uvx ruff check app tests --fix

# Format only
fmt:
	@uvx ruff format app tests

# Lint + Format
ruff: fmt lint

# Run the application
run:
	@uv run uvicorn app.main:app --reload

# Run CLI with help
cli:
	@uv run python -c "from app.cli import app; app()" -- --help

# Clean build artifacts
clean:
	@rm -rf build dist *.egg-info htmlcov .coverage coverage.xml
	@rm -rf __pycache__ .pytest_cache .ruff_cache
	@rm -rf .mypy_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Database migrations
db-upgrade:
	@uv run alembic upgrade head

db-downgrade:
	@uv run alembic downgrade -1

db-migrate:
	@uv run alembic revision --autogenerate -m "$(message)"

# Pre-commit hooks
pre-commit:
	@uvx prek run --all-files

# Show help
help:
	@echo ""
	@echo "Usage:"
	@echo "    make [target]"
	@echo ""
	@echo "Targets:"
	@awk '/^[a-zA-Z\-_0-9]+:/ \
	{ \
		helpMessage = match(lastLine, /^# (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 2, RLENGTH); \
			printf "\033[36m%-22s\033[0m %s\n", helpCommand,helpMessage; \
		} \
	} { lastLine = $$0 }' $(MAKEFILE_LIST)

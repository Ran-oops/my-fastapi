# Enterprise FastAPI Project Commands

# Default recipe to show available commands
default:
    @just --list

# Init the venv and install pre-commit hooks
init: sync
    uvx prek install --hook-type commit-msg --hook-type pre-commit --hook-type pre-push

# Sync the project with the venv
sync:
    uv sync

# Sync the project with dev dependencies
dev:
    uv sync --all-extras --all-groups

# Build wheel
build:
    uv build

# Test all
test:
    uv run pytest tests -v

# Test fast (skip slow tests)
test-fast:
    uv run pytest tests -v -m "not slow"

# Test with coverage
test-cov:
    uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml

# Lint only
lint:
    uvx ruff check app tests --fix

# Format only
fmt:
    uvx ruff format app tests

# Lint + Format
ruff: fmt lint

# Run the application
run:
    uv run uvicorn app.main:app --reload

# Run CLI with help
cli:
    uv run python manage.py --help

# Clean build artifacts
clean:
    rm -rf build dist *.egg-info htmlcov .coverage coverage.xml
    rm -rf __pycache__ .pytest_cache .ruff_cache
    rm -rf .mypy_cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Database migrations - upgrade to head
db-upgrade:
    uv run alembic upgrade head

# Database migrations - downgrade one version
db-downgrade:
    uv run alembic downgrade -1

# Database migrations - create new migration
db-migrate message:
    uv run alembic revision --autogenerate -m "{{message}}"

# Pre-commit hooks - run all
pre-commit:
    uvx prek run --all-files

# Type check
typecheck:
    uvx ty check app

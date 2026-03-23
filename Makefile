.PHONY: help install dev test lint format check clean run

help:
	@echo "Available commands:"
	@echo "  make install    - Install production dependencies"
	@echo "  make dev        - Install development dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linting (ruff + ty)"
	@echo "  make format     - Format code"
	@echo "  make check      - Run all checks (lint + test)"
	@echo "  make clean      - Clean cache files"
	@echo "  make run        - Start the application"
	@echo "  make cli        - Run CLI with help"

install:
	uv sync

dev:
	uv sync --dev

test:
	uv run pytest tests -v --cov=app --cov-report=term-missing

lint:
	uvx ruff check app tests
	uvx ty check app

format:
	uvx ruff format app tests
	uvx ruff check --fix app tests

check: lint test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

run:
	uv run python run.py

cli:
	uv run python manage.py --help

db-upgrade:
	uv run alembic upgrade head

db-downgrade:
	uv run alembic downgrade -1

db-migrate:
	uv run alembic revision --autogenerate -m "$(message)"

pre-commit:
	uvx prek run --all-files

md-lint:
	uvx rumdl README.md

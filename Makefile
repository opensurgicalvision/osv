.PHONY: setup-ai check-ai lint format test test-sync help

help:
	@echo "OpenSurgicalVision (OSV) Development Commands:"
	@echo "  make setup-ai    - Generate all vendor AI configurations (.claude, cursor, copilot, aider, AGENTS.md) from .ai/"
	@echo "  make check-ai    - Check if vendor AI configs are in sync with .ai/ (used in CI)"
	@echo "  make lint        - Run ruff and mypy linters"
	@echo "  make format      - Format code with ruff"
	@echo "  make test        - Run test suite"
	@echo "  make test-sync   - Run AI config sync test"

setup-ai:
	python .ai/build.py

check-ai:
	python .ai/build.py --check

lint:
	ruff check .
	mypy osv tests

format:
	ruff format .
	ruff check --fix .

test:
	pytest tests/

test-sync:
	pytest tests/test_ai_sync.py

.PHONY: install dev-install sync lint format test clean help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package
	uv pip install .

dev-install: ## Install package in editable mode with dev deps
	uv sync --group dev

sync: ## Lock and sync all dependencies
	uv sync

lint: ## Run linter and format check
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-format code
	uv run ruff check --fix .
	uv run ruff format .

test: ## Run tests
	uv run pytest -v

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info __pycache__ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

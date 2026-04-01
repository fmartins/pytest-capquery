.DEFAULT_GOAL := help
.PHONY: setup test test-unit test-e2e db-up db-down clean format check-format help

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Install the package and dependencies
	pyenv install -s 3.13.0
	pyenv local 3.13.0
	python -m venv .venv
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -e '.[test]'

db-up: ## Start Docker Compose databases
	docker-compose up -d
	@echo "Waiting for databases to be ready..."
	@sleep 10
	@echo "Databases are ready."

db-down: ## Tear down Docker Compose databases
	docker-compose down -v

test: test-unit test-e2e ## Run all tests

test-unit: ## Run unit tests
	./.venv/bin/pytest -vvv tests/unit/

test-e2e: db-up ## Run E2E tests and strict dialect matrix
	./.venv/bin/pytest -vvv tests/e2e/ || (make db-down && exit 1)
	make db-down

clean: ## Remove virtual environment and cached files
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/

format: ## Run Prettier to format markdown, yaml, and json files
	npx prettier --write .

check-format: ## Check if files comply with Prettier formatting (for CI)
	npx prettier --check .

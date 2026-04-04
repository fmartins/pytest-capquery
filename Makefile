.DEFAULT_GOAL := help
.PHONY: setup setup-env install test tdd db-up db-down clean format check-format help

help:
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1,$$2 }' $(MAKEFILE_LIST)

setup: setup-env install

setup-env:
	pyenv install -s 3.13.0
	pyenv local 3.13.0

install:
	python -m venv .venv
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -e '.[test]'
	./.venv/bin/pre-commit install

db-up:
	docker compose up -d
	@echo "Waiting for databases to be ready..."
	@sleep 10
	@echo "Databases are ready."

db-down:
	docker compose down -v

test: db-up
	./.venv/bin/pytest -p no:capquery -n auto -vvv --cov=pytest_capquery --cov-report=term-missing --cov-report=xml --junitxml=junit.xml -o junit_family=legacy tests/ || (make db-down && exit 1)
	make db-down

tdd: db-up
	./.venv/bin/ptw src/ tests/ --now --runner ./.venv/bin/pytest -vvv -p no:capquery --capquery-update || (make db-down && exit 1)
	make db-down

clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/

format:
	npx prettier --write .

check-format:
	npx prettier --check .

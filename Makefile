.PHONY: setup test test-unit test-e2e db-up db-down clean

setup:
	pyenv install -s 3.13.0
	pyenv local 3.13.0
	python -m venv .venv
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -e '.[test]'

db-up:
	docker-compose up -d
	@echo "Waiting for databases to be ready..."
	@sleep 10
	@echo "Databases are ready."

db-down:
	docker-compose down -v

test: test-unit test-e2e

test-unit:
	./.venv/bin/pytest -vvv tests/unit/

test-e2e: db-up
	./.venv/bin/pytest -vvv tests/e2e/ || (make db-down && exit 1)
	make db-down

clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/

.PHONY: setup test clean

setup:
	pyenv install -s 3.11.0
	pyenv local 3.11.0
	python -m venv .venv
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -e '.[test]'

test:
	./.venv/bin/pytest tests/

clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/

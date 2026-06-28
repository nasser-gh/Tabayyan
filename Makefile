.PHONY: install test lint bench build docker clean

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

bench:
	python benchmarks/run.py --write

build:
	python -m build

docker:
	docker build -t tabayyan:local .

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

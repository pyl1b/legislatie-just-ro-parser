PYTHON_FILES := $(wildcard *.py)


init:
	pip install -e .


init-d:
	pip install -e .[dev]


test:
	mypy leropa tests
	pytest


lint:
	ruff check --force-exclude .


format:
	ruff format --force-exclude .


delint: format
	ruff check --fix --force-exclude .

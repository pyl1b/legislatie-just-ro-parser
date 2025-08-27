PYTHON_FILES := $(wildcard *.py)


init:
	pip install -e .


init-d:
	pip install -e .[dev]


test:
	pytest


lint:
	ruff check .


format:
	ruff format .


delint: format
	ruff check --fix .


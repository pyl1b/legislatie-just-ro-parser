"""Utilities for discovering optional LLM modules."""

from __future__ import annotations

from pathlib import Path

# Alias for a list of strings used for model names.
StrList = list[str]


def available_models() -> StrList:
    """Return available LLM model modules.

    Scans the ``leropa.llm`` package for Python modules and returns their
    names sorted alphabetically.

    Returns:
        Sorted list of module names.
    """

    # Locate the directory containing LLM modules.
    package_dir = Path(__file__).parent

    # Gather all Python files except ``__init__`` and private ones.
    modules = [
        path.stem
        for path in package_dir.glob("[!_]*.py")
        if path.stem != "__init__"
    ]

    # Return a deterministic list of module names.
    return sorted(modules)

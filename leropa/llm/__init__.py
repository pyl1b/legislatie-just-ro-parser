"""Utilities for discovering optional LLM modules."""

from __future__ import annotations

import os

import requests

# Alias for a list of strings used for model names.
StrList = list[str]


# Default endpoint for listing models on the local Ollama server.
OLLAMA_TAGS_URL = os.environ.get(
    "OLLAMA_TAGS_URL", "http://localhost:11434/api/tags"
)


def available_models() -> StrList:
    """Return model names available on the Ollama server.

    Returns:
        Sorted list of model names reported by the Ollama server. If the
        server cannot be reached or provides unexpected data, an empty list is
        returned.
    """

    try:
        # Request the list of models from the Ollama API.
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)

        # Raise for HTTP errors (4xx, 5xx) to trigger the exception handler.
        response.raise_for_status()

        # Parse the JSON payload.
        payload = response.json()
    except Exception:
        # In case of network errors or invalid responses, assume no models are
        # available to keep the caller logic simple.
        return []

    # Extract model names from the response, ignoring malformed entries.
    models = [
        m.get("name", "") for m in payload.get("models", []) if m.get("name")
    ]

    # Return a deterministic list of model names.
    return sorted(models)

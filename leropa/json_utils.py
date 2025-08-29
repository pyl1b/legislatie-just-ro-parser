"""JSON serialization helpers using optional orjson."""

from __future__ import annotations

try:
    import orjson  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    orjson = None  # type: ignore[assignment]

import json


def json_dumps(data: object) -> str:
    """Serialize data to a JSON string.

    Args:
        data: Data structure to serialize.

    Returns:
        JSON representation of ``data``.
    """

    if orjson is not None:
        return orjson.dumps(data).decode()
    return json.dumps(data, ensure_ascii=False)


def json_loads(data: str | bytes) -> object:
    """Deserialize JSON data from a string or bytes.

    Args:
        data: JSON content as ``str`` or ``bytes``.

    Returns:
        Parsed JSON object.
    """

    if orjson is not None:
        return orjson.loads(data)
    if isinstance(data, (bytes, bytearray)):
        return json.loads(data.decode())
    return json.loads(data)

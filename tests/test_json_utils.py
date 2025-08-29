"""Tests for JSON utility functions."""

import json

from pytest import MonkeyPatch

from leropa import json_utils


def test_json_dumps_without_orjson(monkeypatch: MonkeyPatch) -> None:
    """Serialize using standard json when orjson is absent."""

    monkeypatch.setattr(json_utils, "orjson", None)
    data = {"a": 1}
    assert json_utils.json_dumps(data) == json.dumps(data, ensure_ascii=False)


def test_json_dumps_with_orjson(monkeypatch: MonkeyPatch) -> None:
    """Serialize using orjson when available."""

    class Fake:
        def dumps(
            self, obj: object
        ) -> bytes:  # pragma: no cover - simple stub
            return b"{}"

    monkeypatch.setattr(json_utils, "orjson", Fake())
    assert json_utils.json_dumps({}) == "{}"


def test_json_loads_without_orjson(monkeypatch: MonkeyPatch) -> None:
    """Deserialize JSON using standard json when orjson is absent."""

    monkeypatch.setattr(json_utils, "orjson", None)
    data = {"a": 1}
    text = json.dumps(data)
    assert json_utils.json_loads(text) == data
    assert json_utils.json_loads(text.encode()) == data


def test_json_loads_with_orjson(monkeypatch: MonkeyPatch) -> None:
    """Deserialize JSON using orjson when available."""

    class Fake:
        def loads(self, data: bytes) -> dict:  # pragma: no cover - simple stub
            return {"b": 2}

    monkeypatch.setattr(json_utils, "orjson", Fake())
    assert json_utils.json_loads(b"{}") == {"b": 2}

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

rag: Any
try:
    from leropa.llm import rag_legal_qdrant as rag
except ModuleNotFoundError:
    rag = None

pytestmark = pytest.mark.skipif(
    rag is None, reason="rag_legal_qdrant deps missing"
)


def test_split_into_token_chunks_word_fallback() -> None:
    """Split text using word-based fallback when no tokenizer is available."""

    text = "one two three four"
    with patch.object(rag, "_ENC", None):
        parts = rag._split_into_token_chunks(
            text, chunk_tokens=3, overlap_tokens=1
        )
    assert parts == ["one two three", "three four"]


def test_read_json_file_handles_json_and_jsonl(tmp_path: Path) -> None:
    """Read objects from JSON and JSONL files."""

    json_file = tmp_path / "a.json"
    json_file.write_text(
        json.dumps([{"full_text": "a", "article_id": 1, "label": "A"}])
    )
    jsonl_file = tmp_path / "b.jsonl"
    jsonl_file.write_text(
        "\n".join(
            [
                json.dumps({"full_text": "b", "article_id": 2, "label": "B"}),
                json.dumps({"full_text": "c", "article_id": 3, "label": "C"}),
            ]
        )
    )
    objs_json = rag._read_json_file(str(json_file))
    objs_jsonl = rag._read_json_file(str(jsonl_file))
    assert objs_json[0]["article_id"] == 1
    assert len(objs_jsonl) == 2
    assert objs_jsonl[1]["label"] == "C"


def test_iter_json_objects_yields_articles(tmp_path: Path) -> None:
    """Iterate over JSON objects in a directory tree."""

    (tmp_path / "a.json").write_text(
        json.dumps({"full_text": "x", "article_id": 1, "label": "A"})
    )
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.jsonl").write_text(
        json.dumps({"full_text": "y", "article_id": 2, "label": "B"})
        + "\n"
        + json.dumps({"full_text": "z", "article_id": 3, "label": "C"})
    )
    items = list(rag._iter_json_objects(str(tmp_path)))
    texts = sorted(obj["full_text"] for _, obj in items)
    assert texts == ["x", "y", "z"]


def test_validate_article_normalizes_fields() -> None:
    """Return normalized article or None when invalid."""

    valid = {"full_text": "t", "article_id": 1, "label": 2}
    result = rag._validate_article(valid, "src")
    assert result == {"full_text": "t", "article_id": "1", "label": "2"}
    invalid = {"full_text": "", "article_id": 1, "label": "L"}
    assert rag._validate_article(invalid, "src") is None

import json
from pathlib import Path
from unittest.mock import patch

from leropa.llm import export_legal_articles_to_md as exporter


def test_token_chunks_word_fallback() -> None:
    """Chunk text using word-based logic when tiktoken is unavailable."""

    text = "one two three four five"
    with patch.object(exporter, "_ENC", None):
        chunks = exporter.token_chunks(text, max_tokens=2, overlap_tokens=0)
    assert chunks == ["one two", "three four", "five"]


def test_export_folder_writes_chunked_files(tmp_path: Path) -> None:
    """Write chunked Markdown files with YAML front matter."""

    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    sample = {
        "full_text": "one two three four five",
        "article_id": "a1",
        "label": "L1",
    }
    (input_dir / "sample.json").write_text(json.dumps(sample))

    with patch.object(exporter, "_ENC", None):
        arts, files = exporter.export_folder(
            str(input_dir),
            str(output_dir),
            max_tokens=2,
            overlap_tokens=0,
        )

    assert arts == 1
    assert files == 3
    md_files = sorted(output_dir.glob("*.md"))
    assert len(md_files) == 3
    content = md_files[0].read_text()
    assert content.startswith("---\n")
    assert "Article L1 (ID:" in content
    assert "## TEXT" in content
    assert "one two" in content

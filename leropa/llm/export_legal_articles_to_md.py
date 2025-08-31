"""Utilities to export legal articles to Markdown files."""

import datetime
import glob
import hashlib
import os
import re
import uuid
from typing import List, Tuple

import yaml

from leropa.json_utils import json_loads
from leropa.parser.document_info import DocumentInfo
from leropa.parser.full import FullDocumentVersion

# Optional token-aware chunking.
try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover
    _ENC = None  # type: ignore[assignment]


# ---------- Helpers ----------


def now_iso() -> str:
    """Return current UTC timestamp."""

    # Build an ISO-formatted UTC timestamp without microseconds.
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def slug(s: str, lim: int = 80) -> str:
    """Return a slugified version of the string.

    Args:
        s: Input string to slugify.
        lim: Maximum length of the slug.

    Returns:
        Slugified string.
    """

    # Replace non alphanumeric characters with underscores.
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(s))
    return s[:lim] or str(uuid.uuid4())


def sha1_text(text: str) -> str:
    """Return the SHA1 hash for the text.

    Args:
        text: Input text.

    Returns:
        Hexadecimal SHA1 digest.
    """

    # Encode text to bytes then compute hash.
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


def read_any_file(path: str) -> "FullDocumentVersion":
    """Read a JSON or JSONL file and return a list of records.

    Args:
        path: Path to the JSON or JSONL file.

    Returns:
        List of record dictionaries.
    """

    # Handle newline-delimited JSON by loading line by line.
    if path.lower().endswith(".jsonl"):
        articles = []
        with open(path, "rb") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    obj = json_loads(ln)
                    assert isinstance(obj, dict)
                    articles.append(obj)

        return FullDocumentVersion(
            articles=articles,
            document=DocumentInfo(
                title="",
                description="",
                source=path,
                ver_id=os.path.basename(path).replace(".jsonl", ""),
            ),
        )

    if path.lower().endswith(".yaml"):
        with open(path, "rb") as f:
            data = yaml.safe_load(f)
    else:
        with open(path, "rb") as f:
            data = json_loads(f.read())

    if not isinstance(data, dict):
        raise ValueError(
            f"Unsupported JSON/YAML structure in {path}; top level object is"
            f" {type(data)} (expected dict)"
        )

    return FullDocumentVersion.from_raw_data(data)


def token_len(text: str) -> int:
    """Return the token count for the text.

    Args:
        text: Text to count tokens for.

    Returns:
        Estimated token count.
    """

    if _ENC is None:
        # Quick heuristic: words as tokens.
        return max(1, len(text.split()))

    return len(_ENC.encode(text))


def token_chunks(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    """Split text into chunks.

    Args:
        text: The text to chunk.
        max_tokens: Maximum tokens per chunk.
        overlap_tokens: Tokens to overlap between chunks.

    Returns:
        A list of text chunks.
    """
    if max_tokens <= 0:
        return [text]

    step = max(1, max_tokens - overlap_tokens)

    if _ENC is None:
        # Fall back to splitting by words when tokenizer is unavailable.
        words = text.split()
        chunks: List[str] = []

        for start in range(0, len(words), step):
            end = min(len(words), start + max_tokens)
            if start >= end:
                break
            chunks.append(" ".join(words[start:end]))

        return chunks

    toks = _ENC.encode(text)
    chunks: List[str] = []

    for start in range(0, len(toks), step):
        end = min(len(toks), start + max_tokens)
        if start >= end:
            break
        chunks.append(_ENC.decode(toks[start:end]))

    return chunks


def ensure_dir(p: str) -> None:
    """Create directory if it does not exist.

    Args:
        p: Path to the directory.
    """

    os.makedirs(p, exist_ok=True)


# ---------- Export ----------


def export_folder(
    input_dir: str,
    output_dir: str,
    max_tokens: int = 1000,
    overlap_tokens: int = 200,
    title_template: str = "",
    body_heading: str = "TEXT",
    ext: str = ".md",
) -> Tuple[int, int]:
    """Export all JSON articles inside a folder.

    Args:
        input_dir: Directory containing JSON or JSONL files.
        output_dir: Destination directory for exported files.
        max_tokens: Maximum tokens per chunk.
        overlap_tokens: Token overlap between chunks.
        title_template: Template for document titles.
        body_heading: Heading shown before article text.
        ext: Output file extension.

    Returns:
        Tuple of number of articles processed and files written.
    """

    ensure_dir(output_dir)

    files = (
        glob.glob(os.path.join(input_dir, "**", "*.json"), recursive=True)
        + glob.glob(os.path.join(input_dir, "**", "*.jsonl"), recursive=True)
        + glob.glob(os.path.join(input_dir, "**", "*.yaml"), recursive=True)
    )

    num_articles = 0
    num_files = 0

    for f in files:
        try:
            doc = read_any_file(f)
            doc_title = doc.document.title or str(id(doc))
            for article in doc.articles:
                title = title_template.format(
                    label=article.label,
                    article_id=article.article_id,
                    document=doc.document.title or "",
                )

                text = article.full_text
                parts = token_chunks(
                    text, max_tokens=max_tokens, overlap_tokens=overlap_tokens
                )

                total = len(parts)
                num_articles += 1

                base = "__".join(
                    slug(a)
                    for a in (doc_title, article.label, article.article_id)
                )
                for idx, chunk in enumerate(parts):
                    chunk_idx = idx

                    meta = {
                        "title": title,
                        "article_id": article.article_id,
                        "label": article.label,
                        "source_file": os.path.basename(f),
                        "source_url": doc.document.source,
                        "chunk_index": chunk_idx,
                        "total_chunks": total,
                        "tokens": token_len(chunk),
                        "hash": sha1_text(chunk),
                        "created_at": now_iso(),
                        "exporter": "leropa.llm.export_legal_articles_to_md",
                        "exporter_version": "1.0",
                    }

                    # YAML front-matter.
                    yaml_data = yaml.safe_dump(
                        meta,
                        sort_keys=False,
                        allow_unicode=True,
                        default_flow_style=False,
                    )
                    yaml_front_matter = f"---\n{yaml_data}---\n"

                    # Body as Markdown with a clear heading.
                    body = f"# {title}\n\n## {body_heading}\n\n{chunk}\n"

                    content = yaml_front_matter + "\n" + body

                    fname = f"{base}__chunk{chunk_idx:03d}{ext}"
                    out_p = os.path.join(output_dir, fname)

                    with open(out_p, "w", encoding="utf-8") as w:
                        w.write(content)

                    num_files += 1
        except Exception as e:  # pragma: no cover - best effort.
            print(f"[warn] {f}: {e}")

    return num_articles, num_files

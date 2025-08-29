"""Utilities to export legal articles to Markdown files."""

import argparse
import datetime
import glob
import hashlib
import os
import re
import uuid
from typing import Any, Dict, List, Tuple

import yaml

from leropa.json_utils import json_loads

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


def read_any_json(path: str) -> List[Dict[str, Any]]:
    """Read a JSON or JSONL file and return a list of records.

    Args:
        path: Path to the JSON or JSONL file.

    Returns:
        List of record dictionaries.
    """

    out: List[Dict[str, Any]] = []

    # Handle newline-delimited JSON by loading line by line.
    if path.lower().endswith(".jsonl"):
        with open(path, "rb") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    obj = json_loads(ln)
                    assert isinstance(obj, dict)
                    out.append(obj)
        return out

    with open(path, "rb") as f:
        data = json_loads(f.read())

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]

    raise ValueError(f"Unsupported JSON structure in {path}")


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


def normalize_record(rec: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    """Validate and normalize a record.

    Args:
        rec: Raw record mapping.
        source_file: Name of the source file for attribution.

    Returns:
        Normalized record mapping.
    """

    missing = [k for k in ("full_text", "article_id", "label") if k not in rec]
    if missing:
        raise ValueError(f"Missing keys {missing}")

    text = (rec.get("full_text") or "").strip()
    if not text:
        raise ValueError("Empty full_text")

    return {
        "full_text": text,
        "article_id": str(rec.get("article_id")),
        "label": str(rec.get("label")),
        "source_file": source_file,
    }


# ---------- Export ----------


def export_folder(
    input_dir: str,
    output_dir: str,
    max_tokens: int = 1000,
    overlap_tokens: int = 200,
    title_template: str = "Article {label} (ID: {article_id})",
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

    files = glob.glob(
        os.path.join(input_dir, "**", "*.json"), recursive=True
    ) + glob.glob(os.path.join(input_dir, "**", "*.jsonl"), recursive=True)

    num_articles = 0
    num_files = 0

    for f in files:
        try:
            for raw in read_any_json(f):
                try:
                    rec = normalize_record(raw, os.path.basename(f))
                except Exception as e:
                    print(f"[skip] {f}: {e}")
                    continue

                text = rec["full_text"]
                article_id = rec["article_id"]
                label = rec["label"]
                title = title_template.format(
                    label=label, article_id=article_id
                )

                parts = token_chunks(
                    text, max_tokens=max_tokens, overlap_tokens=overlap_tokens
                )

                total = len(parts)
                num_articles += 1

                base = f"{slug(label)}__{slug(article_id)}"
                for idx, chunk in enumerate(parts):
                    chunk_idx = idx

                    meta = {
                        "title": title,
                        "article_id": article_id,
                        "label": label,
                        "source_file": rec["source_file"],
                        "chunk_index": chunk_idx,
                        "total_chunks": total,
                        "tokens": token_len(chunk),
                        "hash": sha1_text(chunk),
                        "created_at": now_iso(),
                        "exporter": "export_legal_articles_to_md.py",
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
                    body = (
                        f"# {title}\n"
                        "\n"
                        f"**Source:** {rec['source_file']}\n"
                        "\n"
                        f"## {body_heading}\n"
                        "\n"
                        f"{chunk}\n"
                    )

                    content = yaml_front_matter + "\n" + body

                    fname = f"{base}__chunk{chunk_idx:03d}{ext}"
                    out_p = os.path.join(output_dir, fname)

                    with open(out_p, "w", encoding="utf-8") as w:
                        w.write(content)

                    num_files += 1
        except Exception as e:  # pragma: no cover - best effort.
            print(f"[warn] {f}: {e}")

    return num_articles, num_files


# ---------- CLI ----------


def main() -> None:
    """CLI entry point."""

    ap = argparse.ArgumentParser(
        description=(
            "Export legal JSON articles to chunked Markdown with YAML "
            "front-matter."
        )
    )
    ap.add_argument("input_dir", help="Folder with .json/.jsonl files")
    ap.add_argument("output_dir", help="Folder to write .md files into")
    ap.add_argument(
        "--max-tokens",
        type=int,
        default=1000,
        help="Tokens per chunk (0 = no chunking)",
    )
    ap.add_argument(
        "--overlap",
        type=int,
        default=200,
        help="Overlap tokens between chunks",
    )
    ap.add_argument(
        "--ext",
        default=".md",
        choices=[".md", ".txt"],
        help="Output file extension",
    )
    ap.add_argument(
        "--title-template",
        default="Article {label} (ID: {article_id})",
        help="Title format",
    )
    ap.add_argument(
        "--body-heading",
        default="TEXT",
        help="Body heading shown before the text",
    )
    args = ap.parse_args()

    print(f"[info] token-aware chunking: {'on' if _ENC else 'word-based'}")

    arts, files = export_folder(
        args.input_dir,
        args.output_dir,
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap,
        title_template=args.title_template,
        body_heading=args.body_heading,
        ext=args.ext,
    )

    print(
        f"[done] exported {arts} articles into {files} "
        f"files @ {args.output_dir}"
    )


if __name__ == "__main__":
    main()

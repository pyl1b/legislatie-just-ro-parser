"""All-in-one local RAG pipeline for legal JSON articles with Qdrant (Docker)
and Ollama.

Before you run this script
--------------------------

1) Run Qdrant in Docker (one-time)

docker run --name qdrant -p 6333:6333 \\
    -e QDRANT__LOG_LEVEL=DEBUG \\
    -e QDRANT__TELEMETRY_DISABLED=true \\
    -e QDRANT__CLUSTER__ENABLED=false \\
    -v qdrant_storage:/qdrant/storage qdrant/qdrant:latest \\

2) Install Python deps (in a venv recommended)

pip install qdrant-client requests tqdm tiktoken orjson
# optional re-ranker (CPU ok):
pip install sentence-transformers

3) Pull Ollama models

ollama pull nomic-embed-text
ollama pull llama3.1:8b   # or mistral:7b


JSON input format
-----------------

- Either a single JSON per file (object) or a list of such objects.
- Each object must include:
  {
    "full_text": "str",
    "article_id": "string-or-int",
    "label": "Article number or label"
  }

Usage (Python REPL or another script):
--------------------------------------
from rag_legal_qdrant import (
    start_qdrant_docker, recreate_collection, ingest_folder,
    search, ask_with_context, delete_by_article_id
)

# 1) Ensure Qdrant is running (manually via Docker CLI or programmatically):
# start_qdrant_docker()  # optional helper; requires Docker Desktop running

# 2) (Re)create collection
recreate_collection("legal_articles")

# 3) Ingest a folder of JSON files
ingest_folder(r"C:/path/to/json_folder", collection="legal_articles")

# 4) Search or Ask
hits = search(
    "What are the obligations for data controllers?",
    collection="legal_articles",
    top_k=10,
)
print(hits[0])

answer = ask_with_context(
    "Summarize remedies available under article 77.",
    collection="legal_articles",
)
print(answer["text"])

# 5) Maintenance
delete_by_article_id("article-77", collection="legal_articles")
"""

import logging
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests
import yaml  # type: ignore[import]
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)
from tqdm import tqdm  # type: ignore

from leropa.json_utils import json_loads

# Optional re-ranker (CPU ok). If unavailable, pipeline still works.
CrossEncoder: Any = None  # ensure bound for type checkers and runtime
try:
    from sentence_transformers import CrossEncoder  # type: ignore

    _HAS_RERANKER = True
except Exception:
    _HAS_RERANKER = False

logger = logging.getLogger(__name__)

# -----------------------------
# Defaults.
# -----------------------------
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_EMBED_URL = os.environ.get(
    "OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings"
)
OLLAMA_CHAT_URL = os.environ.get(
    "OLLAMA_CHAT_URL", "http://localhost:11434/api/chat"
)

EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")  # 768 dims
EMBED_DIMS = int(os.environ.get("EMBED_DIMS", "768"))
# GEN_MODEL = os.environ.get("GEN_MODEL", "llama3.1:8b")
GEN_MODEL = os.environ.get("GEN_MODEL", "llama3.2:3b")

# If articles are long, you may wish to sub-chunk. Set to 0 to disable.
MAX_TOKENS_PER_CHUNK = int(os.environ.get("MAX_TOKENS_PER_CHUNK", "1000"))
OVERLAP_TOKENS = int(os.environ.get("OVERLAP_TOKENS", "200"))

# Reranker model (if sentence-transformers installed)
RERANKER_MODEL = os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-base")
TOP_K_RETRIEVE = int(os.environ.get("TOP_K_RETRIEVE", "24"))
TOP_K_CONTEXT = int(os.environ.get("TOP_K_CONTEXT", "8"))

# Tokenizer for chunking
try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    # Chunking by tokens disabled if tiktoken not available
    _ENC = None  # type: ignore


# -----------------------------
# Helpers
# -----------------------------


def _split_into_token_chunks(
    text: str, chunk_tokens: int, overlap_tokens: int
) -> List[str]:
    """Split ``text`` into chunks of approximately ``chunk_tokens`` tokens.

    Args:
        text: Source text to split.
        chunk_tokens: Maximum tokens per chunk.
        overlap_tokens: Tokens overlapping between chunks.

    Returns:
        List of text chunks.
    """
    if chunk_tokens <= 0:
        return [text]
    if not _ENC:
        # Simple word-based fallback
        words = text.split()
        chunks, start = [], 0
        step = max(1, chunk_tokens - overlap_tokens)
        while start < len(words):
            end = min(len(words), start + chunk_tokens)
            chunks.append(" ".join(words[start:end]))
            start += step
        return chunks

    # Token-accurate chunking
    tokens = _ENC.encode(text)
    chunks = []
    step = max(1, chunk_tokens - overlap_tokens)
    for start in range(0, len(tokens), step):
        end = min(len(tokens), start + chunk_tokens)
        if start >= end:
            break
        chunk = _ENC.decode(tokens[start:end])
        chunks.append(chunk)
    return chunks


def _is_jsonl(path: str) -> bool:
    """Return ``True`` if ``path`` points to a JSON Lines file."""
    # treat .jsonl as JSON lines; .json can be array or single object
    return path.lower().endswith(".jsonl")


def _extract_articles(data: object) -> List[Dict[str, Any]]:
    """Extract article dictionaries from loaded content.

    Args:
        data: Parsed file content.

    Returns:
        List of article objects.
    """

    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]

    if isinstance(data, dict):
        arts = data.get("articles")
        if isinstance(arts, list):
            return [a for a in arts if isinstance(a, dict)]
        return [data]

    raise ValueError("Unsupported document structure")


def _read_json_file(path: str) -> List[Dict[str, Any]]:
    """Load a JSON/JSONL file into a list of article objects.

    Args:
        path: Path to the JSON or JSONL file.

    Returns:
        List of article objects.
    """

    if _is_jsonl(path):
        out = []
        with open(path, "rb") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json_loads(line)
                out.append(obj)
        return out

    with open(path, "rb") as f:
        data = json_loads(f.read())

    return _extract_articles(data)


def _read_yaml_file(path: str) -> List[Dict[str, Any]]:
    """Load a YAML file into a list of article objects.

    Args:
        path: Path to the YAML file.

    Returns:
        List of article objects.
    """

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return _extract_articles(data)


def _iter_json_objects(
    root: str | Path,
) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """Yield (source_file, article) pairs from ``root`` directory.

    Handles JSON, JSONL or YAML files containing article records or parser
    outputs with an ``articles`` field.

    Args:
        root: Root directory to traverse for data files.

    Yields:
        Tuples of source file path and article object.
    """

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lower = fn.lower()
            path = os.path.join(dirpath, fn)
            try:
                if lower.endswith((".json", ".jsonl")):
                    objs = _read_json_file(path)
                elif lower.endswith((".yaml", ".yml")):
                    objs = _read_yaml_file(path)
                else:
                    continue
                for obj in objs:
                    yield path, obj
            except Exception as e:
                logger.exception(f"Skipping {path}: {e}")


def _validate_article(
    obj: Dict[str, Any], source: str
) -> Optional[Dict[str, Any]]:
    """Validate and normalize an article object.

    Args:
        obj: Raw article data.
        source: Path of the source file for logging.

    Returns:
        Normalized article mapping or ``None`` if validation fails.
    """
    missing = [k for k in ("full_text", "article_id", "label") if k not in obj]
    if missing:
        logger.warning(f"{source}: missing keys {missing}; skipping.")
        return None
    text = (obj.get("full_text") or "").strip()
    if not text:
        logger.warning(f"{source}: empty full_text; skipping.")
        return None

    # Normalize:
    return {
        "full_text": text,
        "article_id": str(obj.get("article_id")),
        "label": str(obj.get("label")),
    }


def _ollama_embed(text: str) -> List[float]:
    """Return embedding vector for ``text`` using Ollama."""
    r = requests.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    return data["embedding"]


def _ollama_chat(system: str, user: str, stream: bool = False) -> str:
    """Send a chat prompt to Ollama and return the response text.

    Args:
        system: System prompt.
        user: User prompt.
        stream: Whether to stream the response.

    Returns:
        Generated text reply.
    """
    payload = {
        "model": GEN_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": stream,
    }
    r = requests.post(
        OLLAMA_CHAT_URL, json=payload, stream=stream, timeout=None
    )
    r.raise_for_status()

    if not stream:
        data = r.json()
        return data.get("message", {}).get("content", "")

    # stream=True: concatenate chunks
    out = []
    for line in r.iter_lines():
        if not line:
            continue
        try:
            # Ollama streams json lines like:
            #     {"message":{"content":"..."}, "done":false}
            j = json_loads(line.decode("utf-8"))
            assert isinstance(j, dict), f"Expected dict, got {type(j)}"
            msg = j.get("message", {}).get("content")
            if msg:
                out.append(msg)
        except Exception:
            continue
    return "".join(out)


# -----------------------------
# Public API
# -----------------------------
def start_qdrant_docker(
    name: str = "qdrant",
    port: int = 6333,
    volume: str = "qdrant_storage",
    image: str = "qdrant/qdrant:latest",
) -> bool:
    """Start a Qdrant Docker container if not already running.

    Args:
        name: Name of the Docker container.
        port: Host port to expose Qdrant on.
        volume: Docker volume for persistent storage.
        image: Docker image to run.
    """
    try:
        # Try to start if already created
        subprocess.run(["docker", "start", name], check=False)
        # If not existing, run new container
        subprocess.run(
            [
                "docker",
                "run",
                "--name",
                name,
                "-p",
                f"{port}:6333",
                "-v",
                f"{volume}:/qdrant/storage",
                "-d",
                image,
            ],
            check=False,
        )
        return True
    except Exception:
        logger.exception("Failed to start Qdrant via Docker automatically")
        return False


def recreate_collection(
    collection: str,
    vector_size: int = EMBED_DIMS,
    distance: Distance = Distance.COSINE,
) -> None:
    """Create or recreate a Qdrant collection.

    Args:
        collection: Name of the collection.
        vector_size: Size of the embedding vectors.
        distance: Similarity metric used for vectors.
    """
    client = QdrantClient(url=QDRANT_URL)
    client.recreate_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=vector_size, distance=distance),
    )


def ingest_folder(
    root: str | Path,
    collection: str,
    batch_size: int = 32,
    chunk_tokens: int = MAX_TOKENS_PER_CHUNK,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> int:
    """Ingest articles from ``root`` into Qdrant.

    Accepts JSON, JSONL or YAML files containing either individual article
    objects or parser dumps with an ``articles`` list. Splits very long
    articles into token chunks when ``chunk_tokens`` is greater than zero.

    Args:
        root: The root folder to ingest.
        collection: The name of the Qdrant collection.
        batch_size: The number of points to upsert at once.
        chunk_tokens: The maximum number of tokens per chunk.
        overlap_tokens: The number of tokens to overlap between chunks.
    """
    client = QdrantClient(url=QDRANT_URL)

    def _upsert(points: List[PointStruct]) -> None:
        client.upsert(collection_name=collection, points=points)

    buf_points: List[PointStruct] = []

    total = 0
    # tqdm shows a progress bar.
    for source, obj in tqdm(
        list(_iter_json_objects(root)), desc="Scanning", ncols=80
    ):
        rec = _validate_article(obj, source)
        if not rec:
            continue

        text = rec["full_text"]
        chunks = _split_into_token_chunks(text, chunk_tokens, overlap_tokens)

        for idx, chunk in enumerate(chunks):
            vec = _ollama_embed(chunk)
            p = PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "article_id": rec["article_id"],
                    "label": rec["label"],
                    "source_file": source,
                    "chunk_index": idx,
                    "text": chunk,
                },
            )
            buf_points.append(p)
            if len(buf_points) >= batch_size:
                _upsert(buf_points)
                total += len(buf_points)
                buf_points.clear()

    if buf_points:
        client.upsert(collection_name=collection, points=buf_points)
        total += len(buf_points)

    return total


def search(
    query: str,
    collection: str,
    top_k: int = TOP_K_RETRIEVE,
    filter_by_label: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Vector search for relevant chunks. Optional filter by article label.

    Args:
        query: The search query.
        collection: The name of the Qdrant collection.
        top_k: The number of chunks to retrieve.
        filter_by_label: Optional filter by article label.

    Returns:
        list of dicts: {"text", "article_id", "label", "source_file", "score"}
    """
    client = QdrantClient(url=QDRANT_URL)
    q_vec = _ollama_embed(query)

    q_filter = None
    if filter_by_label:
        q_filter = Filter(
            must=[
                FieldCondition(
                    key="label", match=MatchValue(value=str(filter_by_label))
                )
            ]
        )

    hits = client.search(
        collection_name=collection,
        query_vector=q_vec,
        limit=top_k,
        with_payload=True,
        query_filter=q_filter,
    )

    results = []
    for h in hits:
        payload = h.payload or {}
        results.append(
            {
                "text": payload.get("text", ""),
                "article_id": payload.get("article_id"),
                "label": payload.get("label"),
                "source_file": payload.get("source_file"),
                "score": h.score,
            }
        )
    return results


def ask_with_context(
    question: str,
    collection: str,
    top_k: int = TOP_K_RETRIEVE,
    final_k: int = TOP_K_CONTEXT,
    use_reranker: bool = True,
) -> Dict[str, Any]:
    """Retrieve → (optional rerank) → generate answer with citations.

    Args:
        question: The question to answer.
        collection: The name of the Qdrant collection.
        top_k: The number of chunks to retrieve.
        final_k: The number of chunks to use for the final answer.
        use_reranker: Whether to use the reranker.

    Returns:
        {"text": answer, "contexts": [...]}
        with contexts including [n] indices.
    """
    # 1) Retrieve
    items = search(question, collection=collection, top_k=top_k)

    # 2) Optional rerank to choose best 'final_k'
    if use_reranker and _HAS_RERANKER and len(items) > final_k:
        assert CrossEncoder is not None
        reranker = CrossEncoder(RERANKER_MODEL, device="cpu")
        pairs = [(question, it["text"]) for it in items]
        scores = reranker.predict(pairs).tolist()
        for it, s in zip(items, scores):
            it["rerank"] = float(s)
        items.sort(key=lambda x: x["rerank"], reverse=True)
    contexts = items[:final_k]

    # 3) Build context blocks and prompt
    ctx_blocks = []
    for i, c in enumerate(contexts, start=1):
        src = (
            f"{c.get('source_file', '')}#article_id={c.get('article_id')}"
            f"&label={c.get('label')}"
        )
        ctx_blocks.append(f"[{i}] Source: {src}\n{c['text']}")
    context = "\n\n".join(ctx_blocks)

    system = (
        "You are a precise legal research assistant. "
        "Use ONLY the supplied CONTEXT to answer the user's question. "
        "Cite sources using bracketed numbers like [1], [2] "
        "that correspond to the context blocks. "
        "If the answer is not in the context, say you don't know."
    )
    user = (
        f"QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\n"
        "Answer with citations like [1], [2]."
    )

    answer_text = _ollama_chat(system, user, stream=False)

    return {"text": answer_text, "contexts": contexts}


def delete_by_article_id(article_id: str, collection: str) -> int:
    """Delete all vectors for a given article_id.

    Args:
        article_id: The article_id to delete.
        collection: The name of the Qdrant collection.

    Returns:
        The number of vectors deleted (best-effort).
    """
    client = QdrantClient(url=QDRANT_URL)
    # Select points by payload filter
    f = Filter(
        must=[
            FieldCondition(
                key="article_id", match=MatchValue(value=str(article_id))
            )
        ]
    )
    res = client.scroll(
        collection_name=collection,
        with_payload=False,
        limit=10000,
        scroll_filter=f,
    )
    total_deleted = 0
    while True:
        points, next_page = res
        if not points:
            break
        ids = [p.id for p in points]
        if ids:
            client.delete(
                collection_name=collection,
                points_selector=PointIdsList(points=ids),
            )
            total_deleted += len(ids)
        if not next_page:
            break
        res = client.scroll(
            collection_name=collection,
            with_payload=False,
            limit=10000,
            scroll_filter=f,
            offset=next_page,
        )
    return total_deleted

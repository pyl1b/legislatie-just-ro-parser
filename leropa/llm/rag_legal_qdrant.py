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

import os

try:
    import orjson as json
except ImportError:
    import json  # type: ignore

import subprocess
import uuid
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests
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

# Optional re-ranker (CPU ok). If unavailable, pipeline still works.
CrossEncoder: Any = None  # ensure bound for type checkers and runtime
try:
    from sentence_transformers import CrossEncoder  # type: ignore

    _HAS_RERANKER = True
except Exception:
    _HAS_RERANKER = False

# -----------------------------
# Defaults (change if you like)
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
GEN_MODEL = os.environ.get("GEN_MODEL", "llama3.1:8b")

# If your articles are long, you may wish to sub-chunk. Set to 0 to disable.
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
def _token_len(text: str) -> int:
    """Return the number of tokens in ``text``.

    Args:
        text: Text to measure.

    Returns:
        Count of tokens according to the configured encoder.
    """
    if not _ENC:
        # fallback heuristic
        return max(1, len(text.split()))
    return len(_ENC.encode(text))


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
                obj = json.loads(line)
                out.append(obj)
        return out

    with open(path, "rb") as f:
        data = json.loads(f.read())

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        raise ValueError(f"Unsupported JSON structure in {path}")


def _iter_json_objects(
    root: str,
) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """Yield ``(source_file, article)`` pairs from ``root`` directory.

    Args:
        root: Root directory to traverse for JSON files.

    Yields:
        Tuples of source file path and article object.
    """
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith((".json", ".jsonl")):
                continue
            path = os.path.join(dirpath, fn)
            try:
                objs = _read_json_file(path)
                for obj in objs:
                    yield path, obj
            except Exception as e:
                print(f"[WARN] Skipping {path}: {e}")


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
        print(f"[WARN] {source}: missing keys {missing}; skipping.")
        return None
    text = (obj.get("full_text") or "").strip()
    if not text:
        print(f"[WARN] {source}: empty full_text; skipping.")
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
            j = json.loads(line.decode("utf-8"))
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
) -> None:
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
        print(f"[INFO] Qdrant requested on http://localhost:{port}")
    except Exception as e:
        print(f"[WARN] Could not start Qdrant via Docker automatically: {e}")
        print(
            "Run manually:\n  docker run --name qdrant -p 6333:6333 "
            "-v qdrant_storage:/qdrant/storage qdrant/qdrant:latest"
        )


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
    print(f"[INFO] Collection '{collection}' ready at {QDRANT_URL}.")


def ingest_folder(
    root: str,
    collection: str,
    batch_size: int = 32,
    chunk_tokens: int = MAX_TOKENS_PER_CHUNK,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> None:
    """Ingest all JSON/JSONL files in 'root' into Qdrant.

    Splits very long articles into token chunks (if chunk_tokens > 0).

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

    print(f"[INFO] Ingested {total} chunks into '{collection}'.")


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
    print(
        f"[INFO] Deleted ~{total_deleted} points for article_id={article_id}"
    )
    return total_deleted


# -----------------------------
# Optional: simple CLI helpers
# -----------------------------
def _cli() -> None:
    import argparse

    ap = argparse.ArgumentParser(
        description="Local RAG for legal JSON articles (Qdrant + Ollama)."
    )
    ap.add_argument("--collection", default="legal_articles")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("recreate", help="(Re)create Qdrant collection.")
    s1.add_argument("--dims", type=int, default=EMBED_DIMS)

    s2 = sub.add_parser("ingest", help="Ingest a folder of JSON/JSONL files.")
    s2.add_argument("folder")
    s2.add_argument("--batch", type=int, default=32)
    s2.add_argument("--chunk", type=int, default=MAX_TOKENS_PER_CHUNK)
    s2.add_argument("--overlap", type=int, default=OVERLAP_TOKENS)

    s3 = sub.add_parser("search", help="Semantic search.")
    s3.add_argument("query")
    s3.add_argument("--topk", type=int, default=TOP_K_RETRIEVE)
    s3.add_argument("--label", type=str, default=None)

    s4 = sub.add_parser("ask", help="Ask a question with citations.")
    s4.add_argument("question")
    s4.add_argument("--topk", type=int, default=TOP_K_RETRIEVE)
    s4.add_argument("--finalk", type=int, default=TOP_K_CONTEXT)
    s4.add_argument("--no-rerank", action="store_true")

    s5 = sub.add_parser("delete", help="Delete by article_id.")
    s5.add_argument("article_id")

    s6 = sub.add_parser(
        "start-qdrant", help="Attempt to start Qdrant via Docker."
    )
    s6.add_argument("--name", default="qdrant")
    s6.add_argument("--port", type=int, default=6333)
    s6.add_argument("--volume", default="qdrant_storage")
    s6.add_argument("--image", default="qdrant/qdrant:latest")

    args = ap.parse_args()
    if args.cmd == "recreate":
        recreate_collection(args.collection, vector_size=args.dims)
    elif args.cmd == "ingest":
        ingest_folder(
            args.folder,
            collection=args.collection,
            batch_size=args.batch,
            chunk_tokens=args.chunk,
            overlap_tokens=args.overlap,
        )
    elif args.cmd == "search":
        res = search(
            args.query,
            collection=args.collection,
            top_k=args.topk,
            filter_by_label=args.label,
        )
        for i, r in enumerate(res, 1):
            print(
                f"\n[{i}] score={r['score']:.4f} "
                f"label={r['label']} "
                f"article_id={r['article_id']}\n"
                f"{r['text'][:600]}..."
            )
    elif args.cmd == "ask":
        out = ask_with_context(
            args.question,
            collection=args.collection,
            top_k=args.topk,
            final_k=args.finalk,
            use_reranker=not args.no_rerank,
        )
        print("\n--- Answer ---\n")
        print(out["text"])
        print("\n--- Contexts ---")
        for i, c in enumerate(out["contexts"], 1):
            print(
                f"[{i}] label={c['label']} "
                f"article_id={c['article_id']} "
                f"src={c['source_file']}"
            )
    elif args.cmd == "delete":
        delete_by_article_id(args.article_id, collection=args.collection)
    elif args.cmd == "start-qdrant":
        start_qdrant_docker(
            name=args.name,
            port=args.port,
            volume=args.volume,
            image=args.image,
        )


if __name__ == "__main__":
    _cli()

"""FastAPI application exposing CLI commands."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import yaml  # type: ignore[import-untyped]
from fastapi import (  # type: ignore[import-not-found]
    BackgroundTasks,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Response,
)
from fastapi.responses import (  # type: ignore[import-not-found]
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)

from leropa import parser
from leropa.cli import _import_llm_module
from leropa.json_utils import json_loads
from leropa.llm import available_models
from leropa.xlsx import write_workbook

JSONDict = dict[str, Any]
DocumentSummary = dict[str, str | None]
DocumentSummaryList = list[DocumentSummary]

# Directory containing structured document files.
DOCUMENTS_DIR = Path(
    os.environ.get("LEROPA_DOCUMENTS", Path.home() / ".leropa" / "documents")
)


def _document_files() -> list[Path]:
    """Return available document files from ``DOCUMENTS_DIR``.

    Returns:
        Paths pointing to JSON or YAML files. Nonexistent directories
        yield an empty list.
    """

    # Return early when directory does not exist.
    if not DOCUMENTS_DIR.exists():
        return []

    # Collect files with supported extensions.
    files: list[Path] = []
    for pattern in ("*.json", "*.yaml", "*.yml"):
        files.extend(DOCUMENTS_DIR.glob(pattern))
    return files


def _load_document_file(path: Path) -> JSONDict:
    """Load a structured document from ``path``.

    Args:
        path: Location of the JSON or YAML file.

    Returns:
        Parsed document dictionary.
    """

    text = path.read_text(encoding="utf-8")

    # Decode according to file extension.
    if path.suffix == ".json":
        return json_loads(text)  # type: ignore[return-value]
    return yaml.safe_load(text)


def _strip_full_text(doc: JSONDict) -> JSONDict:
    """Remove ``full_text`` from articles to expose granular content.

    Args:
        doc: Document structure to mutate.

    Returns:
        The same document with article ``full_text`` fields removed.
    """

    for article in doc.get("articles", []):
        article.pop("full_text", None)
    return doc


def _render_document(doc: JSONDict) -> str:
    """Render a document structure into basic HTML.

    Args:
        doc: Parsed document data.

    Returns:
        HTML string representing the document.
    """

    parts = [f"<h1>{doc['document'].get('title', '')}</h1>"]

    # Render each article with its paragraphs and subparagraphs.
    for article in doc.get("articles", []):
        label = article.get("label", article.get("article_id", ""))
        parts.append(f"<h2>Art. {label}</h2>")

        for paragraph in article.get("paragraphs", []):
            par_label = paragraph.get("label", "")
            text = paragraph.get("text", "")
            parts.append(f"<p>{par_label} {text}</p>")

            # Include subparagraphs when present.
            for sub in paragraph.get("subparagraphs", []):
                sub_label = sub.get("label", "")
                sub_text = sub.get("text", "")
                parts.append(f"<p>{sub_label} {sub_text}</p>")

    return "".join(parts)


app = FastAPI()


@app.get("/models")
async def list_models() -> JSONResponse:
    """Return the list of available LLM models."""

    # Provide the model names as a simple JSON list.
    return JSONResponse(available_models())


@app.get("/")
async def chat_form() -> HTMLResponse:
    """Render a minimal chat form."""

    # Build options for all available models.
    model_opts = "".join(
        f"<option value='{name}'>{name}</option>"
        for name in available_models()
    )

    # Return a simple HTML form for submitting questions and selecting a model.
    return HTMLResponse(
        "<form method='post' action='/chat'>"
        f"<select name='model'>{model_opts}</select>"
        "<input name='question' type='text'/>"
        "<button type='submit'>Ask</button>"
        "</form>"
    )


@app.post("/chat")
async def chat(
    question: str = Form(...),
    model: str = Form("rag_legal_qdrant"),
) -> HTMLResponse:
    """Handle chat questions and display the answer."""

    # Import the requested RAG module and generate an answer.
    mod = _import_llm_module(model)
    answer = mod.ask_with_context(question, collection="legal_articles")

    # Build the model options for rendering the form again.
    model_opts = "".join(
        f"<option value='{name}'>{name}</option>"
        for name in available_models()
    )

    # Render the answer in a new HTML page along with the form.
    return HTMLResponse(
        f"<p>{answer['text']}</p>"
        "<form method='post' action='/chat'>"
        f"<select name='model'>{model_opts}</select>"
        "<input name='question' type='text'/>"
        "<button type='submit'>Ask</button>"
        "</form>"
    )


@app.get("/documents")
async def list_documents(
    format: str = Query(default="json", enum=["json", "html"]),
) -> Response:
    """List structured documents available on the server.

    Args:
        format: Desired response format.

    Returns:
        Either a JSON list or an HTML page with document links.
    """

    # Gather summaries for all known documents.
    summaries: DocumentSummaryList = []
    for path in _document_files():
        data = _load_document_file(path)
        info = data.get("document", {})
        summaries.append(
            {"ver_id": info.get("ver_id"), "title": info.get("title")}
        )

    # Render as HTML when requested.
    if format == "html":
        template = (
            "<li><a href='/documents/{ver}?format=html'>{title}</a></li>"
        )
        items = "".join(
            template.format(ver=s["ver_id"], title=s["title"])
            for s in summaries
        )
        return HTMLResponse(f"<ul>{items}</ul>")

    return JSONResponse(summaries)


@app.get("/documents/{ver_id}")
async def get_document(
    ver_id: str, format: str = Query(default="json", enum=["json", "html"])
) -> Response:
    """Return a specific document by version identifier.

    Args:
        ver_id: Document version identifier.
        format: Desired response format.

    Returns:
        Document structure without ``full_text`` fields or its HTML rendering.
    """

    # Locate the document file matching ``ver_id``.
    file_path = next((p for p in _document_files() if p.stem == ver_id), None)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = _strip_full_text(_load_document_file(file_path))

    # Render as HTML when requested.
    if format == "html":
        return HTMLResponse(_render_document(doc))

    return JSONResponse(doc)


@app.get("/convert")
async def convert_endpoint(
    ver_id: str,
    background_tasks: BackgroundTasks,
    cache_dir: str | None = Query(default=None),
    output_format: str = Query(default="json", enum=["json", "yaml", "xlsx"]),
) -> Response:
    """Convert a document identifier to structured data.

    Args:
        ver_id: Identifier for the document version to convert.
        cache_dir: Directory for the HTML cache.
        output_format: Desired output format.

    Returns:
        The structured document in the requested format.
    """

    # Convert cache path to ``Path`` if provided.
    cache_path = Path(cache_dir) if cache_dir else None

    # Retrieve and parse the document structure.
    doc = parser.fetch_document(ver_id, cache_path)

    # Return JSON when requested.
    if output_format == "json":
        return JSONResponse(doc)

    # Return YAML output.
    if output_format == "yaml":
        text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
        return PlainTextResponse(text, media_type="application/x-yaml")

    # Prepare XLSX output by writing to a temporary file.
    tmp = NamedTemporaryFile(suffix=".xlsx", delete=False)
    write_workbook(doc, Path(tmp.name))

    # Schedule file deletion after the response is sent.
    background_tasks.add_task(os.unlink, tmp.name)

    # Serve the file as a download.
    return FileResponse(tmp.name, filename=f"{ver_id}.xlsx")


@app.get("/export-md")
async def export_md_endpoint(
    input_dir: str,
    output_dir: str,
    max_tokens: int = 1000,
    overlap: int = 200,
    ext: str = ".md",
    title_template: str = "Article {label} (ID: {article_id})",
    body_heading: str = "TEXT",
    model: str = "export_legal_articles_to_md",
) -> JSONResponse:
    """Export legal JSON articles to chunked Markdown files.

    Args:
        input_dir: Folder containing JSON or JSONL files.
        output_dir: Destination folder for Markdown files.
        max_tokens: Tokens per chunk (0 disables chunking).
        overlap: Token overlap between chunks.
        ext: Output file extension.
        title_template: Title format used in the Markdown output.
        body_heading: Heading shown before the article text.

    Returns:
        Summary of the export operation.
    """

    # Import the requested exporter module.
    mod = _import_llm_module(model)

    # Execute the export and capture resulting counts.
    art_count, file_count = mod.export_folder(
        input_dir,
        output_dir,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        title_template=title_template,
        body_heading=body_heading,
        ext=ext,
    )

    # Report counts to the caller.
    return JSONResponse(
        {
            "articles": art_count,
            "files": file_count,
            "output_dir": output_dir,
        }
    )


@app.get("/rag/recreate")
async def rag_recreate(
    collection: str = "legal_articles",
    dims: int = 768,
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """(Re)create the configured Qdrant collection.

    Args:
        collection: Qdrant collection name.
        dims: Embedding vector size.

    Returns:
        Confirmation of the operation.
    """

    # Import the requested RAG module and trigger the collection creation.
    mod = _import_llm_module(model)
    mod.recreate_collection(collection, vector_size=dims)
    return JSONResponse({"status": "ready"})


@app.get("/rag/ingest")
async def rag_ingest(
    folder: str,
    collection: str = "legal_articles",
    batch: int = 32,
    chunk: int = 1000,
    overlap: int = 200,
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """Ingest a folder of JSON/JSONL files.

    Args:
        folder: Path to the directory containing the data files.
        collection: Qdrant collection name.
        batch: Batch size for uploads.
        chunk: Tokens per chunk.
        overlap: Token overlap between chunks.

    Returns:
        Number of ingested chunks.
    """

    # Import the requested RAG module and process the folder.
    mod = _import_llm_module(model)
    total_ingested = mod.ingest_folder(
        folder,
        collection=collection,
        batch_size=batch,
        chunk_tokens=chunk,
        overlap_tokens=overlap,
    )
    return JSONResponse({"chunks": total_ingested})


@app.get("/rag/search")
async def rag_search(
    query: str,
    collection: str = "legal_articles",
    topk: int = 24,
    label: str | None = None,
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """Perform a semantic search over ingested articles.

    Args:
        query: Query string for semantic search.
        collection: Qdrant collection name.
        topk: Number of results to retrieve.
        label: Filter by article label.

    Returns:
        Search results from the RAG module.
    """

    # Import the requested RAG module and perform the search.
    mod = _import_llm_module(model)
    hits = mod.search(query, collection=collection, top_k=topk, label=label)
    return JSONResponse(hits)


@app.get("/rag/ask")
async def rag_ask(
    question: str,
    collection: str = "legal_articles",
    topk: int = 24,
    finalk: int = 8,
    no_rerank: bool = False,
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """Ask a question and receive an answer with context.

    Args:
        question: The question to ask the model.
        collection: Qdrant collection name.
        topk: Number of documents to retrieve.
        finalk: Number of documents to include in the final context.
        no_rerank: Disable the re-ranker when True.

    Returns:
        Generated answer and its contexts.
    """

    # Import the requested RAG module and get the answer with context.
    mod = _import_llm_module(model)
    answer = mod.ask_with_context(
        question,
        collection=collection,
        top_k=topk,
        final_k=finalk,
        use_reranker=not no_rerank,
    )
    return JSONResponse(answer)


@app.delete("/rag/delete")
async def rag_delete(
    article_id: str,
    collection: str = "legal_articles",
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """Delete items from the collection by ``article_id``.

    Args:
        article_id: Identifier of the article to remove.
        collection: Qdrant collection name.

    Returns:
        Number of deleted points.
    """

    # Import the requested RAG module and perform the deletion.
    mod = _import_llm_module(model)
    total_deleted = mod.delete_by_article_id(article_id, collection=collection)
    return JSONResponse({"deleted": total_deleted})


@app.get("/rag/start-qdrant")
async def rag_start_qdrant(
    name: str = "qdrant",
    port: int = 6333,
    volume: str = "qdrant_storage",
    image: str = "qdrant/qdrant:latest",
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """Attempt to start Qdrant via Docker.

    Args:
        name: Docker container name.
        port: Qdrant port to expose.
        volume: Docker volume for persistent storage.
        image: Docker image to run.

    Returns:
        Whether the container was started successfully.
    """

    # Import the requested RAG module and start the Docker container.
    mod = _import_llm_module(model)
    result = mod.start_qdrant_docker(
        name=name, port=port, volume=volume, image=image
    )
    return JSONResponse({"started": bool(result)})

try:
    import orjson as json  # type: ignore[import-not-found]
except ImportError:
    import json

import importlib
import logging
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import ModuleType
from typing import Optional

import click
import yaml  # type: ignore
from dotenv import load_dotenv

from leropa import parser
from leropa.xlsx import write_workbook

try:
    __version__ = version("leropa")
except PackageNotFoundError:
    __version__ = "0.0.1-dev"


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.option("--trace/--no-trace", default=False)
@click.option(
    "--log-file",
    type=click.Path(file_okay=True, dir_okay=False),
    envvar="LEROPA_LOG_FILE",
)
@click.version_option(__version__, prog_name="leropa")
def cli(debug: bool, trace: bool, log_file: Optional[str] = None) -> None:
    """Configure logging and load environment variables.

    Args:
        debug: Toggle debug logging.
        trace: Toggle trace logging.
        log_file: Optional path to the log file.
    """
    if trace:
        level = 1
    elif debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        filename=log_file,
        level=level,
        format="[%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if trace:
        logging.debug("Trace mode is on")
    if debug:
        logging.debug("Debug mode is on")
    load_dotenv()


@cli.command()
@click.argument("ver_id")
@click.option(
    "--cache-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default=None,
    help="Directory for the HTML cache.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(file_okay=True, dir_okay=True),
    default=None,
    help="Write output to FILE or DIRECTORY instead of the console.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml", "xlsx"]),
    default="json",
    help="Output format.",
)
def convert(
    ver_id: str,
    cache_dir: Optional[str] = None,
    output_path: Optional[str] = None,
    output_format: str = "json",
) -> None:
    """Convert a document identifier to structured data.

    Args:
        ver_id: Identifier for the document version to convert.
        cache_dir: Directory used to cache downloaded HTML files.
        output_path: Optional file or directory path for the converted data.
            If a directory is provided, the file name is automatically
            generated from ``ver_id``.
        output_format: Format of the converted data.
    """

    cache_path = Path(cache_dir) if cache_dir else None

    # Retrieve and parse the document structure.
    doc = parser.fetch_document(ver_id, cache_path)

    # Determine the output file path if one was provided. When the user
    # passes a directory, generate the file name using the document
    # identifier and the chosen format extension.
    final_path: Optional[Path] = None
    if output_path:
        final_path = Path(output_path)

        # Mapping from format names to file extensions.
        extensions = {"json": ".json", "yaml": ".yaml", "xlsx": ".xlsx"}

        # If the provided path is a directory, build the file path inside it.
        if final_path.is_dir():
            final_path = final_path / f"{ver_id}{extensions[output_format]}"

    if output_format == "json":
        content = json.dumps(doc, ensure_ascii=False)
        if final_path:
            final_path.write_text(content, encoding="utf-8")
        else:
            click.echo(content)
    elif output_format == "yaml":
        content = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
        if final_path:
            final_path.write_text(content, encoding="utf-8")
        else:
            click.echo(content)
    elif output_format == "xlsx":
        if final_path is None:
            raise click.UsageError("Output file is required for xlsx format.")

        # Write the structured data to the workbook using the dedicated
        # helper function that organizes sheets and tables.
        write_workbook(doc, final_path)


def _import_llm_module(module: str) -> ModuleType:
    """Import a module from ``leropa.llm`` requiring optional dependencies.

    Args:
        module: The module name relative to ``leropa.llm``.

    Returns:
        The imported module.

    Throws:
        click.ClickException: If the module or its dependencies are missing.
    """

    try:
        # Attempt to import the requested module.
        return importlib.import_module(f"leropa.llm.{module}")
    except ModuleNotFoundError as exc:  # pragma: no cover - narrow except
        # Inform the user that LLM extras are required.
        click.echo(
            "This command requires optional LLM dependencies.\n"
            "Install them with `pip install -e .[llm]`."
        )

        # Offer to install the dependencies immediately.
        if click.confirm("Install them now?", default=False):
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".[llm]"],
                check=True,
            )
            return _import_llm_module(module)

        # Abort execution with a clear message.
        raise click.ClickException("Missing LLM dependencies") from exc


@cli.command("export-md")
@click.argument("input_dir")
@click.argument("output_dir")
@click.option(
    "--max-tokens",
    type=int,
    default=1000,
    show_default=True,
    help="Tokens per chunk (0 disables chunking).",
)
@click.option(
    "--overlap",
    type=int,
    default=200,
    show_default=True,
    help="Token overlap between chunks.",
)
@click.option(
    "--ext",
    type=click.Choice([".md", ".txt"]),
    default=".md",
    show_default=True,
    help="Output file extension.",
)
@click.option(
    "--title-template",
    default="Article {label} (ID: {article_id})",
    show_default=True,
    help="Title format used in the Markdown output.",
)
@click.option(
    "--body-heading",
    default="TEXT",
    show_default=True,
    help="Heading shown before the article text.",
)
def export_md(
    input_dir: str,
    output_dir: str,
    max_tokens: int = 1000,
    overlap: int = 200,
    ext: str = ".md",
    title_template: str = "Article {label} (ID: {article_id})",
    body_heading: str = "TEXT",
) -> None:
    """Export legal JSON articles to chunked Markdown files.

    Args:
        input_dir: Folder containing JSON or JSONL files.
        output_dir: Destination folder for Markdown files.
        max_tokens: Tokens per chunk; ``0`` disables chunking.
        overlap: Token overlap between chunks.
        ext: Output file extension.
        title_template: Template for the document title.
        body_heading: Heading displayed before the text body.
    """

    # Import the exporter module, aborting if dependencies are missing.
    mod = _import_llm_module("export_legal_articles_to_md")

    # Execute the export operation and report the results to the user.
    art_count, file_count = mod.export_folder(
        input_dir,
        output_dir,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        title_template=title_template,
        body_heading=body_heading,
        ext=ext,
    )
    click.echo(
        f"Exported {art_count} articles into {file_count} files @ {output_dir}"
    )


@cli.group()
@click.option(
    "--collection",
    default="legal_articles",
    show_default=True,
    help="Qdrant collection name.",
)
@click.pass_context
def rag(ctx: click.Context, collection: str) -> None:
    """Interact with the local Qdrant/Ollama RAG pipeline.

    Args:
        ctx: Click context object.
        collection: Name of the Qdrant collection to use.
    """

    # Store the collection name for the subcommands.
    ctx.ensure_object(dict)
    ctx.obj["collection"] = collection


@rag.command()
@click.option(
    "--dims",
    type=int,
    default=768,
    show_default=True,
    help="Embedding vector size.",
)
@click.pass_context
def recreate(ctx: click.Context, dims: int) -> None:
    """(Re)create the configured Qdrant collection."""

    # Import the RAG module and trigger the collection creation.
    mod = _import_llm_module("rag_legal_qdrant")
    mod.recreate_collection(ctx.obj["collection"], vector_size=dims)


@rag.command()
@click.argument("folder")
@click.option(
    "--batch",
    type=int,
    default=32,
    show_default=True,
    help="Batch size for uploads.",
)
@click.option(
    "--chunk",
    type=int,
    default=1000,
    show_default=True,
    help="Tokens per chunk.",
)
@click.option(
    "--overlap",
    type=int,
    default=200,
    show_default=True,
    help="Token overlap between chunks.",
)
@click.pass_context
def ingest(
    ctx: click.Context,
    folder: str,
    batch: int = 32,
    chunk: int = 1000,
    overlap: int = 200,
) -> None:
    """Ingest a folder of JSON/JSONL files."""

    # Import the RAG module and process the folder.
    mod = _import_llm_module("rag_legal_qdrant")
    mod.ingest_folder(
        folder,
        collection=ctx.obj["collection"],
        batch_size=batch,
        chunk_tokens=chunk,
        overlap_tokens=overlap,
    )


@rag.command()
@click.argument("query")
@click.option(
    "--topk",
    type=int,
    default=24,
    show_default=True,
    help="Number of results to retrieve.",
)
@click.option("--label", default=None, help="Filter by article label.")
@click.pass_context
def search(
    ctx: click.Context, query: str, topk: int = 24, label: str | None = None
) -> None:
    """Perform a semantic search over ingested articles."""

    # Import the RAG module and perform the search.
    mod = _import_llm_module("rag_legal_qdrant")
    hits = mod.search(
        query,
        collection=ctx.obj["collection"],
        top_k=topk,
        filter_by_label=label,
    )

    # Display the results to the user.
    for idx, hit in enumerate(hits, start=1):
        click.echo(
            f"\n[{idx}] score={hit['score']:.4f} label={hit['label']} "
            f"article_id={hit['article_id']}\n{hit['text'][:600]}..."
        )


@rag.command()
@click.argument("question")
@click.option(
    "--topk",
    type=int,
    default=24,
    show_default=True,
    help="Number of documents to retrieve.",
)
@click.option(
    "--finalk",
    type=int,
    default=8,
    show_default=True,
    help="Number of documents to include in the final context.",
)
@click.option("--no-rerank", is_flag=True, help="Disable the re-ranker.")
@click.pass_context
def ask(
    ctx: click.Context,
    question: str,
    topk: int = 24,
    finalk: int = 8,
    no_rerank: bool = False,
) -> None:
    """Ask a question and receive an answer with context."""

    # Import the RAG module and get the answer with context.
    mod = _import_llm_module("rag_legal_qdrant")
    answer = mod.ask_with_context(
        question,
        collection=ctx.obj["collection"],
        top_k=topk,
        final_k=finalk,
        use_reranker=not no_rerank,
    )

    # Present the answer and its contexts.
    click.echo("\n--- Answer ---\n")
    click.echo(answer["text"])
    click.echo("\n--- Contexts ---")
    for idx, c in enumerate(answer["contexts"], start=1):
        click.echo(
            f"[{idx}] label={c['label']} article_id={c['article_id']} "
            f"src={c['source_file']}"
        )


@rag.command()
@click.argument("article_id")
@click.pass_context
def delete(ctx: click.Context, article_id: str) -> None:
    """Delete items from the collection by ``article_id``."""

    # Import the RAG module and perform the deletion.
    mod = _import_llm_module("rag_legal_qdrant")
    mod.delete_by_article_id(article_id, collection=ctx.obj["collection"])


@rag.command("start-qdrant")
@click.option("--name", default="qdrant", show_default=True)
@click.option("--port", type=int, default=6333, show_default=True)
@click.option("--volume", default="qdrant_storage", show_default=True)
@click.option("--image", default="qdrant/qdrant:latest", show_default=True)
def start_qdrant(
    name: str = "qdrant",
    port: int = 6333,
    volume: str = "qdrant_storage",
    image: str = "qdrant/qdrant:latest",
) -> None:
    """Attempt to start Qdrant via Docker."""

    # Import the RAG module and start the Docker container.
    mod = _import_llm_module("rag_legal_qdrant")
    mod.start_qdrant_docker(name=name, port=port, volume=volume, image=image)

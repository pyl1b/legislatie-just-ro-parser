import json
import logging
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
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

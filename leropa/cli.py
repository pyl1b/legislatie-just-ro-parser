import json
import logging
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from leropa import parser

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
def convert(ver_id: str, cache_dir: Optional[str] = None) -> None:
    """Convert a document identifier to JSON.

    Args:
        ver_id: Identifier for the document version to convert.
        cache_dir: Directory used to cache downloaded HTML files.
    """

    cache_path = Path(cache_dir) if cache_dir else None

    # Retrieve and parse the document structure.
    doc = parser.fetch_document(ver_id, cache_path)

    # Output the structured representation as JSON.
    click.echo(json.dumps(doc, ensure_ascii=False))

import json
import logging
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Optional

import click
import yaml
from dotenv import load_dotenv
from openpyxl import Workbook

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
@click.option(
    "--output",
    "output_path",
    type=click.Path(file_okay=True, dir_okay=False),
    default=None,
    help="Write output to FILE instead of the console.",
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
        output_path: Optional file path for the converted data.
        output_format: Format of the converted data.
    """

    cache_path = Path(cache_dir) if cache_dir else None

    # Retrieve and parse the document structure.
    doc = parser.fetch_document(ver_id, cache_path)

    if output_format == "json":
        content = json.dumps(doc, ensure_ascii=False)
        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")
        else:
            click.echo(content)
    elif output_format == "yaml":
        content = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")
        else:
            click.echo(content)
    elif output_format == "xlsx":
        if output_path is None:
            raise click.UsageError("Output file is required for xlsx format.")

        workbook = Workbook()

        # Remove default sheet created by Workbook.
        default_sheet = workbook.active
        workbook.remove(default_sheet)

        for key, value in doc.items():
            sheet = workbook.create_sheet(title=key)

            if isinstance(value, list) and value:
                headers = list(value[0].keys())
                sheet.append(headers)

                for item in value:
                    row = []
                    for h in headers:
                        cell_value = item.get(h)
                        if isinstance(cell_value, (list, dict)):
                            cell_value = json.dumps(
                                cell_value, ensure_ascii=False
                            )
                        row.append(cell_value)
                    sheet.append(row)
            elif isinstance(value, dict):
                sheet.append(list(value.keys()))
                sheet.append([value.get(k) for k in value.keys()])
            else:
                sheet.append(["value"])
                sheet.append([value])

        workbook.save(output_path)

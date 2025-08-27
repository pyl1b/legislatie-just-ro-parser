import logging
from typing import Optional

import click
from dotenv import load_dotenv

from leropa.__version__ import __version__


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

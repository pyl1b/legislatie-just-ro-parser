"""Tests for the command line interface."""

from click.testing import CliRunner
from pytest_mock import MockerFixture

from leropa import cli


def test_convert_outputs_json(mocker: MockerFixture) -> None:
    """Ensure converting a document id outputs JSON."""

    sample = {"document": {"ver_id": "123"}, "articles": []}
    mocker.patch("leropa.parser.fetch_document", return_value=sample)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["convert", "123"])

    assert result.exit_code == 0
    assert '"ver_id": "123"' in result.output

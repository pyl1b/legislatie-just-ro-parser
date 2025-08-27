"""Tests for the command line interface."""

import json
from pathlib import Path

import yaml
from click.testing import CliRunner
from openpyxl import load_workbook
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


def test_convert_writes_json_to_file(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Ensure JSON output is written to a file."""

    sample = {"document": {"ver_id": "123"}, "articles": []}
    mocker.patch("leropa.parser.fetch_document", return_value=sample)

    out_file = tmp_path / "out.json"
    runner = CliRunner()
    result = runner.invoke(
        cli.cli, ["convert", "123", "--output", str(out_file)]
    )

    assert result.exit_code == 0
    assert json.loads(out_file.read_text()) == sample


def test_convert_outputs_yaml(mocker: MockerFixture) -> None:
    """Ensure YAML output is sent to the console."""

    sample = {"document": {"ver_id": "123"}, "articles": []}
    mocker.patch("leropa.parser.fetch_document", return_value=sample)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["convert", "123", "--format", "yaml"])

    assert result.exit_code == 0
    assert yaml.safe_load(result.output) == sample


def test_convert_writes_xlsx(mocker: MockerFixture, tmp_path: Path) -> None:
    """Ensure XLSX output writes each data type to its own sheet."""

    sample = {
        "document": {"ver_id": "123"},
        "articles": [
            {"article_id": "a1", "full_text": "abc", "paragraphs": []}
        ],
    }
    mocker.patch("leropa.parser.fetch_document", return_value=sample)

    out_file = tmp_path / "out.xlsx"
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        [
            "convert",
            "123",
            "--format",
            "xlsx",
            "--output",
            str(out_file),
        ],
    )

    assert result.exit_code == 0
    workbook = load_workbook(out_file)
    assert set(workbook.sheetnames) == {"document", "articles"}
    doc_sheet = workbook["document"]
    assert doc_sheet.cell(row=2, column=1).value == "123"

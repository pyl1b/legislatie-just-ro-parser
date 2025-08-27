"""Tests for the command line interface."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml  # type: ignore[import-untyped]
from click.testing import CliRunner
from openpyxl import load_workbook  # type: ignore[import-untyped]

from leropa import cli


def test_convert_outputs_json() -> None:
    """Ensure converting a document id outputs JSON."""

    sample = {"document": {"ver_id": "123"}, "articles": []}
    with patch("leropa.parser.fetch_document", return_value=sample):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["convert", "123"])

    assert result.exit_code == 0
    assert '"ver_id": "123"' in result.output


def test_convert_writes_json_to_file(tmp_path: Path) -> None:
    """Ensure JSON output is written to a file."""

    sample = {"document": {"ver_id": "123"}, "articles": []}
    out_file = tmp_path / "out.json"

    with patch("leropa.parser.fetch_document", return_value=sample):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli, ["convert", "123", "--output", str(out_file)]
        )

    assert result.exit_code == 0
    assert json.loads(out_file.read_text()) == sample


def test_convert_writes_json_to_directory(tmp_path: Path) -> None:
    """Ensure JSON output is written when a directory is provided."""

    sample = {"document": {"ver_id": "123"}, "articles": []}

    with patch("leropa.parser.fetch_document", return_value=sample):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli, ["convert", "123", "--output", str(tmp_path)]
        )

    out_file = tmp_path / "123.json"
    assert result.exit_code == 0
    assert json.loads(out_file.read_text()) == sample


def test_convert_outputs_yaml() -> None:
    """Ensure YAML output is sent to the console."""

    sample = {"document": {"ver_id": "123"}, "articles": []}
    with patch("leropa.parser.fetch_document", return_value=sample):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["convert", "123", "--format", "yaml"])

    assert result.exit_code == 0
    assert yaml.safe_load(result.output) == sample


def test_convert_writes_xlsx(tmp_path: Path) -> None:
    """Ensure XLSX output writes each data type to its own sheet."""

    sample = {
        "document": {"ver_id": "123"},
        "articles": [
            {"article_id": "a1", "full_text": "abc", "paragraphs": []}
        ],
    }
    out_file = tmp_path / "out.xlsx"

    with patch("leropa.parser.fetch_document", return_value=sample):
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


def test_convert_writes_xlsx_to_directory(tmp_path: Path) -> None:
    """Ensure XLSX output is written when a directory is provided."""

    sample = {
        "document": {"ver_id": "123"},
        "articles": [
            {"article_id": "a1", "full_text": "abc", "paragraphs": []}
        ],
    }

    with patch("leropa.parser.fetch_document", return_value=sample):
        runner = CliRunner()
        result = runner.invoke(
            cli.cli,
            [
                "convert",
                "123",
                "--format",
                "xlsx",
                "--output",
                str(tmp_path),
            ],
        )

    out_file = tmp_path / "123.xlsx"
    assert result.exit_code == 0
    workbook = load_workbook(out_file)
    assert set(workbook.sheetnames) == {"document", "articles"}


def test_convert_writes_xlsx_with_nested_values(tmp_path: Path) -> None:
    """Ensure XLSX output serializes nested data structures."""

    sample: dict[str, Any] = {
        "document": {
            "ver_id": "123",
            "versions": [{"ver_id": "2", "date": "2022-01-01"}],
        },
        "articles": [],
    }
    out_file = tmp_path / "out.xlsx"

    with patch("leropa.parser.fetch_document", return_value=sample):
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
    doc_sheet = workbook["document"]

    # The versions list is stored as a JSON string in the second column.
    versions_cell = str(doc_sheet.cell(row=2, column=2).value)
    assert json.loads(versions_cell) == sample["document"]["versions"]

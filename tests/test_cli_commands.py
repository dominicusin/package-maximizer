"""Targeted CLI branch coverage for mockable commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from package_maximizer.cli.main import (
    cli,
    from_file,
    export_command,
    config_command,
    init_config_command,
    tui_command,
)


class TestFromFileCommand:
    """from_file reads JSON and invokes the maximizer."""

    def test_from_file_json_output(self, tmp_path):
        pkg_file = tmp_path / "packages.json"
        pkg_file.write_text(
            json.dumps([
                {"name": "alpha", "version": "1.0", "conflicts": ["beta"]},
                {"name": "beta", "version": "2.0"},
            ]),
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(from_file, [str(pkg_file), "--output", "json"])
        assert result.exit_code == 0
        assert "alpha" in result.output


class TestExportCommand:
    """export_command writes JSON/CSV/GraphML or stdout."""

    def test_export_json_stdout(self):
        runner = CliRunner()
        result = runner.invoke(export_command, ["alpha", "--format", "json"])
        assert result.exit_code == 0
        assert "alpha" in result.output

    def test_export_csv_stdout(self):
        runner = CliRunner()
        result = runner.invoke(export_command, ["alpha", "--format", "csv"])
        assert result.exit_code == 0
        assert "name" in result.output.lower() or "alpha" in result.output

    def test_export_graphml_stdout(self):
        runner = CliRunner()
        result = runner.invoke(export_command, ["alpha", "--format", "graphml"])
        assert result.exit_code == 0
        assert "alpha" in result.output

    def test_export_with_output_file(self, tmp_path):
        out = tmp_path / "result.json"
        runner = CliRunner()
        result = runner.invoke(export_command, ["alpha", "--format", "json", "--output-file", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert "alpha" in out.read_text(encoding="utf-8")


class TestConfigCommand:
    """config_command renders text/json/yaml."""

    def test_config_text_output(self):
        runner = CliRunner()
        result = runner.invoke(config_command, [])
        assert result.exit_code == 0
        assert "Источник конфигурации" in result.output

    def test_config_json_output(self):
        runner = CliRunner()
        result = runner.invoke(config_command, ["--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)


class TestInitConfigCommand:
    """init-config creates a default config file."""

    def test_init_config_creates_file(self, tmp_path):
        target = tmp_path / "pm.json"
        runner = CliRunner()
        result = runner.invoke(init_config_command, ["--config", str(target)])
        assert result.exit_code == 0
        assert target.exists()
        assert target.suffix == ".json"

    def test_init_config_skip_existing(self, tmp_path):
        target = tmp_path / "pm.json"
        target.write_text("{}", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(init_config_command, ["--config", str(target)])
        assert result.exit_code == 1
        assert "уже существует" in result.output


class TestTuiCommand:
    """tui_command should fail cleanly when textual is unavailable."""

    def test_tui_missing_textual_exits(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "package_maximizer.tui.app", None)
        runner = CliRunner()
        result = runner.invoke(tui_command, [])
        assert result.exit_code != 0

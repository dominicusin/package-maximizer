"""Targeted CLI branch coverage for mockable commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from package_maximizer.cli.main import (
    cli,
    config_command,
    export_command,
    from_file,
    init_config_command,
    list_managers,
    list_solvers,
    maximize,
    tui_command,
    version,
)


class TestFromFileCommand:
    """from_file reads JSON and invokes the maximizer."""

    def test_from_file_json_output(self, tmp_path):
        pkg_file = tmp_path / "packages.json"
        pkg_file.write_text(
            json.dumps(
                [
                    {"name": "alpha", "version": "1.0", "conflicts": ["beta"]},
                    {"name": "beta", "version": "2.0"},
                ]
            ),
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
        result = runner.invoke(
            export_command, ["alpha", "--format", "json", "--output-file", str(out)]
        )
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


class TestListManagersCommand:
    """list_managers shows all 22 registered package managers."""

    def test_list_managers_text(self):
        runner = CliRunner()
        result = runner.invoke(list_managers, [])
        assert result.exit_code == 0
        assert "apt" in result.output
        assert "pacman" in result.output
        assert "brew" in result.output
        assert "pip" in result.output
        assert "conda" in result.output


class TestMaximizeCommand:
    """maximize covers solver + error branches."""

    def test_maximize_basic(self):
        runner = CliRunner()
        result = runner.invoke(
            maximize, ["alpha", "beta", "--solver", "greedy", "--output", "text"]
        )
        assert result.exit_code == 0
        assert "alpha" in result.output or "beta" in result.output

    def test_maximize_json(self):
        runner = CliRunner()
        result = runner.invoke(
            maximize, ["alpha", "beta", "--solver", "greedy", "--output", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "output" in data

    def test_maximize_unknown_manager(self):
        runner = CliRunner()
        result = runner.invoke(maximize, ["alpha", "--manager", "unknown_xyz"])
        assert result.exit_code != 0

    def test_maximize_unknown_solver(self):
        runner = CliRunner()
        result = runner.invoke(maximize, ["alpha", "--solver", "unknown_xyz"])
        assert result.exit_code != 0

    def test_maximize_with_conflicts(self):
        runner = CliRunner()
        result = runner.invoke(
            maximize, ["alpha", "beta", "--solver", "greedy", "-c", "alpha", "beta"]
        )
        assert result.exit_code == 0

    def test_maximize_with_weights(self):
        runner = CliRunner()
        result = runner.invoke(
            maximize,
            [
                "alpha",
                "beta",
                "--solver",
                "greedy",
                "-w",
                "alpha",
                "2.0",
                "-w",
                "beta",
                "1.0",
            ],
        )
        assert result.exit_code == 0


class TestListSolversCommand:
    """list_solvers shows all registered solvers."""

    def test_list_solvers(self):
        runner = CliRunner()
        result = runner.invoke(list_solvers, [])
        assert result.exit_code == 0
        assert "greedy" in result.output


class TestVersionCommand:
    """version prints the version string."""

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(version, [])
        assert result.exit_code == 0
        assert "version" in result.output.lower()

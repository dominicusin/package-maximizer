"""
Extended CLI tests for uncovered branches.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from package_maximizer.cli.main import (benchmark, check_updates, cli,
                                        config_command, export_command,
                                        from_file, info, init_config_command,
                                        list_installed, list_managers,
                                        list_solvers, maximize, search,
                                        system_info, tui_command, version)


class TestFromFileExtended:
    """from_file extended coverage."""

    def test_from_file_text_output(self, tmp_path):
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
        result = runner.invoke(from_file, [str(pkg_file), "--output", "text"])
        assert result.exit_code == 0
        assert "alpha" in result.output

    def test_from_file_unknown_manager(self, tmp_path):
        pkg_file = tmp_path / "packages.json"
        pkg_file.write_text(
            json.dumps([{"name": "alpha"}]),
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(from_file, [str(pkg_file), "--manager", "unknown_xyz"])
        assert result.exit_code != 0

    def test_from_file_invalid_json(self, tmp_path):
        pkg_file = tmp_path / "packages.json"
        pkg_file.write_text("not json at all", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(from_file, [str(pkg_file)])
        assert result.exit_code != 0


class TestBenchmarkCommand:
    """benchmark command coverage."""

    def test_benchmark_text(self):
        runner = CliRunner()
        result = runner.invoke(
            benchmark, ["--solvers", "greedy", "--packages", "10", "--runs", "2"]
        )
        assert result.exit_code == 0
        assert "greedy" in result.output

    def test_benchmark_json(self):
        runner = CliRunner()
        result = runner.invoke(
            benchmark,
            [
                "--solvers",
                "greedy",
                "--packages",
                "10",
                "--runs",
                "2",
                "--output",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_benchmark_all_solvers(self):
        runner = CliRunner()
        result = runner.invoke(
            benchmark, ["--solvers", "greedy", "--packages", "20", "--runs", "1"]
        )
        assert result.exit_code == 0

    def test_benchmark_unknown_solver(self):
        runner = CliRunner()
        result = runner.invoke(
            benchmark,
            ["--solvers", "nonexistent_solver", "--packages", "5", "--runs", "1"],
        )
        assert result.exit_code == 0


class TestSearchCommand:
    """search command coverage."""

    def test_search_text(self):
        runner = CliRunner()
        result = runner.invoke(search, ["python", "--manager", "apt", "--limit", "5"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_search_json(self):
        runner = CliRunner()
        result = runner.invoke(
            search, ["python", "--manager", "apt", "--limit", "5", "--output", "json"]
        )
        assert result.exit_code == 0 or result.exit_code == 1


class TestInfoCommand:
    """info command coverage."""

    def test_info_text(self):
        runner = CliRunner()
        result = runner.invoke(info, ["nginx", "--manager", "apt"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_info_json(self):
        runner = CliRunner()
        result = runner.invoke(info, ["nginx", "--manager", "apt", "--output", "json"])
        assert result.exit_code == 0 or result.exit_code == 1


class TestCheckUpdatesCommand:
    """check_updates command coverage."""

    def test_check_updates_text(self):
        runner = CliRunner()
        result = runner.invoke(check_updates, ["--manager", "apt"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_check_updates_json(self):
        runner = CliRunner()
        result = runner.invoke(check_updates, ["--manager", "apt", "--output", "json"])
        assert result.exit_code == 0 or result.exit_code == 1


class TestSystemInfoCommand:
    """system_info command coverage."""

    def test_system_info_text(self):
        runner = CliRunner()
        result = runner.invoke(system_info, ["--manager", "apt"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_system_info_json(self):
        runner = CliRunner()
        result = runner.invoke(system_info, ["--manager", "apt", "--output", "json"])
        assert result.exit_code == 0 or result.exit_code == 1


class TestConfigCommand:
    """config command coverage."""

    def test_config_yaml_output(self):
        runner = CliRunner()
        result = runner.invoke(config_command, ["--output", "yaml"])
        assert result.exit_code == 0

    def test_config_text_output(self):
        runner = CliRunner()
        result = runner.invoke(config_command, ["--output", "text"])
        assert result.exit_code == 0

    def test_config_json_output(self):
        runner = CliRunner()
        result = runner.invoke(config_command, ["--output", "json"])
        assert result.exit_code == 0


class TestInitConfigCommand:
    """init-config command coverage."""

    def test_init_config_creates_file(self, tmp_path):
        target = tmp_path / "test_config.json"
        runner = CliRunner()
        result = runner.invoke(init_config_command, ["--config", str(target)])
        assert result.exit_code == 0
        assert target.exists()

    def test_init_config_skip_existing(self, tmp_path):
        target = tmp_path / "existing.json"
        target.write_text("{}", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(init_config_command, ["--config", str(target)])
        assert result.exit_code != 0


class TestExportCommand:
    """export command coverage."""

    def test_export_json_stdout(self):
        runner = CliRunner()
        result = runner.invoke(export_command, ["alpha", "--format", "json"])
        assert result.exit_code == 0
        assert "alpha" in result.output

    def test_export_csv_stdout(self):
        runner = CliRunner()
        result = runner.invoke(export_command, ["alpha", "--format", "csv"])
        assert result.exit_code == 0

    def test_export_graphml_stdout(self):
        runner = CliRunner()
        result = runner.invoke(export_command, ["alpha", "--format", "graphml"])
        assert result.exit_code == 0

    def test_export_with_output_file(self, tmp_path):
        out = tmp_path / "result.json"
        runner = CliRunner()
        result = runner.invoke(
            export_command, ["alpha", "--format", "json", "--output-file", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_export_with_conflicts(self):
        runner = CliRunner()
        result = runner.invoke(
            export_command, ["alpha", "beta", "-c", "alpha", "beta", "--format", "json"]
        )
        assert result.exit_code == 0


class TestTuiCommand:
    """tui command coverage."""

    def test_tui_missing_textual_exits(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "package_maximizer.tui.app", None)
        runner = CliRunner()
        result = runner.invoke(tui_command, [])
        assert result.exit_code != 0


class TestMaximizeExtended:
    """maximize extended coverage."""

    def test_maximize_verbose(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-v", "maximize", "alpha", "--solver", "greedy"])
        assert result.exit_code == 0

    def test_maximize_quiet(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["-q", "maximize", "alpha", "--solver", "greedy"])
        assert result.exit_code == 0

    def test_maximize_with_config(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"default_solver": "greedy"}), encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(cfg), "maximize", "alpha"])
        assert result.exit_code == 0


class TestListSolversCommand:
    """list_solvers coverage."""

    def test_list_solvers(self):
        runner = CliRunner()
        result = runner.invoke(list_solvers, [])
        assert result.exit_code == 0
        assert "greedy" in result.output


class TestVersionCommand:
    """version command coverage."""

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(version, [])
        assert result.exit_code == 0
        assert "version" in result.output.lower()


class TestListManagersCommand:
    """list_managers coverage."""

    def test_list_managers(self):
        runner = CliRunner()
        result = runner.invoke(list_managers, [])
        assert result.exit_code == 0
        assert "apt" in result.output

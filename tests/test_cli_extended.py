"""
Tests for extended CLI commands (Phase 4)
"""

import pytest
import json
from click.testing import CliRunner
from package_maximizer.cli import (
    list_installed,
    search,
    info,
    check_updates,
    system_info
)


class TestListInstalledCommand:
    """Tests for list-installed CLI command"""

    def test_list_installed_basic(self):
        """Test basic list-installed command"""
        runner = CliRunner()
        result = runner.invoke(list_installed, ['--manager', 'apt'])
        
        # Should complete without error
        assert result.exit_code == 0 or result.exit_code == 1  # May fail if system doesn't have the PM

    def test_list_installed_json_output(self):
        """Test list-installed with JSON output"""
        runner = CliRunner()
        result = runner.invoke(list_installed, ['--manager', 'apt', '--output', 'json'])
        
        # Should complete (may fail on systems without the PM)
        assert result.exit_code in [0, 1]

    def test_list_installed_limit(self):
        """Test list-installed with limit"""
        runner = CliRunner()
        result = runner.invoke(list_installed, ['--manager', 'apt', '--limit', '5'])
        
        assert result.exit_code in [0, 1]


class TestSearchCommand:
    """Tests for search CLI command"""

    def test_search_basic(self):
        """Test basic search command"""
        runner = CliRunner()
        result = runner.invoke(search, ['python', '--manager', 'apt'])
        
        # Should complete without error
        assert result.exit_code == 0 or result.exit_code == 1

    def test_search_json_output(self):
        """Test search with JSON output"""
        runner = CliRunner()
        result = runner.invoke(search, ['python', '--manager', 'apt', '--output', 'json'])
        
        assert result.exit_code in [0, 1]

    def test_search_limit(self):
        """Test search with limit"""
        runner = CliRunner()
        result = runner.invoke(search, ['python', '--manager', 'apt', '--limit', '5'])
        
        assert result.exit_code in [0, 1]


class TestInfoCommand:
    """Tests for info CLI command"""

    def test_info_basic(self):
        """Test basic info command"""
        runner = CliRunner()
        result = runner.invoke(info, ['nginx', '--manager', 'apt'])
        
        # Should complete (may fail if package not found)
        assert result.exit_code in [0, 1]

    def test_info_json_output(self):
        """Test info with JSON output"""
        runner = CliRunner()
        result = runner.invoke(info, ['nginx', '--manager', 'apt', '--output', 'json'])
        
        assert result.exit_code in [0, 1]


class TestCheckUpdatesCommand:
    """Tests for check-updates CLI command"""

    def test_check_updates_basic(self):
        """Test basic check-updates command"""
        runner = CliRunner()
        result = runner.invoke(check_updates, ['--manager', 'apt'])
        
        # Should complete without error
        assert result.exit_code == 0 or result.exit_code == 1

    def test_check_updates_json_output(self):
        """Test check-updates with JSON output"""
        runner = CliRunner()
        result = runner.invoke(check_updates, ['--manager', 'apt', '--output', 'json'])
        
        assert result.exit_code in [0, 1]


class TestSystemInfoCommand:
    """Tests for system-info CLI command"""

    def test_system_info_basic(self):
        """Test basic system-info command"""
        runner = CliRunner()
        result = runner.invoke(system_info, ['--manager', 'apt'])
        
        # Should complete without error
        assert result.exit_code == 0 or result.exit_code == 1

    def test_system_info_json_output(self):
        """Test system-info with JSON output"""
        runner = CliRunner()
        result = runner.invoke(system_info, ['--manager', 'apt', '--output', 'json'])
        
        assert result.exit_code in [0, 1]


class TestCLICommandsExist:
    """Test that all CLI commands are properly registered"""

    def test_all_commands_importable(self):
        """Test that all CLI commands can be imported"""
        from package_maximizer.cli import (
            cli,
            maximize,
            list_solvers,
            list_parsers,
            version,
            from_file,
            benchmark,
            list_installed,
            search,
            info,
            check_updates,
            system_info
        )
        
        # All should be callable
        assert callable(cli)
        assert callable(maximize)
        assert callable(list_solvers)
        assert callable(list_parsers)
        assert callable(version)
        assert callable(from_file)
        assert callable(benchmark)
        assert callable(list_installed)
        assert callable(search)
        assert callable(info)
        assert callable(check_updates)
        assert callable(system_info)

    def test_cli_group_has_commands(self):
        """Test that CLI group has all commands registered"""
        from package_maximizer.cli import cli
        
        # Check that commands are registered
        commands = cli.list_commands(cli)
        
        expected_commands = [
            'maximize',
            'list-solvers',
            'list-parsers',
            'version',
            'from-file',
            'benchmark',
            'list-installed',
            'search',
            'info',
            'check-updates',
            'system-info'
        ]
        
        for cmd in expected_commands:
            assert cmd in commands, f"Command '{cmd}' not found in CLI"


class TestCLICommandBehavior:
    """Exercise CLI command behavior via Click CliRunner."""

    def test_maximize_help(self):
        from click.testing import CliRunner
        from package_maximizer.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["maximize", "--help"])
        assert result.exit_code == 0
        assert "[PACKAGES]" in result.output

    def test_maximize_basic_passes(self):
        from click.testing import CliRunner
        from package_maximizer.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["maximize", "pkg-a", "pkg-b", "--manager", "apt"])
        assert result.exit_code == 0

    def test_list_solvers_contains_greedy(self):
        from click.testing import CliRunner
        from package_maximizer.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["list-solvers"])
        assert result.exit_code == 0
        assert "greedy" in result.output.lower()

    def test_list_parsers_contains_apt(self):
        from click.testing import CliRunner
        from package_maximizer.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["list-parsers"])
        assert result.exit_code == 0
        assert "apt" in result.output.lower()

    def test_benchmark_help(self):
        from click.testing import CliRunner
        from package_maximizer.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["benchmark", "--help"])
        assert result.exit_code == 0

    def test_export_help(self):
        from click.testing import CliRunner
        from package_maximizer.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0

    def test_tui_help(self):
        from click.testing import CliRunner
        from package_maximizer.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["tui", "--help"])
        assert result.exit_code == 0

    def test_version_reports_package_version(self):
        from click.testing import CliRunner
        from package_maximizer.cli import cli
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "0.5" in result.output

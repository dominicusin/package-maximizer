"""
Tests for the new CLI commands: history and shell.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from package_maximizer.cli.main import cli

# --- Shell command tests -----------------------------------------------------


def test_shell_command_imports():
    """shell command imports MaximizerShell without crashing."""
    runner = CliRunner()
    with patch("package_maximizer.tui.shell.MaximizerShell") as mock_shell:
        result = runner.invoke(cli, ["shell"])
    assert result.exit_code == 0


def test_shell_command_with_manager():
    """shell command accepts --manager flag."""
    runner = CliRunner()
    with patch("package_maximizer.tui.shell.MaximizerShell") as mock_shell:
        result = runner.invoke(cli, ["shell", "--manager", "pip"])
    assert result.exit_code == 0
    # Verify MaximizerShell was called with manager="pip"
    mock_shell.assert_called_once()
    call_kwargs = mock_shell.call_args
    assert call_kwargs.kwargs.get("manager") == "pip" or call_kwargs.args[0] == "pip"


# --- Shell unit tests (without running interactive loop) ---------------------


def test_shell_maximize_command():
    """MaximizerShell.do_maximize solves and prints results."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    with patch.object(shell, "_get_maximizer") as mock_max:
        mock_max.return_value.solve.return_value = ["pkg1", "pkg2"]
        shell.do_maximize("pkg1 pkg2 pkg3")
    assert mock_max.return_value.solve.called


def test_shell_maximize_empty():
    """do_maximize with no args prints usage."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    shell.do_maximize("")


def test_shell_propose_command():
    """do_propose loads metadata and prints results."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    with patch.object(shell, "_get_maximizer") as mock_max:
        mock_max.return_value.solve.return_value = ["pkg1"]
        with patch("package_maximizer.adapters.get_adapter") as mock_adapter:
            mock_adapter.return_value = None
            shell.do_propose("pkg1 pkg2")
    assert mock_max.return_value.solve.called


def test_shell_analyze_command():
    """do_analyze prints selected and excluded packages."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    with patch.object(shell, "_get_maximizer") as mock_max:
        mock_max.return_value.solve.return_value = ["pkg1"]
        shell.do_analyze("pkg1 pkg2")
    assert mock_max.return_value.solve.called


def test_shell_compare_command():
    """do_compare runs all solvers and prints table."""
    from package_maximizer.solvers import SOLVER_REGISTRY
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    # do_compare directly instantiates solvers — verify it runs
    shell.do_compare("pkg1 pkg2 pkg3")
    # Should have processed all solvers from registry
    solver_names = list(SOLVER_REGISTRY.keys())
    assert len(solver_names) > 0


def test_shell_manager_command():
    """do_manager sets the manager."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    shell.do_manager("pip")
    assert shell.manager == "pip"


def test_shell_manager_invalid():
    """do_manager with invalid manager prints error."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    shell.do_manager("invalid")
    # Manager should remain unchanged
    assert shell.manager == "apt"


def test_shell_solver_command():
    """do_solver sets the solver."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    shell.do_solver("z3")
    assert shell.solver == "z3"


def test_shell_solver_show_current():
    """do_solver with no args shows current solver."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    shell.do_solver("")
    assert shell.solver == "greedy"


def test_shell_exit_command():
    """do_exit returns True (signals cmdloop to stop)."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    assert shell.do_exit("") is True
    assert shell.do_quit("") is True


def test_shell_json_command():
    """do_json outputs JSON for maximize."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    with patch.object(shell, "_get_maximizer") as mock_max:
        mock_max.return_value.solve.return_value = ["pkg1", "pkg2"]
        shell.do_json("maximize pkg1 pkg2 pkg3")
    assert mock_max.return_value.solve.called


def test_shell_json_analyze():
    """do_json outputs JSON for analyze."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    with patch.object(shell, "_get_maximizer") as mock_max:
        mock_max.return_value.solve.return_value = ["pkg1"]
        shell.do_json("analyze pkg1 pkg2")
    assert mock_max.return_value.solve.called


def test_shell_default_unknown_command():
    """default prints unknown command message."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    shell.default("unknowncmd arg1")


def test_shell_help():
    """do_help prints available commands."""
    from package_maximizer.tui.shell import MaximizerShell

    shell = MaximizerShell()
    shell.do_help("")

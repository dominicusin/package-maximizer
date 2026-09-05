"""Tests for the Textual TUI module."""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")


def test_tui_app_importable():
    """MaximizerApp should be importable when textual is installed."""
    from textual.app import App

    from package_maximizer.tui.app import MaximizerApp

    assert issubclass(MaximizerApp, App)


def test_run_tui_callable():
    """run_tui should be a callable that imports cleanly."""
    from package_maximizer.tui.app import run_tui

    assert callable(run_tui)


def test_cli_tui_command_registered():
    """The CLI group should expose a 'tui' command."""
    from package_maximizer.cli.main import cli

    assert "tui" in cli.commands

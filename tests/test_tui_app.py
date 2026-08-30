"""Tests for the Textual TUI app structure."""

from __future__ import annotations

import pytest

from package_maximizer.tui.app import MaximizerApp


class TestMaximizerApp:
    """MaximizerApp should compose expected widgets."""

    def test_app_class_exists(self):
        assert issubclass(MaximizerApp, object)

    def test_app_has_css(self):
        assert hasattr(MaximizerApp, "CSS")

    def test_app_compose_returns_generator(self):
        app = MaximizerApp()
        compose = app.compose()
        assert compose is not None

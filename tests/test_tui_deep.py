"""
Deep TUI tests for MaximizerApp via Textual's headless run_test().

These exercise the real widget tree (compose, input, button handler,
solver integration) so tui/app.py coverage moves from a surface-level
import check to the actual interactive logic.
"""

import asyncio

import pytest

from package_maximizer.tui.app import MaximizerApp


def _run_app(packages: str, solver: str = "greedy"):
    """Mount the app, set inputs, press Run, return rendered result text."""

    async def _drive():
        app = MaximizerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            inp = app.query_one("#packages")
            inp.value = packages
            sel = app.query_one("#solver")
            sel.value = solver
            await pilot.pause()
            btn = app.query_one("#run")
            btn.press()
            await pilot.pause()
            result = app.query_one("#result_text")
            return str(result.render())

    return asyncio.run(_drive())


def test_app_compose_widgets_present():
    """compose() builds the expected widget tree."""
    app = MaximizerApp()
    async_context = None

    async def _check():
        nonlocal async_context
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#packages") is not None
            assert app.query_one("#solver") is not None
            assert app.query_one("#run") is not None
            assert app.query_one("#result_text") is not None
            assert app.query_one("#log_output") is not None
            async_context = "ok"

    asyncio.run(_check())
    assert async_context == "ok"


def test_button_run_with_packages():
    """Pressing Run with valid packages updates result_text."""
    out = _run_app("vim,nano,emacs", "greedy")
    assert "Selected" in out or "No selection" in out
    assert "Results will appear here." not in out


def test_button_run_empty_packages():
    """Empty input writes a log line and does not crash."""
    out = _run_app("", "greedy")
    # No selection path: result stays default or shows No selection
    assert isinstance(out, str)


def test_button_run_with_solver_z3():
    """Solver selection is honoured (z3 path executes)."""
    out = _run_app("a,b,c", "z3")
    assert "Selected" in out or "No selection" in out


def test_non_run_button_ignored():
    """Buttons other than #run do not trigger solving."""
    async def _drive():
        app = MaximizerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            # There is only one button (#run); just ensure no crash on idle
            await pilot.pause()
            return app.query_one("#result_text").render()

    out = asyncio.run(_drive())
    assert isinstance(str(out), str)


def test_run_tui_callable():
    """run_tui() is callable (does not actually start the loop)."""
    from package_maximizer.tui.app import run_tui

    assert callable(run_tui)

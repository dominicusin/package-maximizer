"""Targeted tests for previously uncovered branches (coverage gate >= 90%)."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from package_maximizer.cli.main import (
    history_command,
    info,
    maximize,
    propose,
    shell_command,
)
from package_maximizer.core.package import Package
from package_maximizer.solvers.enhanced_greedy import EnhancedGreedySolver

CLI_MOD = importlib.import_module("package_maximizer.cli.main")


def _meta(name, depends=(), conflicts=()):
    meta = SimpleNamespace(
        name=name, version="1", depends=list(depends), conflicts=list(conflicts)
    )
    meta.to_package = lambda: Package(
        name=name, depends=list(depends), conflicts=list(conflicts)
    )
    return meta


def _adapter():
    adapter = MagicMock()
    adapter.fetch.side_effect = lambda n: _meta(
        n,
        depends=["ghost"] if n == "c" else [],
        conflicts=["b"] if n == "a" else [],
    )
    return adapter


def _info(**overrides):
    data = dict(
        name="vim",
        version="9.0",
        description="editor",
        depends=["libc"],
        conflicts=[],
        size=42,
        installed=True,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


# --- CLI ---------------------------------------------------------------------


class TestCliExplain:
    def test_maximize_explain_reports_conflict_and_dependency(self):
        result = CliRunner().invoke(
            maximize,
            [
                "a",
                "b",
                "c",
                "-c",
                "a",
                "b",
                "-d",
                "c",
                "missing",
                "--solver",
                "greedy",
                "--explain",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Причины отклонения" in result.output

    def test_maximize_explain_unexplained_exclusion(self):
        with patch.object(CLI_MOD, "PackageMaximizer") as pm:
            pm.return_value.solve.return_value = ["a"]
            result = CliRunner().invoke(maximize, ["a", "b", "--explain"])
        assert result.exit_code == 0, result.output
        assert "не оптимально" in result.output

    def test_maximize_error_exits_1(self):
        with patch.object(
            CLI_MOD, "PackageMaximizer", side_effect=RuntimeError("boom")
        ):
            result = CliRunner().invoke(maximize, ["a"])
        assert result.exit_code == 1
        assert "boom" in result.output

    def test_propose_explain_all_selected(self):
        no_meta = MagicMock()
        no_meta.fetch.return_value = None
        with patch("package_maximizer.adapters.get_adapter", return_value=no_meta):
            result = CliRunner().invoke(
                propose, ["a", "b", "--solver", "greedy", "--explain"]
            )
        assert result.exit_code == 0, result.output
        assert "Все пакеты выбраны" in result.output

    def test_propose_explain_with_exclusions(self):
        with patch("package_maximizer.adapters.get_adapter", return_value=_adapter()):
            result = CliRunner().invoke(
                propose, ["a", "b", "c", "--solver", "greedy", "--explain"]
            )
        assert result.exit_code == 0, result.output
        assert "Причины отклонения" in result.output

    def test_propose_explain_unexplained_and_error(self):
        no_meta = MagicMock()
        no_meta.fetch.return_value = None
        with (
            patch("package_maximizer.adapters.get_adapter", return_value=no_meta),
            patch.object(CLI_MOD, "PackageMaximizer") as pm,
        ):
            pm.return_value.solve.return_value = ["a"]
            result = CliRunner().invoke(propose, ["a", "b", "--explain"])
        assert "не оптимально" in result.output
        with patch.object(
            CLI_MOD, "PackageMaximizer", side_effect=RuntimeError("boom")
        ):
            result = CliRunner().invoke(propose, ["a"])
        assert result.exit_code == 1


class TestCliInfoHistoryShell:
    def test_info_text_and_json(self):
        with patch.object(CLI_MOD, "RealRepoIntegration") as rri:
            rri.return_value.get_package_info.return_value = _info()
            text = CliRunner().invoke(info, ["vim"])
            js = CliRunner().invoke(info, ["vim", "-o", "json"])
        assert "Версия: 9.0" in text.output
        assert "Конфликты: Нет" in text.output
        assert json.loads(js.output)["size"] == 42

    def test_info_not_found_and_error(self):
        with patch.object(CLI_MOD, "RealRepoIntegration") as rri:
            rri.return_value.get_package_info.return_value = None
            assert CliRunner().invoke(info, ["nope"]).exit_code == 1
            rri.return_value.get_package_info.side_effect = RuntimeError("x")
            assert CliRunner().invoke(info, ["vim"]).exit_code == 1

    def test_history_variants(self):
        entries = [{"date": "2026-01-01", "operation": "install", "package": "vim"}]
        with patch.object(CLI_MOD, "RealRepoIntegration") as rri:
            rri.return_value.get_transaction_history.return_value = entries
            text = CliRunner().invoke(history_command, [])
            js = CliRunner().invoke(history_command, ["-o", "json"])
            rri.return_value.get_transaction_history.return_value = []
            empty = CliRunner().invoke(history_command, [])
            rri.side_effect = RuntimeError("x")
            err = CliRunner().invoke(history_command, [])
        assert "install" in text.output and "OK" in text.output
        assert json.loads(js.output) == entries
        assert "пуста" in empty.output
        assert err.exit_code == 1

    def test_shell_command_runs_shell(self):
        with patch("package_maximizer.tui.shell.MaximizerShell") as sh:
            result = CliRunner().invoke(shell_command, ["-m", "pip"])
        assert result.exit_code == 0
        sh.assert_called_once_with(manager="pip")
        sh.return_value.run.assert_called_once()


# --- EnhancedGreedySolver ------------------------------------------------------


class TestEnhancedGreedyStrategies:
    PKGS = [
        Package(name="hub", depends=["x", "y"], conflicts=["leaf"]),
        Package(name="leaf"),
        Package(name="x"),
        Package(name="y"),
    ]

    def test_remove_strategy_replaces_conflicting(self):
        pkgs = [
            Package(name="a", depends=["d1"]),
            Package(name="b", conflicts=["a"]),
            Package(name="d1"),
        ]
        result = EnhancedGreedySolver(conflict_strategy="remove").solve(pkgs)
        assert "a" not in result or "b" not in result

    def test_skip_strategy(self):
        result = EnhancedGreedySolver(conflict_strategy="skip").solve(self.PKGS)
        assert "hub" in result and "leaf" not in result

    def test_weights_skip_strategy(self):
        solver = EnhancedGreedySolver(conflict_strategy="skip")
        result = solver.solve_with_weights(self.PKGS, {"leaf": 5.0})
        assert "leaf" in result and "hub" not in result

    def test_weights_remove_keeps_heavier(self):
        solver = EnhancedGreedySolver(conflict_strategy="remove")
        pkgs = [Package(name="a", conflicts=["b"]), Package(name="b")]
        assert solver.solve_with_weights(pkgs, {"a": 3.0, "b": 1.0}) == ["a"]

    def test_weights_remove_replaces_lighter(self):
        solver = EnhancedGreedySolver(conflict_strategy="remove")
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b"),
            Package(name="c", conflicts=["b"]),
        ]
        assert "b" not in solver.solve_with_weights(pkgs, {"a": 2.0, "c": 2.0})

    def test_weights_empty_and_dependencies(self):
        solver = EnhancedGreedySolver()
        assert solver.solve_with_weights([], None) == []
        result = solver.solve_with_weights(self.PKGS, None)
        assert {"hub", "x", "y"} <= set(result)


# --- TUI shell ------------------------------------------------------------------


class TestShellExtras:
    def _shell(self):
        from package_maximizer.tui.shell import MaximizerShell

        return MaximizerShell(manager="apt")

    def test_get_integration_cached(self):
        shell = self._shell()
        with patch(
            "package_maximizer.integrations.real_repo_integration.RealRepoIntegration"
        ) as rri:
            first = shell._get_integration()
            assert shell._get_integration() is first
        rri.assert_called_once_with(package_manager="apt")

    def test_maximize_and_propose_errors(self, capsys):
        shell = self._shell()
        with patch.object(shell, "_get_maximizer", side_effect=RuntimeError("bad")):
            shell.do_maximize("a b")
            shell.do_propose("a b")
            shell.do_analyze("a b")
        assert capsys.readouterr().out.count("Ошибка: bad") == 3

    def test_propose_adapter_failure_and_empty(self, capsys):
        shell = self._shell()
        shell.do_propose("")
        with patch("package_maximizer.adapters.get_adapter", side_effect=OSError):
            shell.do_propose("a")
        out = capsys.readouterr().out
        assert "Usage: propose" in out and "Предложено (1)" in out

    def test_analyze_with_bottlenecks(self, capsys):
        shell = self._shell()
        maximizer = MagicMock()
        maximizer.solve.return_value = ["a"]
        with patch.object(shell, "_get_maximizer", return_value=maximizer):
            shell.do_analyze("a b")
        assert "Исключено (1)" in capsys.readouterr().out

    def test_info_variants(self, capsys):
        shell = self._shell()
        integration = MagicMock()
        integration.get_package_info.side_effect = [_info(), None, RuntimeError("e")]
        with patch.object(shell, "_get_integration", return_value=integration):
            shell.do_info("vim")
            shell.do_info("nope")
            shell.do_info("vim")
            shell.do_info("")
        out = capsys.readouterr().out
        assert "Version: 9.0" in out
        assert "не найден" in out and "Ошибка: e" in out and "Usage: info" in out

    def test_help_for_command_and_run(self, capsys):
        shell = self._shell()
        shell.do_help("maximize")
        assert "maximize" in capsys.readouterr().out
        with patch.object(shell, "cmdloop") as loop:
            shell.run()
        loop.assert_called_once()


# --- Textual TUI app ----------------------------------------------------------


textual = pytest.importorskip("textual")


def _drive(actions):
    from package_maximizer.tui.app import MaximizerApp

    async def _run():
        app = MaximizerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            out = await actions(app, pilot)
            await pilot.pause()
            return app, out

    return asyncio.run(_run())


async def _wait_for(pilot, condition, attempts=100):
    for _ in range(attempts):
        if condition():
            return
        await pilot.pause(0.05)


async def _wait_for_log(pilot, log, before, attempts=100):
    """Wait until the log grew past ``before`` and stopped changing."""
    prev = -1
    for _ in range(attempts):
        await pilot.pause(0.05)
        n = len(log.lines)
        if n > before and n == prev:
            return
        prev = n


class TestTuiAppExtras:
    def test_dark_mode_button_toggles_twice(self):
        async def actions(app, pilot):
            btn = app.query_one("#dark_mode")
            btn.press()
            await _wait_for(pilot, lambda: str(btn.label) == "Light Mode")
            label_dark = str(btn.label)
            btn.press()
            await _wait_for(pilot, lambda: str(btn.label) == "Dark Mode")
            return label_dark, str(btn.label), app.dark_mode

        app, (dark, light, mode) = _drive(actions)
        assert dark == "Light Mode" and light == "Dark Mode" and mode is False
        assert not app.has_class("dark-mode")

    def test_actions_help_toggle_and_quit(self):
        async def actions(app, pilot):
            app.action_help()
            app.action_toggle_dark_mode()
            await pilot.pause()
            lines = list(app.query_one("#log_output").lines)
            dark = app.dark_mode
            await app.action_quit()
            return lines, dark

        _, (lines, dark) = _drive(actions)
        assert "=== HELP ===" in lines and dark is True

    def _run_with(self, packages, metadata, adapter=None, maximize_error=None):
        async def actions(app, pilot):
            app.query_one("#packages").value = packages
            app.query_one("#metadata").value = metadata
            await pilot.pause()
            log = app.query_one("#log_output")
            before = len(log.lines)
            app.query_one("#run").press()
            await _wait_for_log(pilot, log, before)
            return list(log.lines)

        patches = [
            patch("package_maximizer.adapters.get_adapter", return_value=adapter)
        ]
        if maximize_error:
            patches.append(
                patch(
                    "package_maximizer.core.maximizer.PackageMaximizer.maximize",
                    side_effect=maximize_error,
                )
            )
        for p in patches:
            p.start()
        try:
            return _drive(actions)[1]
        finally:
            for p in patches:
                p.stop()

    def test_run_with_metadata_adapter(self):
        adapter = MagicMock()
        adapter.fetch.return_value = SimpleNamespace(
            name="vim", depends=["libc"], conflicts=["nano"]
        )
        lines = self._run_with("vim,nano", True, adapter)
        assert any("Loaded metadata" in line for line in lines)

    def test_run_with_metadata_no_adapter_and_error(self):
        lines = self._run_with("vim", True, None, maximize_error=RuntimeError("kaput"))
        assert any("No adapter" in line for line in lines)
        assert any("Error: kaput" in line for line in lines)

    def test_run_tui_invokes_app_run(self):
        from package_maximizer.tui import app as tui_app

        with patch.object(tui_app.MaximizerApp, "run") as run:
            tui_app.run_tui()
        run.assert_called_once()


# --- Web API ------------------------------------------------------------------


from package_maximizer.web.app import app as flask_app  # noqa: E402

KEY = {"X-API-Key": os.environ.get("PM_API_KEY", "test-key-for-tests")}


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestWebExtras:
    def test_maximize_explain(self, client):
        r = client.post(
            "/api/v1/maximize",
            json={
                "packages": ["a", "b", "c"],
                "conflicts": [["a", "b"]],
                "explain": True,
            },
            headers=KEY,
        )
        assert r.status_code == 200
        assert "excluded" in r.get_json()

    def test_propose_explain(self, client):
        with patch("package_maximizer.adapters.get_adapter", return_value=_adapter()):
            r = client.post(
                "/api/v1/propose",
                json={"packages": ["a", "b", "c"], "explain": True},
                headers=KEY,
            )
        assert r.status_code == 200
        assert "excluded" in r.get_json()

    def test_maximize_get_with_weights(self, client):
        r = client.get(
            "/api/maximize?packages=a,b&weights=a:2.5,b:oops,bad", headers=KEY
        )
        assert r.status_code == 200

    def test_analyze_with_metadata(self, client):
        with patch("package_maximizer.adapters.get_adapter", return_value=_adapter()):
            r = client.post(
                "/api/v1/analyze",
                json={"packages": ["a", "b", "c"], "metadata": True},
                headers=KEY,
            )
        assert r.status_code == 200
        with patch("package_maximizer.adapters.get_adapter", side_effect=OSError):
            r = client.post(
                "/api/v1/analyze",
                json={"packages": ["a"], "metadata": True},
                headers=KEY,
            )
        assert r.status_code == 200

    def test_compare_with_metadata(self, client):
        with patch("package_maximizer.adapters.get_adapter", return_value=_adapter()):
            r = client.post(
                "/api/v1/compare",
                json={"packages": ["a", "b", "c"], "metadata": True},
                headers=KEY,
            )
        assert r.status_code == 200
        with patch("package_maximizer.adapters.get_adapter", side_effect=OSError):
            r = client.post(
                "/api/v1/compare",
                json={"packages": ["a"], "metadata": True},
                headers=KEY,
            )
        assert r.status_code == 200

    def test_run_app_requires_key(self):
        web_app = importlib.import_module("package_maximizer.web.app")
        with patch.object(web_app, "API_KEY", ""), pytest.raises(SystemExit):
            web_app.run_app()
        with (
            patch.object(web_app, "API_KEY", "k"),
            patch.object(web_app.app, "run") as run,
        ):
            web_app.run_app(port=1234)
        run.assert_called_once_with(host="127.0.0.1", port=1234, debug=False)


# --- Lazy parser registry -------------------------------------------------------


class TestParserRegistryView:
    def test_dict_view_methods(self):
        import package_maximizer.parsers as parsers

        reg = parsers.PARSER_REGISTRY
        assert reg.get("apt") is reg["apt"]
        assert reg.get("nope") is None
        with pytest.raises(KeyError):
            reg["nope"]
        assert list(iter(reg)) == list(reg.keys())
        assert dict(reg.items())["apt"] is reg["apt"]
        assert reg["apt"] in list(reg.values())
        assert parsers.APTParser is reg["apt"]
        with pytest.raises(AttributeError):
            parsers.NoSuchParser  # noqa: B018

    def test_get_parser_unknown(self):
        from package_maximizer.parsers import get_parser

        with pytest.raises(ValueError, match="not found"):
            get_parser("nope")

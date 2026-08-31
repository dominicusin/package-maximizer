"""Textual TUI for Package Maximizer."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Log,
    Select,
    Static,
)


class MaximizerApp(App):
    """Interactive terminal UI for package maximization."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        height: 1fr;
    }
    #results {
        height: 1fr;
    }
    #log {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Container(id="main"):
            with Horizontal():
                yield Input(placeholder="Packages: vim,nano,emacs", id="packages")
                yield Select(
                    [("greedy", "greedy"), ("z3", "z3"), ("pulp", "pulp")],
                    value="greedy",
                    id="solver",
                )
                yield Button("Run", id="run")
            with Vertical(id="results"):
                yield Static("Results will appear here.", id="result_text")
        with Container(id="log"):
            yield Log(id="log_output")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "run":
            return
        packages_text = self.query_one("#packages", Input).value
        solver = self.query_one("#solver", Select).value
        log = self.query_one("#log_output", Log)
        result_text = self.query_one("#result_text", Static)

        packages = [p.strip() for p in packages_text.split(",") if p.strip()]
        if not packages:
            log.write_line("No packages provided.")
            return

        log.write_line(f"Running solver={solver} on {len(packages)} packages...")
        try:
            from package_maximizer.core.maximizer import PackageMaximizer
            from package_maximizer.core.package import Package

            maximizer = PackageMaximizer(manager="apt", solver=solver or "greedy")
            pkg_objs = [Package(name=p) for p in packages]
            selected = maximizer.maximize(pkg_objs)
            selected_names = [p.name for p in selected]
            result_text.update(
                "Selected: " + ", ".join(selected_names) if selected_names else "No selection"
            )
            log.write_line(f"Selected {len(selected_names)}/{len(packages)} packages.")
        except Exception as exc:  # noqa: BLE001
            log.write_line(f"Error: {exc}")


def run_tui() -> None:
    """Run the Textual TUI."""
    app = MaximizerApp()
    app.run()

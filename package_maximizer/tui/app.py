"""Textual TUI for Package Maximizer."""

from __future__ import annotations

import logging

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Checkbox, Footer, Header, Input, Log, Select, Static

logger = logging.getLogger(__name__)


class MaximizerApp(App):
    """Interactive terminal UI for package maximization."""

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
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
    .dark-mode {
        background: $boost;
        color: $text;
    }
    .dark-mode Screen {
        background: $boost;
    }
    .dark-mode #main {
        background: $surface;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dark_mode = False

    @property
    def dark_mode(self) -> bool:
        return self._dark_mode

    def toggle_dark_mode(self) -> None:
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            self.styles.background = "color: $boost"
            self.query_one("#main").styles.background = "color: $surface"
            self.query_one("#log").styles.background = "color: $surface"
        else:
            self.styles.background = "color: $surface"
            self.query_one("#main").styles.background = None
            self.query_one("#log").styles.background = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Container(id="main"):
            with Horizontal():
                yield Input(placeholder="Packages: vim,nano,emacs", id="packages")
                yield Select(
                    [
                        ("greedy", "greedy"),
                        ("z3", "z3"),
                        ("pulp", "pulp"),
                        ("ortools", "ortools"),
                    ],
                    value="greedy",
                    id="solver",
                )
                yield Checkbox("Load metadata", id="metadata")
                yield Button("Run", id="run")
                yield Button("Dark Mode", id="dark_mode")
            with Vertical(id="results"):
                yield Static("Results will appear here.", id="result_text")
        with Container(id="log"):
            yield Log(id="log_output")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dark_mode":
            self.toggle_dark_mode()
            self.query_one("#dark_mode", Button).label = (
                "Light Mode" if self._dark_mode else "Dark Mode"
            )
            return
        if event.button.id != "run":
            return
        packages_text = self.query_one("#packages", Input).value
        solver = self.query_one("#solver", Select).value
        metadata = self.query_one("#metadata", Checkbox).value
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
            if metadata:
                from package_maximizer.adapters import get_adapter

                adapter = get_adapter("apt")
                if adapter is not None:
                    for pkg in pkg_objs:
                        meta = adapter.fetch(pkg.name)
                        if meta and meta.name:
                            if meta.depends:
                                pkg.depends = meta.depends
                            if meta.conflicts:
                                pkg.conflicts = meta.conflicts
                    log.write_line(f"Loaded metadata for {len(packages)} packages.")
                else:
                    log.write_line("No adapter for metadata; continuing without it.")
            selected = maximizer.maximize(pkg_objs)
            selected_names = [p.name for p in selected]
            result_text.update(
                "Selected: " + ", ".join(selected_names)
                if selected_names
                else "No selection"
            )
            log.write_line(f"Selected {len(selected_names)}/{len(packages)} packages.")
        except Exception as exc:  # noqa: BLE001
            log.write_line(f"Error: {exc}")

    def action_toggle_dark_mode(self) -> None:
        """Toggle dark mode via keyboard shortcut (Ctrl+D)."""
        self.toggle_dark_mode()
        logger.info(f"Dark mode: {self._dark_mode}")

    def action_help(self) -> None:
        """Show help dialog via keyboard shortcut (Ctrl+H)."""
        from textual.widgets import Footer

        log = self.query_one("#log_output", Log)
        log.write_line("")
        log.write_line("=== HELP ===")
        log.write_line("Ctrl+R  - Run maximization")
        log.write_line("Ctrl+D  - Toggle dark mode")
        log.write_line("Ctrl+H  - Show this help")
        log.write_line("Ctrl+Q  - Quit")
        log.write_line("===========")
        log.write_line("")

    async def action_quit(self) -> None:
        """Quit the application via keyboard shortcut (Ctrl+Q)."""
        self.exit()


def run_tui() -> None:
    """Run the Textual TUI."""
    app = MaximizerApp()
    app.run()

"""
CLI module - Командный интерфейс Package Maximizer.
"""

from .main import (
    benchmark,
    check_updates,
    cli,
    from_file,
    info,
    list_installed,
    list_parsers,
    list_solvers,
    maximize,
    search,
    system_info,
    version,
)

__all__ = [
    "cli",
    "maximize",
    "list_solvers",
    "list_parsers",
    "version",
    "from_file",
    "benchmark",
    "list_installed",
    "search",
    "info",
    "check_updates",
    "system_info",
]

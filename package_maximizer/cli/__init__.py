"""
CLI module - Командный интерфейс Package Maximizer.
"""

from .main import cli, maximize, list_solvers, list_parsers, version, from_file, benchmark
from .main import list_installed, search, info, check_updates, system_info

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

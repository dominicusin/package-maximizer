"""Dependency Injection module for Package Maximizer."""

from __future__ import annotations

from .container import Container, ServiceLocator, inject
from .factories import (
    ParserFactory,
    SolverFactory,
    build_default_parser_factory,
    build_default_solver_factory,
)

__all__ = [
    "Container",
    "ServiceLocator",
    "inject",
    "SolverFactory",
    "ParserFactory",
    "build_default_solver_factory",
    "build_default_parser_factory",
]

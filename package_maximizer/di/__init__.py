"""Dependency Injection module for Package Maximizer."""

from __future__ import annotations

from .container import Container, ServiceLocator, inject

__all__ = [
    "Container",
    "ServiceLocator",
    "inject",
]

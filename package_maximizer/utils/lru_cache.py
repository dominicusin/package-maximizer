"""
Lightweight LRU cache helpers.

Provides module-level decorators for caching solver/parser construction
and other repeatable lookups. Uses ``functools.lru_cache`` under the hood
so no external dependency is required.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def lru_cache(maxsize: int = 128) -> Callable[[F], F]:
    """
    Drop-in replacement for :func:`functools.lru_cache` with a friendlier
    default for the package-maximizer codebase.
    """
    return functools.lru_cache(maxsize=maxsize)  # type: ignore[return-value]


def lru_cache_method(maxsize: int = 128) -> Callable[[F], F]:
    """
    LRU cache decorator intended for ``self``-bound methods.

    Example::

        class SolverFactory:
            @lru_cache_method()
            def create(self, name: str) -> ConstraintSolver: ...
    """
    return functools.lru_cache(maxsize=maxsize)  # type: ignore[return-value]

"""
Factory pattern for solvers and parsers.

Provides lazy, DI-friendly factories that build solver/parser instances
on demand from the existing registries. Factories support optional
lazy-loading (only import the heavy optional dependency when first used)
and a shared ``CacheManager`` injection for parser instances.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

from ..utils.lru_cache import lru_cache

if TYPE_CHECKING:
    from ..core.interfaces import ConstraintSolver, PackageParser
    from ..utils.cache import CacheManager

logger = logging.getLogger(__name__)


class SolverFactory:
    """
    Factory for creating solver instances by name.

    Example:
        >>> factory = SolverFactory()
        >>> solver = factory.create("greedy")
        >>> isinstance(solver, ConstraintSolver)
    """

    def __init__(
        self,
        registry: Optional[dict[str, Callable[[], "ConstraintSolver"]]] = None,
    ) -> None:
        # registry maps lowercase name -> a zero-arg callable returning a solver
        self._registry: dict[str, Callable[[], "ConstraintSolver"]] = dict(registry or {})

    def register(self, name: str, builder: Callable[[], "ConstraintSolver"]) -> None:
        """Register a new solver builder under ``name`` (case-insensitive)."""
        self._registry[name.lower()] = builder

    def available(self) -> list[str]:
        """Return the list of registered solver names."""
        return sorted(self._registry.keys())

    @lru_cache(maxsize=256)
    def create(self, name: str) -> "ConstraintSolver":
        """
        Create a solver instance by name.

        Args:
            name: Solver name (case-insensitive).

        Returns:
            A ``ConstraintSolver`` instance.

        Raises:
            ValueError: If the solver name is unknown.
        """
        key = name.lower()
        if key not in self._registry:
            available = ", ".join(self.available())
            raise ValueError(f"Solver '{name}' not found. Available: {available}")
        return self._registry[key]()

    def create_all(self) -> dict[str, "ConstraintSolver"]:
        """Create one instance of every registered solver."""
        return {name: builder() for name, builder in self._registry.items()}


class ParserFactory:
    """
    Factory for creating package parser instances by name.

    Parsers may receive a shared ``CacheManager`` so that repeated
    queries to the underlying package manager are cached.
    """

    def __init__(
        self,
        registry: Optional[dict[str, Callable[..., "PackageParser"]]] = None,
        cache: "Optional[CacheManager]" = None,
    ) -> None:
        self._registry: dict[str, Callable[..., "PackageParser"]] = dict(registry or {})
        self._cache = cache

    def register(self, name: str, builder: Callable[..., "PackageParser"]) -> None:
        """Register a new parser builder under ``name`` (case-insensitive)."""
        self._registry[name.lower()] = builder

    def available(self) -> list[str]:
        """Return the list of registered parser names."""
        return sorted(self._registry.keys())

    @lru_cache(maxsize=256)
    def create(self, name: str) -> "PackageParser":
        """
        Create a parser instance by name.

        Args:
            name: Parser name (case-insensitive).

        Returns:
            A ``PackageParser`` instance.

        Raises:
            ValueError: If the parser name is unknown.
        """
        key = name.lower()
        if key not in self._registry:
            available = ", ".join(self.available())
            raise ValueError(f"Parser '{name}' not found. Available: {available}")
        builder = self._registry[key]
        if self._cache is not None:
            try:
                return builder(cache=self._cache)
            except TypeError:
                return builder()
        return builder()

    def create_all(self) -> dict[str, "PackageParser"]:
        """Create one instance of every registered parser."""
        return {name: self.create(name) for name in self._registry}


def build_default_solver_factory() -> SolverFactory:
    """
    Build a SolverFactory populated from the package's SOLVER_REGISTRY.

    Uses lazy builders so optional dependencies (z3, pulp, ortools, ...) are
    only imported when a solver is actually created.
    """
    from ..solvers import SOLVER_REGISTRY

    factory = SolverFactory()
    for name in SOLVER_REGISTRY.keys():
        def _build(name: str = name) -> "ConstraintSolver":  # type: ignore[name-defined]
            from ..solvers import get_solver

            return get_solver(name)  # type: ignore[no-any-return]
        factory.register(name, _build)
    return factory


def build_default_parser_factory(
    cache: "Optional[CacheManager]" = None,
) -> ParserFactory:
    """
    Build a ParserFactory populated from the package's PARSER_REGISTRY.

    Args:
        cache: Optional shared cache injected into parsers that accept it.
    """
    from ..parsers import PARSER_REGISTRY

    factory = ParserFactory(cache=cache)
    for name in PARSER_REGISTRY.keys():
        def _build(name: str = name) -> "PackageParser":  # type: ignore[name-defined]
            from ..parsers import get_parser

            return get_parser(name)  # type: ignore[no-any-return]
        factory.register(name, _build)
    return factory

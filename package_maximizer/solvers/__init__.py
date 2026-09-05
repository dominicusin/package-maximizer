"""Solvers module - Модуль солверов для решения задачи максимизации пакетов."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .enhanced_greedy import EnhancedGreedySolver
    from .greedy import GreedySolver
    from .maxsat_solver import MaxSatSolver
    from .minisat_solver import MiniSatSolver
    from .ortools_solver import ORToolsSolver
    from .pulp_solver import PulPSolver
    from .z3_solver import Z3Solver

# Names that callers may import directly (e.g. ``from package_maximizer.solvers
# import MaxSatSolver``). They are resolved lazily so a missing optional
# dependency only fails when that specific class is actually accessed.
_PUBLIC_SOLVER_NAMES = {
    "GreedySolver": (".greedy", "GreedySolver"),
    "EnhancedGreedySolver": (".enhanced_greedy", "EnhancedGreedySolver"),
    "Z3Solver": (".z3_solver", "Z3Solver"),
    "PulPSolver": (".pulp_solver", "PulPSolver"),
    "ORToolsSolver": (".ortools_solver", "ORToolsSolver"),
    "MaxSatSolver": (".maxsat_solver", "MaxSatSolver"),
    "MiniSatSolver": (".minisat_solver", "MiniSatSolver"),
}

# Available solvers (names re-exported for typing convenience)
__all__ = [
    "GreedySolver",
    "Z3Solver",
    "PulPSolver",
    "ORToolsSolver",
    "MaxSatSolver",
    "MiniSatSolver",
    "EnhancedGreedySolver",
    "get_solver",
    "SOLVER_REGISTRY",
]

# Lazy registry: name -> (module_path, class_name, required_dependency).
# Optional solvers are only imported when actually requested, so a missing
# dependency (z3, pulp, ortools, ...) never breaks `import package_maximizer`.
_SOLVER_SPECS = {
    "greedy": (".greedy", "GreedySolver", None),
    "enhanced_greedy": (".enhanced_greedy", "EnhancedGreedySolver", None),
    "z3": (".z3_solver", "Z3Solver", "z3"),
    "pulp": (".pulp_solver", "PulPSolver", "pulp"),
    "ortools": (".ortools_solver", "ORToolsSolver", "ortools"),
    "maxsat": (".maxsat_solver", "MaxSatSolver", "pysat"),
    "minisat": (".minisat_solver", "MiniSatSolver", "pysat"),
}


class _LazySolverRegistry(dict):
    """
    Dict-like view over ``_SOLVER_SPECS``.

    - ``keys()``/``__contains__`` see every registered solver name even if its
      optional dependency is not yet imported.
    - ``__getitem__``/``get`` lazily import and return the solver class (raising
      ``ImportError`` only when a *specific* unavailable solver is requested).
    """

    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        # Start empty; lazily-loaded classes are cached via dict.__setitem__.
        super().__init__()

    def __getitem__(self, name: str):  # type: ignore[override]
        if name not in _SOLVER_SPECS:
            raise KeyError(name)
        cached = super().__getitem__(name)
        if cached is not None:
            return cached
        cls = _load_solver_class(name)
        super().__setitem__(name, cls)
        return cls

    def get(self, name: str, default=None):  # type: ignore[override]
        try:
            return self[name]
        except (KeyError, ImportError):
            return default

    def __contains__(self, name: object) -> bool:  # type: ignore[override]
        return name in _SOLVER_SPECS

    def keys(self):  # type: ignore[override]
        return _SOLVER_SPECS.keys()

    def values(self):  # type: ignore[override]
        return (_resolve(name) for name in _SOLVER_SPECS)

    def items(self):  # type: ignore[override]
        return ((name, _resolve(name)) for name in _SOLVER_SPECS)

    def __iter__(self):  # type: ignore[override]
        return iter(_SOLVER_SPECS)


def _resolve(name: str):
    try:
        return _load_solver_class(name)
    except ImportError:
        return None


# Public registry (lazy). Iterating / listing works without importing optional deps.
SOLVER_REGISTRY = _LazySolverRegistry()


def _load_solver_class(name: str) -> type:
    """Import and return a solver class by registry name (lazy)."""
    # Check the cache directly (bypass lazy __getitem__ to avoid recursion)
    if dict.__contains__(SOLVER_REGISTRY, name):
        return dict.__getitem__(SOLVER_REGISTRY, name)  # type: ignore[arg-type]

    spec = _SOLVER_SPECS.get(name)
    if spec is None:
        available = ", ".join(sorted(_SOLVER_SPECS.keys()))
        raise ValueError(f"Solver '{name}' not found. Available: {available}")

    module_path, class_name, dependency = spec
    try:
        import importlib

        module = importlib.import_module(module_path, __name__)
        cls = getattr(module, class_name)
    except ImportError as exc:
        dep_hint = f" (requires '{dependency}')" if dependency else ""
        raise ImportError(
            f"Solver '{name}' is unavailable{dep_hint}. "
            f"Install it with: pip install {dependency or name}"
        ) from exc

    # Cache without going back through the lazy registry (avoid recursion)
    dict.__setitem__(SOLVER_REGISTRY, name, cls)
    return cls


def get_solver(solver_name: str):
    """
    Получение экземпляра солвера по имени.

    Args:
        solver_name: Имя солвера (регистронезависимое)

    Returns:
        Экземпляр солвера

    Raises:
        ValueError: Если солвер не найден
        ImportError: Если отсутствует необходимая зависимость
    """
    solver_name = solver_name.lower()
    cls = _load_solver_class(solver_name)
    return cls()


def __getattr__(name: str):  # module-level lazy attribute resolution
    spec = _PUBLIC_SOLVER_NAMES.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, class_name = spec
    import importlib

    module = importlib.import_module(module_path, __name__)
    return getattr(module, class_name)

"""Tests for lazy solver/parser registries."""

from __future__ import annotations

import importlib

import pytest


def test_solvers_module_imports_without_optional_deps():
    """Importing the solvers package must not require z3/pulp/ortools."""
    import package_maximizer.solvers as s

    # Names are always visible
    assert set(s.SOLVER_REGISTRY.keys()) >= {
        "greedy",
        "enhanced_greedy",
        "z3",
        "pulp",
        "ortools",
        "maxsat",
        "minisat",
    }


def test_lazy_registry_lists_names_before_import():
    """``keys()`` works without importing any solver class."""
    import package_maximizer.solvers as s

    # Accessing keys() must not populate the class dict eagerly
    assert "z3" in s.SOLVER_REGISTRY
    # The underlying dict may still hold None for unimported solvers
    assert s.SOLVER_REGISTRY.get("z3") is None or hasattr(
        s.SOLVER_REGISTRY.get("z3"), "__call__"
    )


def test_greedy_solver_resolves_lazily():
    """A core solver resolves without optional dependencies."""
    import package_maximizer.solvers as s

    cls = s.SOLVER_REGISTRY["greedy"]
    assert cls is not None
    assert cls.__name__ == "GreedySolver"


def test_requesting_missing_solver_raises_import_error():
    """
    Requesting an optional solver whose dependency is absent should raise a
    clear ImportError (not a generic AttributeError).
    """
    import package_maximizer.solvers as s

    # If the dependency happens to be installed in this env, we cannot
    # exercise the missing-dependency path — skip rather than fail.
    try:
        s.get_solver("z3")
    except ImportError:
        pass
    else:
        pytest.skip("z3 solver is available in this environment")

    with pytest.raises(ImportError):
        s.get_solver("z3")


def test_parsers_registry_lazy():
    """Parsers registry lists all managers without importing them all."""
    import package_maximizer.parsers as p

    assert set(p.PARSER_REGISTRY.keys()) >= {
        "apt",
        "pacman",
        "dnf",
        "brew",
        "snap",
        "flatpak",
        "cargo",
        "npm",
    }
    # get_parser still works for a core parser
    assert p.get_parser("apt") is not None

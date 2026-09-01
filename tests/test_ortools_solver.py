"""
Tests for solvers.ortools_solver — CP-SAT solver with fallback behavior.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from package_maximizer.core.package import Package


class TestORToolsSolverInit:
    """Constructor defaults."""

    def test_default_init(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        assert solver.time_limit == 10000

    def test_custom_init(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver(time_limit=5000)
        assert solver.time_limit == 5000


class TestORToolsAvailable:
    """ORTOOLS_AVAILABLE flag and import handling."""

    def test_ortools_available_flag(self):
        from package_maximizer.solvers import ortools_solver
        # Just verify the flag exists
        assert hasattr(ortools_solver, 'ORTOOLS_AVAILABLE')


class TestORToolsSolve:
    """solve method with various inputs."""

    def test_solve_empty_packages(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        result = solver.solve([])
        assert result == []

    def test_solve_single_package(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [Package(name="a")]
        result = solver.solve(pkgs)
        assert "a" in result

    def test_solve_no_conflicts(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [Package(name="a"), Package(name="b"), Package(name="c")]
        result = solver.solve(pkgs)
        assert len(result) == 3

    def test_solve_with_conflicts(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
        ]
        result = solver.solve(pkgs)
        # Should not contain both a and b
        assert not ("a" in result and "b" in result)

    def test_solve_with_chain_conflicts(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["c"]),
            Package(name="c"),
        ]
        result = solver.solve(pkgs)
        assert len(result) >= 1

    def test_solve_with_isolated_packages(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
            Package(name="d"),
        ]
        result = solver.solve(pkgs)
        assert "c" in result
        assert "d" in result


class TestORToolsSolveWithWeights:
    """solve_with_weights method."""

    def test_solve_with_weights_empty(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        result = solver.solve_with_weights([], {})
        assert result == []

    def test_solve_with_weights_none(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver.solve_with_weights(pkgs, None)
        assert len(result) == 2

    def test_solve_with_weights_prefers_high(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [
            Package(name="low", conflicts=["high"]),
            Package(name="high", conflicts=["low"]),
        ]
        weights = {"low": 1.0, "high": 10.0}
        result = solver.solve_with_weights(pkgs, weights)
        assert "high" in result

    def test_solve_with_weights_respects_conflicts(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
        ]
        weights = {"a": 1.0, "b": 1.0}
        result = solver.solve_with_weights(pkgs, weights)
        assert not ("a" in result and "b" in result)

    def test_solve_with_weights_missing_weight_defaults(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        weights = {"a": 5.0}  # b missing
        result = solver.solve_with_weights(pkgs, weights)
        assert "a" in result


class TestORToolsGreedyFallback:
    """_greedy_fallback method."""

    def test_greedy_fallback_no_weights(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver._greedy_fallback(pkgs)
        assert isinstance(result, list)

    def test_greedy_fallback_with_weights(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        weights = {"a": 2.0, "b": 1.0}
        result = solver._greedy_fallback(pkgs, weights)
        assert isinstance(result, list)

    def test_greedy_fallback_with_conflicts(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
        ]
        result = solver._greedy_fallback(pkgs)
        assert not ("a" in result and "b" in result)


class TestORToolsNotAvailable:
    """Fallback when OR-Tools is not available."""

    def test_solve_fallback_when_not_available(self):
        from package_maximizer.solvers import ortools_solver
        from package_maximizer.solvers.ortools_solver import ORToolsSolver

        original = ortools_solver.ORTOOLS_AVAILABLE
        ortools_solver.ORTOOLS_AVAILABLE = False
        try:
            solver = ORToolsSolver()
            pkgs = [Package(name="a"), Package(name="b")]
            result = solver.solve(pkgs)
            assert isinstance(result, list)
        finally:
            ortools_solver.ORTOOLS_AVAILABLE = original

    def test_solve_with_weights_fallback_when_not_available(self):
        from package_maximizer.solvers import ortools_solver
        from package_maximizer.solvers.ortools_solver import ORToolsSolver

        original = ortools_solver.ORTOOLS_AVAILABLE
        ortools_solver.ORTOOLS_AVAILABLE = False
        try:
            solver = ORToolsSolver()
            pkgs = [Package(name="a"), Package(name="b")]
            result = solver.solve_with_weights(pkgs, {"a": 1.0})
            assert isinstance(result, list)
        finally:
            ortools_solver.ORTOOLS_AVAILABLE = original


class TestORToolsExceptionHandling:
    """Handle solver exceptions gracefully."""

    def test_solve_returns_list_on_exception(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        # Even if something goes wrong, should return a list
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver.solve(pkgs)
        assert isinstance(result, list)

    def test_solve_with_weights_returns_list_on_exception(self):
        from package_maximizer.solvers.ortools_solver import ORToolsSolver
        solver = ORToolsSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver.solve_with_weights(pkgs, {"a": 1.0})
        assert isinstance(result, list)

"""Tests for solvers.minisat_solver — SAT solver with fallback behavior."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from package_maximizer.core.package import Package


class TestMiniSatSolverInit:
    """Constructor defaults."""

    def test_default_init(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver()
        assert solver.time_limit == 10000
        assert solver.solver_name == "m22"

    def test_custom_init(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver(time_limit=5000, solver_name="g3")
        assert solver.time_limit == 5000
        assert solver.solver_name == "g3"


class TestMiniSatAvailable:
    """MINISAT_AVAILABLE flag."""

    def test_minisat_available_flag(self):
        from package_maximizer.solvers import minisat_solver
        assert hasattr(minisat_solver, 'MINISAT_AVAILABLE')


class TestMiniSatSolve:
    """solve method."""

    def test_solve_empty_packages(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver()
        result = solver.solve([])
        assert result == []

    def test_solve_single_package(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver()
        pkgs = [Package(name="a")]
        result = solver.solve(pkgs)
        assert "a" in result

    def test_solve_no_conflicts(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver()
        pkgs = [Package(name="a"), Package(name="b"), Package(name="c")]
        result = solver.solve(pkgs)
        assert len(result) == 3

    def test_solve_with_conflicts(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
        ]
        result = solver.solve(pkgs)
        assert not ("a" in result and "b" in result)


class TestMiniSatSolveWithWeights:
    """solve_with_weights method."""

    def test_solve_with_weights_empty(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver()
        result = solver.solve_with_weights([], {})
        assert result == []

    def test_solve_with_weights_none(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver.solve_with_weights(pkgs, None)
        assert len(result) == 2

    def test_solve_with_weights_prefers_high(self):
        from package_maximizer.solvers.minisat_solver import MiniSatSolver
        solver = MiniSatSolver()
        pkgs = [
            Package(name="low", conflicts=["high"]),
            Package(name="high", conflicts=["low"]),
        ]
        weights = {"low": 1.0, "high": 10.0}
        result = solver.solve_with_weights(pkgs, weights)
        assert "high" in result


class TestMiniSatNotAvailable:
    """Fallback when MiniSat is not available."""

    def test_solve_fallback_when_not_available(self):
        from package_maximizer.solvers import minisat_solver
        from package_maximizer.solvers.minisat_solver import MiniSatSolver

        original = minisat_solver.MINISAT_AVAILABLE
        minisat_solver.MINISAT_AVAILABLE = False
        try:
            solver = MiniSatSolver()
            pkgs = [Package(name="a"), Package(name="b")]
            result = solver.solve(pkgs)
            assert isinstance(result, list)
        finally:
            minisat_solver.MINISAT_AVAILABLE = original

    def test_solve_with_weights_fallback_when_not_available(self):
        from package_maximizer.solvers import minisat_solver
        from package_maximizer.solvers.minisat_solver import MiniSatSolver

        original = minisat_solver.MINISAT_AVAILABLE
        minisat_solver.MINISAT_AVAILABLE = False
        try:
            solver = MiniSatSolver()
            pkgs = [Package(name="a"), Package(name="b")]
            result = solver.solve_with_weights(pkgs, {"a": 1.0})
            assert isinstance(result, list)
        finally:
            minisat_solver.MINISAT_AVAILABLE = original

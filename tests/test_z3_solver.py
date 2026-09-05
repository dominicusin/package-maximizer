"""Tests for solvers.z3_solver — Z3 SMT solver with fallback behavior."""

from __future__ import annotations

import pytest

from package_maximizer.core.package import Package


class TestZ3SolverInit:
    """Constructor defaults."""

    def test_default_init(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        assert solver.timeout == 10000

    def test_custom_init(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver(timeout=5000)
        assert solver.timeout == 5000


class TestZ3Available:
    """Z3_AVAILABLE flag."""

    def test_z3_available_flag(self):
        from package_maximizer.solvers import z3_solver

        assert hasattr(z3_solver, "Z3_AVAILABLE")


class TestZ3Solve:
    """solve method."""

    def test_solve_empty_packages(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        result = solver.solve([])
        assert result == []

    def test_solve_single_package(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        pkgs = [Package(name="a")]
        result = solver.solve(pkgs)
        assert "a" in result

    def test_solve_no_conflicts(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        pkgs = [Package(name="a"), Package(name="b"), Package(name="c")]
        result = solver.solve(pkgs)
        assert len(result) == 3

    def test_solve_with_conflicts(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
            Package(name="c"),
        ]
        result = solver.solve(pkgs)
        assert not ("a" in result and "b" in result)

    def test_solve_all_conflicting(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        pkgs = [
            Package(name="a", conflicts=["b", "c"]),
            Package(name="b", conflicts=["a", "c"]),
            Package(name="c", conflicts=["a", "b"]),
        ]
        result = solver.solve(pkgs)
        assert len(result) == 1


class TestZ3SolveWithWeights:
    """solve_with_weights method."""

    def test_solve_with_weights_empty(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        result = solver.solve_with_weights([], {})
        assert result == []

    def test_solve_with_weights_none(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        pkgs = [Package(name="a"), Package(name="b")]
        result = solver.solve_with_weights(pkgs, None)
        assert len(result) == 2

    def test_solve_with_weights_prefers_high(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        pkgs = [
            Package(name="low", conflicts=["high"]),
            Package(name="high", conflicts=["low"]),
        ]
        weights = {"low": 1.0, "high": 10.0}
        result = solver.solve_with_weights(pkgs, weights)
        assert "high" in result

    def test_solve_with_weights_respects_conflicts(self):
        from package_maximizer.solvers.z3_solver import Z3Solver

        solver = Z3Solver()
        pkgs = [
            Package(name="a", conflicts=["b"]),
            Package(name="b", conflicts=["a"]),
        ]
        weights = {"a": 1.0, "b": 1.0}
        result = solver.solve_with_weights(pkgs, weights)
        assert not ("a" in result and "b" in result)


class TestZ3NotAvailable:
    """Fallback when Z3 is not available."""

    def test_solve_fallback_when_not_available(self):
        from package_maximizer.solvers import z3_solver
        from package_maximizer.solvers.z3_solver import Z3Solver

        original = z3_solver.Z3_AVAILABLE
        z3_solver.Z3_AVAILABLE = False
        try:
            solver = Z3Solver()
            pkgs = [Package(name="a"), Package(name="b")]
            result = solver.solve(pkgs)
            assert isinstance(result, list)
        finally:
            z3_solver.Z3_AVAILABLE = original

    def test_solve_with_weights_fallback_when_not_available(self):
        from package_maximizer.solvers import z3_solver
        from package_maximizer.solvers.z3_solver import Z3Solver

        original = z3_solver.Z3_AVAILABLE
        z3_solver.Z3_AVAILABLE = False
        try:
            solver = Z3Solver()
            pkgs = [Package(name="a"), Package(name="b")]
            result = solver.solve_with_weights(pkgs, {"a": 1.0})
            assert isinstance(result, list)
        finally:
            z3_solver.Z3_AVAILABLE = original
